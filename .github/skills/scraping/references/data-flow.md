# Flujo de datos detallado

## Entrada: `src/data/sources.json`

Cada fuente define:
- `id`, `name`, `base_url`, `max_pages`, `page_param`, `sort_param`
- `batch_delay` (segundos entre items), `enabled` (bool)
- URLs con interpolación de env vars: `"${MY_VAR}"`

## Etapa 1 — Fetch + Parse (`fetcher.py` + `parser.py`)

```
fetcher.fetch_page(url)
  └── requests.get(url, headers=..., verify=ssl_context)
        retry: 3 intentos, backoff exponencial (2s–10s)
        → HTML string

parser.parse_items(html, source)
  ├── Modo 1: busca <article> elements → extrae título, href, excerpt
  └── Modo 2: extrae <script type="application/ld+json"> → JSON-LD
        → list[dict]  (STANDARD_JOB_TEMPLATE)
```

**STANDARD_JOB_TEMPLATE** (campos mínimos del parser):
```python
{
    "id": str,           # slug extraído del URL
    "title": str,
    "url": str,          # URL de la página de detalle
    "excerpt": str,
    "content": str,      # HTML del excerpt / descripción
    "source_id": str,    # fuente.id
    "raw_html": str,     # HTML del artículo completo
}
```

## Etapa 2 — Deduplicación DB (`config/db.py`)

```
db.count_new_slugs(slugs)   → int  (cuántos son nuevos)
db.sync_posts(items)
  ├── INSERT nuevos slugs (ignorar duplicados)
  └── SELECT pendientes (wp_post_id IS NULL)
        → list[dict] pendientes + stats
```

**Tabla PostgreSQL** (`scraped_posts`):
```sql
id              SERIAL PRIMARY KEY
slug            TEXT UNIQUE NOT NULL
url             TEXT
wp_post_id      INTEGER           -- NULL hasta publicación
wp_published_at TIMESTAMPTZ
wp_need_update  BOOLEAN DEFAULT false
created_at      TIMESTAMPTZ DEFAULT now()
```

## Etapa 3 — Enriquecimiento (`mappers/convocatoria.py`)

```
enrich_single(item)
  ├── fetch_page(item["url"])     → HTML de la página de detalle
  ├── parser.parse_detail(html)   → extrae JSON-LD + texto
  └── merge item + detail_data   → item enriquecido

Resultado agrega campos a item:
  "standardized": {
      "job": { title, description, requirements, salary, ... },
      "json_ld": { ... }   # datos del schema.org/JobPosting
  }
```

## Etapa 4 — Mapping a schema canónico (`schemas/convocatoria.py`)

```
ConvocatoriaV2.from_source(item)
  │
  ├── organization: get_or_create_entidad(name) → wp_term_id
  ├── location: normalizar departamento → wp_term_id
  ├── employment: tipo_contrato → wp_term_id
  ├── salary: cascada job.salary → json_ld.baseSalary → texto
  ├── requirements: requirements_parser.segment(texto)
  │     ├── educacion
  │     ├── experiencia  
  │     ├── cursos
  │     └── conocimientos
  ├── careers: careers_utils.extract_careers(educacion) → [wp_term_ids]
  ├── nivel_academico: nivel_academico_utils.classify(educacion) → wp_term_id
  └── application: fechas + url_convocatoria
```

**Prioridad de fallbacks en `from_source()`**:
```
item["campo"]                    ← 1º: campo root (parser básico)
item["standardized"]["job"]["campo"]  ← 2º: parser estructurado
item["standardized"]["json_ld"]["campo"]  ← 3º: JSON-LD schema.org
""  / None                       ← 4º: fallback vacío (nunca falla)
```

## Etapa 5 — Renderizado (`render.py`)

```
render.render_post(conv: ConvocatoriaV2)
  └── Jinja2.render("convocatoria.html", conv=conv)
        → HTML string (contenido del post WP)
```

Template en: `src/templates/convocatoria.html`
Outputs de debug: `output/html/{slug}.html`

## Etapa 6 — Publicación WP (`wp.py` + `services/wp_api.py`)

```
wp.publish_post(conv, html_content, wp_cache)
  ├── wp_cache.get_or_create_entidad(conv.organization.name) → term_id
  ├── wp_cache.get_ids_by_slugs(conv.careers, "carrera") → [ids]
  ├── wp_api.create_post({
  │     title, content, status: "publish",
  │     meta: {
  │       conv_fecha_fin, conv_vacantes, conv_remuneracion,
  │       conv_colegiatura, conv_enlaces, conv_modalidad, ...
  │     },
  │     featured_media: media_id,
  │     categories: [entidad_id],
  │     "conv_carrera": [carrera_ids],
  │     "conv_nivel_academico": [nivel_id],
  │     "conv_departamento": [depto_id],
  │     "conv_tipo_contrato": [contrato_id]
  │   })
  └── returns wp_post_id

db.update_wp_fields(slug, wp_post_id, published_at)
```

## Outputs persistidos

| Archivo | Cuándo | Contenido |
|---------|--------|-----------|
| `output/01_page1_items.json` | Siempre | Items raw página 1 |
| `output/02_page_all_items.json` | Siempre | Items raw todas páginas |
| `output/03_convocatorias_origen.json` | Siempre | Items enriquecidos |
| `output/04_convocatorias_formateada_v2.json` | Siempre | ConvocatoriaV2 |
| `output/html/{slug}.html` | Siempre | HTML renderizado |
| `temp/wp_cache_dump.json` | Si `WP_CACHE_DUMP=true` | Snapshot taxonomías WP |
| `logs/{fecha_hora}.log` | Siempre | Log de ejecución |
