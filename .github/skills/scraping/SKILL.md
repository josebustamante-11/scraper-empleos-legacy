---
name: scraping
description: >
  Arquitectura y convenciones del scraper de convocatorias laborales peruanas.
  Usa este skill para: modificar o agregar fuentes, corregir bugs en el pipeline ETL,
  refactorizar sin duplicar código, escalar el sistema (nuevos parsers, destinos, canales),
  entender el flujo de datos, depurar errores de publicación WP o mapeo de schema,
  y aplicar las convenciones del proyecto al escribir código nuevo.
argument-hint: 'Describe qué quieres cambiar, corregir o entender del scraper'
---

# Scraping — Skill de arquitectura y convenciones

## Propósito de la herramienta

Scraper ETL diario que obtiene convocatorias laborales de entidades públicas peruanas,
las normaliza a un schema canónico `ConvocatoriaV2` y las publica en WordPress vía REST API,
con deduplicación en PostgreSQL (Supabase) y notificaciones por Telegram.

---

## Mapa de archivos

| Archivo | Rol |
|---------|-----|
| `main.py` | Orquestador: coordina todo el pipeline |
| `load_data.py` | Carga taxonomías de WP a JSONs locales |
| `src/fetcher.py` | Descarga HTML con reintentos (tenacity) |
| `src/parser.py` | Extrae items de HTML con BeautifulSoup |
| `src/render.py` | Renderiza `ConvocatoriaV2` → HTML con Jinja2 |
| `src/wp.py` | Publica posts en WordPress via REST API |
| `src/config/__init__.py` | Settings con validación desde env vars |
| `src/config/sources.py` | `ScrapingSource` dataclass; carga `src/data/sources.json` |
| `src/config/db.py` | Pool PostgreSQL; deduplicación; `sync_posts()` |
| `src/mappers/convocatoria.py` | `enrich_single()` + `map_to_v2()` |
| `src/schemas/convocatoria.py` | `ConvocatoriaV2` dataclass canónico |
| `src/services/notifier.py` | Event bus pub-sub; canales pluggables |
| `src/services/wp_api.py` | HTTP wrapper sobre WP REST endpoints |
| `src/services/wp_cache.py` | Cache in-memory de taxonomías WP |
| `src/utils/` | Helpers: text, date, slug, salary, careers, nivel académico |
| `src/data/sources.json` | Definición de fuentes (sin cambios de código) |
| `src/templates/convocatoria.html` | Template Jinja2 del post WP |

---

## Flujo de datos completo

Ver detalle en [data-flow.md](./references/data-flow.md).

```
sources.json → fetcher → parser → DB sync → enrich → map_to_v2 → render → WP API
                                    ↓                     ↓
                               PostgreSQL            ConvocatoriaV2
```

### Fases del pipeline (por fuente)

1. **Scrape**: `fetcher` descarga páginas; `parser` extrae items raw
2. **DB Sync**: inserta slugs nuevos; retorna pendientes (`wp_post_id IS NULL`)
3. **Canary enrich**: enriquece item[0] con página de detalle → si falla, aborta lote
4. **Enrich**: enriquece items[1..n] (skip en error individual)
5. **Reload cache**: recarga taxonomías WP antes de publicar
6. **Map**: `ConvocatoriaV2.from_source()` para cada item
7. **Canary publish**: publica item[0] → si falla, aborta lote
8. **Publish**: publica items[1..n] con `batch_delay` entre cada uno
9. **Notify**: `bus.emit(Event.SUMMARY, ...)` → Telegram

---

## Convenciones y reglas del proyecto

Ver catálogo completo en [conventions.md](./references/conventions.md).

### Reglas críticas (no romper)

- **Patrón canary**: siempre validar item[0] antes de procesar el lote completo
- **Procesamiento secuencial**: nunca paralelizar requests — rate limiting intencional
- **DB como fuente de verdad**: la deduplicación vive en PostgreSQL, no en memoria
- **Cache WP cargada una vez**: no llamar WP API en loops; usar `wp_cache`
- **No código de publicación fuera de `src/wp.py`**: toda interacción WP pasa por ahí
- **Slugs como identificador único**: extraídos del URL; invariantes entre runs

### Extensión sin duplicar código

| Quiero... | Dónde |
|-----------|-------|
| Agregar nueva fuente | Solo editar `src/data/sources.json` |
| Soportar nuevo formato HTML | Agregar variante en `src/parser.py` |
| Agregar campo al schema | Agregar en `ConvocatoriaV2` + `from_source()` + template Jinja2 |
| Agregar canal de notificación | Crear clase que herede `NotificationChannel` en `src/services/notifier.py` |
| Cambiar HTML del post WP | Solo editar `src/templates/convocatoria.html` |
| Agregar meta field WP | Solo editar `src/wp.py` → `publish_post()` |
| Agregar utility reutilizable | Agregar en `src/utils/` (no en `main.py`) |

---

## Schema canónico `ConvocatoriaV2`

```python
@dataclass
class ConvocatoriaV2:
    id: str                  # slug único
    title: str
    organization: Organization   # nombre, entidad_id, entidad_slug
    location: Location           # departamento, modalidad
    employment: Employment       # tipo_contrato, jornada, vacantes
    salary: Salary               # monto, tipo, moneda
    requirements: Requirements   # educacion, experiencia, cursos, conocimientos
    application: Application     # fecha_inicio, fecha_fin, url_convocatoria
    dates: Dates                 # publicado, modificado
    source: Source               # fuente_id, url_origen, url_detalle
    careers: list[int]           # IDs WP de carreras relacionadas
    nivel_academico_id: int      # ID WP del nivel académico
```

`from_source(item)` resuelve datos con cascada de fallbacks:
`root level → standardized.job → json_ld → texto libre`

---

## Diagnóstico rápido de bugs

| Síntoma | Dónde buscar |
|---------|-------------|
| No se publican posts | `src/wp.py` → `publish_post()`; revisar auth WP |
| Slugs duplicados | `src/config/db.py` → `count_new_slugs()` |
| Campo vacío en WP | `src/schemas/convocatoria.py` → `from_source()`; fallbacks |
| HTML mal renderizado | `src/templates/convocatoria.html` + `src/render.py` |
| Carrera no detectada | `src/utils/careers_utils.py` → index de keywords |
| Canary falla siempre | `src/mappers/convocatoria.py` → `enrich_single()` |
| Nueva fuente no parsea | `src/parser.py` → soporta `<article>` y JSON-LD |
| Taxonomía WP no encontrada | `src/services/wp_cache.py` → `get_or_create_*()` |

---

## Procedimiento para cambios seguros

1. **Leer** el archivo relevante antes de editar (nunca editar a ciegas)
2. **Verificar** que el campo/lógica no ya existe en `src/utils/` o `src/schemas/`
3. **Respetar** la fase del pipeline donde debe vivir el cambio (no mover lógica entre fases)
4. **Probar** con `SCRAPING_DEBUG_LIMIT=1` y `TELEGRAM_ENABLED=false`
5. **Verificar** outputs en `output/04_convocatorias_formateada_v2.json` y `output/html/`
6. **No agregar** lógica de negocio a `main.py` — delegar a módulos de `src/`
