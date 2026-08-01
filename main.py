"""
main.py — Punto de entrada principal del scraper ETL

Flujo por cada fuente registrada en src/data/sources.json:
    fetch páginas → parse items → sincronizar DB → publicar en WP

Criterios de diseño:
    - Multi-fuente: itera sobre ScrapingSource; agregar una fuente nueva
      solo requiere editar src/data/sources.json.
    - Canary: el primer item se procesa individualmente antes de continuar,
      para detectar fallos sistémicos temprano.
    - Secuencial: los items restantes se procesan uno a uno, con un delay
      configurable entre cada uno. Esto garantiza trazabilidad total en logs
      y evita saturar el servidor objetivo.
    - Notificaciones reactivas: bus.emit(Event.*) despacha a todos los
      canales registrados (Telegram, etc.) sin duplicar lógica.
"""

import sys
import time
from datetime import datetime

from loguru import logger

from src.config import settings
from src.config.db import (
    count_new_slugs,
    init_db,
    sync_posts,
    sync_posts_pendientes,
    update_wp_fields,
)
from src.config.sources import ScrapingSource, load_sources
from src.fetcher import fetch_page
from src.mappers.convocatoria import enrich_single, export_convocatorias_debug, map_to_v2
from src.parser import parse_items
from src.services.notifier import Event, bus
from src.services.wp_cache import WP_CACHE
from src.services.wp_logos import count_entities_without_logo
from src.utils.file_utils import export_items_json
from src.wp import publish_post


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING — inyecta item_id/slug en cada línea cuando estamos dentro de
# logger.contextualize(item_id=..., slug=...) para rastrear errores
# ─────────────────────────────────────────────────────────────────────────────


def _inject_item_context(record: dict) -> bool:
    """
    Filter de loguru: si el registro tiene item_id en extra, lo antepone
    al mensaje para que cualquier log —incluso de utils profundas— muestre
    a qué item pertenece.

    La guarda `startswith` evita que el prefijo se duplique cuando hay
    múltiples sinks (consola + archivo), ya que loguru llama al filter
    una vez por sink sobre el mismo record compartido.
    """
    extra = record["extra"]
    if "item_id" in extra:
        item_id = extra["item_id"]
        prefix = f"[ID:{item_id}]"
        if not record["message"].startswith(prefix):
            record["message"] = f"{prefix} {record['message']}"
    return True


_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{message}"
)

logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "{message}"
    ),
    filter=_inject_item_context,
    colorize=True,
)
logger.add(
    "logs/{time:YYYY-MM-DD_HH-mm-ss}.log",
    format=_LOG_FORMAT,
    filter=_inject_item_context,
    rotation="00:00",
    retention="30 days",
    encoding="utf-8",
    enqueue=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE PUBLICACIÓN
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_elapsed(seconds: float) -> str:
    """Formatea segundos como 'Xm Ys' o 'Xh Ym Zs'."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _publish_single(item: dict, publicados: list) -> bool:
    """
    Publica un item en WordPress.
    Si tiene éxito, lo agrega a `publicados` para persistir en DB después.
    Retorna True/False. Debe llamarse dentro de un logger.contextualize con item_id.
    """
    try:
        wp_post_id = publish_post(item)
        logger.success(
            f"Publicado: '{item.get('title', '?')}' → [WP_ID:{wp_post_id}]"
        )
        publicados.append(
            {
                "id": item.get("id"),
                "wp_post_id": wp_post_id,
                "wp_published_at": datetime.now(),
            }
        )
        return True
    except Exception as exc:
        logger.error(f"Error publicando '{item.get('title', '?')}': {exc}")
        return False


def _flush_publicados(publicados: list) -> None:
    """Persiste en DB los items publicados exitosamente y vacía la lista."""
    if publicados:
        update_wp_fields(publicados, overwrite=True)
        publicados.clear()


def _export_debug_safe(
    mapped: list[dict],
    enriched: list[dict],
    flow_name: str,
) -> None:
    """Exporta los JSONs de debug capturando excepciones para no interrumpir el flujo."""
    try:
        export_convocatorias_debug(mapped, enriched)
    except Exception as exc:
        logger.warning(f"[{flow_name}] No se pudo exportar debug: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# PROCESAMIENTO CON CANARY + SECUENCIAL
# ─────────────────────────────────────────────────────────────────────────────


def _process_with_canary(
    raw_items: list[dict],
    source: ScrapingSource | None = None,
    flow_name: str = "flujo",
    export_debug: bool = True,
) -> tuple[int, int, int, bool]:
    """
    Procesa una lista de raw items en cuatro fases desacopladas:

        Fase 1 — Enriquecer: descarga las páginas de detalle de todos los items.
                              El primer item (canary) valida que el scraping funcione;
                              si falla, se aborta sin tocar WordPress.
        Fase 2 — Recargar WP cache: obtiene el estado actualizado de taxonomías en WP.
        Fase 3 — Mapear: convierte cada item enriquecido al esquema ConvocatoriaV2.
        Fase 4 — Publicar: inserta en WordPress uno a uno (secuencial, con delay).
                            El primer item publicado también funciona de canary;
                            si falla, se aborta.

    Returns:
        (ok, err, mapped_failed, flow_ok)
    """
    if not raw_items:
        logger.info(f"[{flow_name}] Sin items para procesar.")
        return 0, 0, 0, True

    item_delay = source.batch_delay if source else settings.SCRAPING_BATCH_DELAY
    total = len(raw_items)
    total_ok = total_err = total_map_failed = 0

    # ── FASE 1: Enriquecer (scraping de páginas detalle) ─────────────────────
    logger.info(f"[{flow_name}] Fase 1/4: Canary — enriqueciendo item 1/{total}...")
    canary = raw_items[0]
    with logger.contextualize(item_id=canary.get("id", "?")):
        try:
            canary_enriched = enrich_single(canary)
        except Exception as exc:
            logger.error(f"[{flow_name}] Canary falló en enriquecimiento — lote abortado: {exc}")
            return 0, 0, 1, False

    enriched_items = [canary_enriched]
    logger.info(f"[{flow_name}] Canary OK. Enriqueciendo {total - 1} items restantes...")

    for idx, item in enumerate(raw_items[1:], start=2):
        with logger.contextualize(item_id=item.get("id", "?")):
            logger.info(f"[{flow_name}] [{idx}/{total}] Enriqueciendo...")
            try:
                enriched_items.append(enrich_single(item))
            except Exception as exc:
                logger.error(f"Falló el enriquecimiento: {exc}")
                total_map_failed += 1

    # ── FASE 2: Recargar cache de WordPress ───────────────────────────────────
    logger.info(f"[{flow_name}] Fase 2/4: Recargando cache de WordPress...")
    WP_CACHE.cargar()

    # ── FASE 3: Mapear a ConvocatoriaV2 ───────────────────────────────────────
    logger.info(f"[{flow_name}] Fase 3/4: Mapeando {len(enriched_items)} items a ConvocatoriaV2...")
    mapped_pairs: list[tuple[dict, dict]] = []
    for item_enriquecido in enriched_items:
        with logger.contextualize(item_id=item_enriquecido.get("id", "?")):
            try:
                mapped_pairs.append((map_to_v2(item_enriquecido), item_enriquecido))
            except Exception as exc:
                logger.error(f"Falló el mapeo a V2: {exc}")
                total_map_failed += 1

    if not mapped_pairs:
        logger.warning(f"[{flow_name}] Ningún item pudo mapearse — sin publicaciones.")
        return total_ok, total_err, total_map_failed, True

    # ── FASE 4: Publicar ──────────────────────────────────────────────────────
    n = len(mapped_pairs)
    logger.info(f"[{flow_name}] Fase 4/4: Publicando {n} items en WordPress...")
    publicados:   list[dict] = []
    all_mapped:   list[dict] = []
    all_enriched: list[dict] = []

    for idx, (mapped, enriched) in enumerate(mapped_pairs, start=1):
        with logger.contextualize(item_id=enriched.get("id", "?")):
            if idx > 1:
                logger.info(f"[{flow_name}] [{idx}/{n}] Publicando...")

            if _publish_single(mapped, publicados):
                total_ok += 1
                all_mapped.append(mapped)
                all_enriched.append(enriched)
            else:
                total_err += 1
                if idx == 1:
                    logger.error(f"[{flow_name}] Primer item falló al publicar — lote abortado.")
                    _flush_publicados(publicados)
                    return total_ok, total_err, total_map_failed, False

        if export_debug:
            _export_debug_safe(all_mapped, all_enriched, flow_name)
        _flush_publicados(publicados)

        if idx < n and item_delay > 0:
            time.sleep(item_delay)

    _flush_publicados(publicados)
    return total_ok, total_err, total_map_failed, True


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING DE UNA FUENTE
# ─────────────────────────────────────────────────────────────────────────────


def _scrape_source(source: ScrapingSource) -> tuple[list[dict], int, int]:
    """
    Descarga y parsea todas las páginas necesarias de una fuente.

    Implementa early-stop en la paginación: si una página tiene items
    ya conocidos, detiene la paginación para no re-procesar todo el archivo.

    Returns:
        (all_items, new_count_page1, reviewed_page1)
        new_count_page1 == 0 indica que no hay novedades en esta fuente.
        reviewed_page1  == cuántos items había en la página 1 (para notificar).

    Raises:
        RuntimeError: si no se puede obtener ni parsear la página 1.
    """
    logger.info(f"[{source.id}] Descargando: {source.base_url}")

    try:
        html = fetch_page(source.base_url)
    except Exception as exc:
        raise RuntimeError(f"Falló la descarga de '{source.base_url}': {exc}") from exc

    if not html:
        raise RuntimeError(f"Respuesta vacía al descargar '{source.base_url}'")

    page1_items = parse_items(html, base_url=source.base_url)
    if not page1_items:
        logger.warning(
            f"[{source.id}] Sin items en página 1. "
            "Verifica los selectores en parser.py o la URL de la fuente."
        )
        return [], 0, 0

    logger.info(f"[{source.id}] Página 1: {len(page1_items)} items encontrados")
    export_items_json(page1_items, "output/01_page1_items.json")

    page1_slugs  = [item["slug"] for item in page1_items]
    new_count    = count_new_slugs(page1_slugs)
    items_per_pg = len(page1_items)
    logger.info(f"[{source.id}] {new_count}/{items_per_pg} items nuevos en página 1")

    if new_count == 0:
        return [], 0, items_per_pg

    all_items = list(page1_items)

    # Paginación: solo si toda la página 1 es nueva (para no re-procesar lo conocido)
    if new_count >= items_per_pg and source.max_pages > 1:
        logger.info(
            f"[{source.id}] Página 1 completa es nueva. "
            f"Paginando hasta {source.max_pages} páginas..."
        )
        for page_num in range(2, source.max_pages + 1):
            page_url = source.page_url(page_num)
            try:
                page_html = fetch_page(page_url)
            except Exception as exc:
                logger.warning(f"[{source.id}] Falló fetch página {page_num}: {exc}")
                break

            if not page_html:
                logger.info(f"[{source.id}] Página {page_num} vacía. Fin de paginación.")
                break

            page_items = parse_items(page_html, base_url=source.base_url)
            if not page_items:
                logger.info(f"[{source.id}] Página {page_num} sin items. Fin de paginación.")
                break

            page_slugs     = [item["slug"] for item in page_items]
            page_new_count = count_new_slugs(page_slugs)
            logger.info(
                f"[{source.id}] Página {page_num}: "
                f"{len(page_items)} items, {page_new_count} nuevos"
            )
            all_items.extend(page_items)

            if page_new_count < len(page_items):
                logger.info(
                    f"[{source.id}] Página {page_num} tiene items conocidos — early stop."
                )
                break
    else:
        logger.info(
            f"[{source.id}] Solo {new_count}/{items_per_pg} nuevos. No se necesita paginar."
        )

    export_items_json(all_items, "output/02_page_all_items.json")
    return all_items, new_count, items_per_pg


def _process_source(source: ScrapingSource, global_stats: dict, start_time: float) -> None:
    """Ejecuta el ciclo ETL completo para una fuente: scrape → sync DB → publicar."""
    logger.info(f"{'─' * 20} Fuente: {source.name} ({source.id}) {'─' * 20}")

    # Scraping y paginación
    try:
        scraped_items, _, reviewed = _scrape_source(source)
    except RuntimeError as exc:
        logger.error(str(exc))
        bus.emit(
            Event.CRITICAL,
            source_id=source.id,
            source_name=source.name,
            stage="fetch",
            detail=str(exc),
            elapsed=_fmt_elapsed(time.perf_counter() - start_time),
            **global_stats,
        )
        return

    if not scraped_items:
        global_stats.setdefault("source_notes", []).append(
            f"ℹ️ {source.name or source.id}: sin novedades ({reviewed} revisados)"
        )
        bus.emit(
            Event.NO_NEW_ITEMS,
            source_id=source.id,
            source_name=source.name,
            reviewed=reviewed,
            elapsed=_fmt_elapsed(time.perf_counter() - start_time),
            **global_stats,
        )
        return

    # Sincronizar con DB: insertar nuevos, obtener pendientes
    pending_items, inserted_count = sync_posts(scraped_items, return_stats=True)
    global_stats["total_scraped"]    += len(scraped_items)
    global_stats["inserted"]         += inserted_count
    global_stats["sources_processed"] += 1

    if not pending_items:
        logger.info(f"[{source.id}] Sin pendientes nuevos. Nada que publicar.")
        return

    # Re-enriquecer pending_items con los datos completos del scraping.
    # sync_posts solo guarda {slug, url} en DB y devuelve {id, slug, url}.
    # Fusionamos el dict completo del listado (title, organization, etc.)
    # para que el mapper reciba toda la información y los JSONs de debug
    # sean completos. El id de DB siempre prevalece.
    scraped_by_slug = {item["slug"]: item for item in scraped_items}
    pending_items = [
        {**scraped_by_slug.get(p["slug"], p), "id": p["id"]}
        for p in pending_items
    ]

    # Límite de prueba: SCRAPING_DEBUG_LIMIT=N en el .env procesa solo N items
    debug_limit = settings.SCRAPING_DEBUG_LIMIT
    if debug_limit > 0:
        logger.warning(
            f"[{source.id}] SCRAPING_DEBUG_LIMIT={debug_limit} activo — "
            f"procesando {min(debug_limit, len(pending_items))}/{len(pending_items)} items."
        )
        pending_items = pending_items[:debug_limit]

    # Publicar con canary + lotes concurrentes
    ok, err, map_failed, flow_ok = _process_with_canary(
        pending_items,
        source=source,
        flow_name=source.id,
        export_debug=True,
    )
    global_stats["published_ok"]   += ok
    global_stats["publish_errors"] += err
    global_stats["mapped_failed"]  += map_failed

    if not flow_ok:
        global_stats.setdefault("source_notes", []).append(
            f"⚠️ {source.name or source.id}: canary falló — lote abortado"
        )
        bus.emit(
            Event.CANARY_FAILED,
            source_id=source.id,
            source_name=source.name,
            item_title=pending_items[0].get("slug", "?") if pending_items else "?",
            reason="El canary falló al mapear o publicar. El lote fue abortado.",
            elapsed=_fmt_elapsed(time.perf_counter() - start_time),
            **global_stats,
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    start_time = time.perf_counter()

    logger.info("=" * 50)
    logger.info("Iniciando sync del scraper ETL")
    logger.info("=" * 50)

    # Cargar cache de taxonomías WordPress una sola vez
    WP_CACHE.cargar()

    # 1. Inicializar la base de datos
    if not init_db():
        bus.emit(
            Event.CRITICAL,
            stage="init_db",
            detail="No se pudo inicializar la base de datos.",
            elapsed=_fmt_elapsed(time.perf_counter() - start_time),
            total_scraped=0,
            inserted=0,
            published_ok=0,
            publish_errors=0,
            mapped_failed=0,
            sources_processed=0,
        )
        return

    # 2. Procesar registros pendientes históricos (wp_post_id IS NULL en DB)
    #    Esto atiende items que fallaron en ejecuciones anteriores antes de
    #    buscar novedades nuevas, priorizando consistencia sobre volumen.
    pending_db = sync_posts_pendientes()
    pending_db_ok = pending_db_err = pending_db_map_failed = 0
    if pending_db:
        debug_limit = settings.SCRAPING_DEBUG_LIMIT
        if debug_limit > 0:
            logger.warning(
                f"SCRAPING_DEBUG_LIMIT={debug_limit} activo — "
                f"procesando {min(debug_limit, len(pending_db))}/{len(pending_db)} "
                "pendientes históricos."
            )
            pending_db = pending_db[:debug_limit]
        logger.info(f"Procesando {len(pending_db)} registros pendientes históricos en DB...")
        pending_db_ok, pending_db_err, pending_db_map_failed, flow_ok = _process_with_canary(
            pending_db,
            flow_name="pendientes_db",
            export_debug=True,
        )
        logger.info(
            f"Pendientes DB: {pending_db_ok} publicados | "
            f"{pending_db_err} errores | {pending_db_map_failed} fallidos en mapeo"
        )
        if not flow_ok:
            item_slug = pending_db[0].get("slug", "?") if pending_db else "?"
            bus.emit(
                Event.CRITICAL,
                stage="canary_pendientes_db",
                detail=(
                    f"Canary falló en pendientes históricos "
                    f"(item: {item_slug}). Se abortó el proceso."
                ),
                elapsed=_fmt_elapsed(time.perf_counter() - start_time),
                total_scraped=0,
                inserted=0,
                published_ok=pending_db_ok,
                publish_errors=pending_db_err,
                mapped_failed=pending_db_map_failed,
                sources_processed=0,
                source_notes=[],
            )
            return
    else:
        logger.info("Sin pendientes históricos en DB.")

    # 3. Cargar fuentes y procesar cada una
    try:
        sources = load_sources()
    except RuntimeError as exc:
        bus.emit(
            Event.CRITICAL,
            stage="load_sources",
            detail=str(exc),
            elapsed=_fmt_elapsed(time.perf_counter() - start_time),
            total_scraped=0,
            inserted=0,
            published_ok=pending_db_ok,
            publish_errors=pending_db_err,
            mapped_failed=pending_db_map_failed,
            sources_processed=0,
        )
        return

    # Los conteos de pendientes_db se suman al resumen global para que la
    # notificación final refleje el total real de la ejecución.
    global_stats: dict = {
        "total_scraped":     0,
        "inserted":          0,
        "published_ok":      pending_db_ok,
        "publish_errors":    pending_db_err,
        "mapped_failed":     pending_db_map_failed,
        "sources_processed": 0,
        "source_notes":      [],
    }

    for source in sources:
        _process_source(source, global_stats, start_time)

    # 4. Resumen final
    elapsed = _fmt_elapsed(time.perf_counter() - start_time)
    logger.info(
        f"{'=' * 50}\n"
        f"Resumen: {global_stats['published_ok']} publicados | "
        f"{global_stats['publish_errors']} errores | "
        f"{global_stats['sources_processed']} fuente(s) procesada(s) | "
        f"Tiempo: {elapsed}"
    )

    entities_without_logo = count_entities_without_logo()
    bus.emit(Event.SUMMARY, elapsed=elapsed, entities_without_logo=entities_without_logo, **global_stats)


if __name__ == "__main__":
    main()
