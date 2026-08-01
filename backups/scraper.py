"""
scraper.py — Punto de entrada principal
Orquesta el flujo: fetch → parse → validar → publicar → guardar

Uso:
    python scraper.py           # corre el flujo completo

"""

from datetime import datetime
from loguru import logger
from src.config import settings
from src.config.db import init_db, sync_posts, sync_posts_pendientes, update_wp_fields, count_new_slugs
from src.mappers.convocatoria import mapper_convocatorias_v2
from src.utils.file_utils import export_items_json
from src.fetcher import fetch_page
from src.parser import parse_items
from src.services.telegram_notifier import (
    notify_critical_failure,
    notify_important_summary,
    notify_no_new_items,
)
from src.services.wp_cache import WP_CACHE
from src.wp import publish_post




def main():
    logger.info("===== Iniciando sync =====")

    # 1. Inicializa la DB (crea tabla si no existe)
    if not init_db():
        logger.error("No se pudo inicializar la DB. Abortando sync sin traceback.")
        notify_critical_failure("init_db", "No se pudo inicializar la base de datos")
        return

    # 1.1 Procesar primero los registros pendientes en la DB (wp_post_id IS NULL)
    pending_db = sync_posts_pendientes()
    if pending_db:
        logger.info(f"Procesando primero {len(pending_db)} registros pendientes en la DB (wp_post_id IS NULL)")
        # Mapear y publicar los pendientes
        convocatorias_v2, fallidos = mapper_convocatorias_v2(pending_db)
        if fallidos:
            logger.warning(f"Items que no pudieron ser convertidos a ConvocatoriaV2: {len(fallidos)}")

        WP_CACHE.cargar()

        ok = 0
        err = 0
        publicados = []
        for item in convocatorias_v2:
            try:
                wp_post_id = publish_post(item)
                logger.success(f"Publicado: '{item['title']}' → WP ID {wp_post_id} → ID interno {item.get('id')}")
                publicados.append({
                    "id": item.get("id"),
                    "wp_post_id": wp_post_id,
                    "wp_published_at": datetime.now()
                })
                ok += 1
            except Exception as e:
                logger.error(f"Error procesando '{item.get('title', '?')}': {e}")
                err += 1
        if publicados:
            update_wp_fields(publicados, overwrite=True)
        logger.info(f"===== Resumen pendientes DB: {ok} publicados | {err} errores =====")
        # Si quieres que termine aquí y no siga con scraping, descomenta el return:
        # return

    # 2. Traer HTML de la página 1 (Home) y evaluar si hay items nuevos
    base_url = settings.SCRAPING_TARGET_URL
    try:
        html = fetch_page(base_url)
    except Exception as e:
        logger.error(f"Falló la descarga de la página principal: {e}")
        notify_critical_failure("fetch_page", str(e))
        return

    if not html:
        logger.error("No se pudo obtener el HTML scrapeado.")
        notify_critical_failure("fetch_page", "Respuesta vacía al intentar descargar la página")
        return

    # 3. Parsear página 1 y verificar cuántos items son nuevos (sin insertar)
    page1_items = parse_items(html, base_url=base_url)
    if not page1_items:
        logger.warning("No se encontraron items. Verificá los selectores en parser.py")
        return
    
    logger.info(f"Items encontrados en la página: {len(page1_items)}")
    json_path = export_items_json(page1_items, "output/last_extraction_1.json")
    logger.info(f"JSON generado en: {json_path}")

    items_per_page = len(page1_items)
    page1_slugs = [item["slug"] for item in page1_items]
    new_count = count_new_slugs(page1_slugs)
    logger.info(f"Página 1: {items_per_page} items, {new_count} nuevos")

    if new_count == 0:
        logger.info("No hay items nuevos en la página principal. Nada que hacer.")
        notify_no_new_items(items_per_page)
        return

    # 4. Paginación inteligente: si TODA la página 1 es nueva, seguir paginando
    all_items = list(page1_items)
    max_pages = settings.SCRAPING_MAX_PAGES

    if new_count >= items_per_page and max_pages > 1:
        logger.info(f"Todos los items de página 1 son nuevos. Paginando hasta {max_pages} páginas...")
        for page_num in range(2, max_pages + 1):
            page_url = f"{base_url}?page={page_num}&sort=1-id"
            try:
                page_html = fetch_page(page_url)
            except Exception as e:
                logger.warning(f"Falló fetch de página {page_num}: {e}")
                break

            if not page_html:
                break

            page_items = parse_items(page_html, base_url=base_url)
            if not page_items:
                logger.info(f"Página {page_num} sin items. Deteniendo paginación.")
                break

            page_slugs = [item["slug"] for item in page_items]
            page_new_count = count_new_slugs(page_slugs)
            logger.info(f"Página {page_num}: {len(page_items)} items, {page_new_count} nuevos")

            all_items.extend(page_items)

            if page_new_count < len(page_items):
                logger.info(f"Página {page_num} tiene items conocidos. Early stop.")
                break
    else:
        logger.info(f"Solo {new_count}/{items_per_page} nuevos en página 1. No se necesita paginar más.")

    scraped_items = all_items
    logger.info(f"Total items recolectados: {len(scraped_items)}")
    json_path = export_items_json(scraped_items)
    logger.info(f"JSON generado en: {json_path}")

    # 5. Insertar nuevos en DB y obtener pendientes
    pending_items, inserted_count = sync_posts(scraped_items, return_stats=True)
    # pending_items = pending_items[:50]  # Solo procesar el primer item (para pruebas o limitación)
    if not pending_items:
        logger.info("No hay registros nuevos. Nada que publicar.")
        return

    # 6. Mapear cada item pendiente a la estructura final esperada por WordPress
    convocatorias_v2, fallidos = mapper_convocatorias_v2(pending_items)
    if fallidos:
        logger.warning(f"Items que no pudieron ser convertidos a ConvocatoriaV2: {len(fallidos)}")

    # 1.5 Cargar taxonomías de WP en cache de memoria (entidades, contratos, departamentos, medias + instituciones.json)
    WP_CACHE.cargar()

    # 7. Publicar cada item nuevo en WordPress y guardar en DB
    ok = 0
    err = 0
    publicados = []

    for item in convocatorias_v2:
        try:
            wp_post_id = publish_post(item)
            logger.success(f"Publicado: '{item['title']}' → WP ID {wp_post_id} → ID interno {item.get('id')}")
            publicados.append({
                "id": item.get("id"),
                "wp_post_id": wp_post_id,
                "wp_published_at": datetime.now()
            })
            ok += 1
        except Exception as e:
            logger.error(f"Error procesando '{item.get('title', '?')}': {e}")
            err += 1
    if publicados:
        update_wp_fields(publicados, overwrite=True)

    logger.info(f"===== Resumen: {ok} publicados | {err} errores =====")
    notify_important_summary(
        inserted_count=inserted_count,
        published_ok=ok,
        publish_errors=err,
        mapped_failed_count=len(fallidos),
        total_scraped=len(scraped_items),
    )


if __name__ == "__main__":
    main()
