# Convenciones y reglas del proyecto

## Arquitectura — reglas de capas

```
main.py          → solo orquestación (no lógica de negocio)
src/fetcher.py   → solo HTTP (no parsing, no DB)
src/parser.py    → solo extracción de HTML (no lógica de dominio)
src/mappers/     → transformación entre formatos (no I/O)
src/schemas/     → definición de estructuras de datos (no side effects)
src/services/    → integraciones externas (WP, DB, notificaciones)
src/utils/       → helpers puros reutilizables (sin dependencias circulares)
src/config/      → configuración y Settings (sin lógica de negocio)
```

**Regla**: no cruzar capas saltando niveles. Si `main.py` necesita algo de `src/utils/`,
importar directamente. Si un mapper necesita DB, recibir el resultado como parámetro.

---

## Patrón Canary

Siempre que se procesa un lote de items, el item[0] actúa como canary:

```python
# Enrich canary
canary = items[0]
try:
    canary = enrich_single(canary)
except Exception as e:
    bus.emit(Event.CANARY_FAILED, stage="enrich", detail=str(e))
    return  # aborta TODO el lote

# Publish canary
try:
    wp_id = publish_post(canary_mapped, ...)
except Exception as e:
    bus.emit(Event.CANARY_FAILED, stage="publish", detail=str(e))
    return  # aborta TODO el lote

# Solo si canary OK → procesar el resto
for item in items[1:]:
    ...
```

**Nunca eliminar** el patrón canary. Si quieres probar sin él, usar `SCRAPING_DEBUG_LIMIT=1`.

---

## Convenciones de código Python

### Imports
```python
# Orden: stdlib → third-party → src local
import os
from pathlib import Path

import requests
from loguru import logger

from src.config import settings
from src.schemas.convocatoria import ConvocatoriaV2
```

### Logging
```python
# Siempre usar loguru; nunca print() en código de producción
from loguru import logger

logger.info("Procesando fuente: {source_id}", source_id=source.id)
logger.warning("Campo vacío: {field}", field="salary")
logger.error("Error inesperado: {e}", e=str(e))

# En loops, usar contexto:
with logger.contextualize(slug=item["id"], source=source.id):
    logger.info("Enriqueciendo item")
```

### Manejo de errores
```python
# En procesamiento de items: skip individual, nunca abortar lote
for item in items:
    try:
        result = process(item)
    except Exception as e:
        logger.error("Fallo en item {slug}: {e}", slug=item["id"], e=e)
        error_count += 1
        continue  # seguir con el siguiente

# En canary y operaciones críticas: propagar excepción para que el caller aborte
```

### Dataclasses
```python
# Preferir dataclasses con valores default en vez de dicts ad-hoc
@dataclass
class MiEstructura:
    campo: str = ""
    opcional: int | None = None
    lista: list[str] = field(default_factory=list)
```

---

## Convenciones de configuración

### Settings (`src/config/__init__.py`)
```python
# CORRECTO: leer desde settings
from src.config import settings
delay = settings.batch_delay

# INCORRECTO: leer env vars directamente en módulos
delay = float(os.getenv("SCRAPING_BATCH_DELAY", "1.0"))
```

### Sources (`src/data/sources.json`)
```json
{
  "id": "kebab-case-unico",
  "name": "Nombre oficial de la entidad",
  "base_url": "https://...",
  "max_pages": 10,
  "page_param": "page",
  "sort_param": "sort=1-id",
  "batch_delay": 1.5,
  "enabled": true
}
```

- `id` debe ser único globalmente; se usa como `source_id` en DB y logs
- `batch_delay` puede sobrescribir el global `SCRAPING_BATCH_DELAY`
- Para deshabilitar temporalmente: `"enabled": false` (nunca borrar)
- Para env var en URL: `"base_url": "${ENV_VAR_NAME}"`

---

## Convenciones del WP Cache

```python
# CORRECTO: siempre usar wp_cache para taxonomías
from src.services.wp_cache import wp_cache

entidad_id = wp_cache.get_or_create_entidad("NOMBRE ENTIDAD")
carrera_ids = wp_cache.get_ids_by_slugs(["slug1", "slug2"], "conv_carrera")

# INCORRECTO: llamar WP API directamente en loops
response = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?name=...")
```

El cache se recarga una vez por lote (fase 2 del pipeline). No forzar recarga manual.

---

## Convenciones de notificaciones

```python
from src.services.notifier import bus, Event

# Eventos disponibles
bus.emit(Event.CRITICAL, stage="fetch", detail="mensaje")
bus.emit(Event.CANARY_FAILED, stage="enrich", detail="mensaje")
bus.emit(Event.NO_NEW_ITEMS, source_id="fuente")
bus.emit(Event.SUMMARY, inserted=5, published_ok=5, published_err=0, elapsed=12.3)
```

Para agregar un nuevo canal (ej: email, Slack):
1. Crear clase en `src/services/notifier.py` que herede `NotificationChannel`
2. Implementar `handles(event) -> bool` y `send(notif: Notification)`
3. Registrar: `bus.register(MiCanal())`

---

## Variables de entorno para desarrollo

```bash
# Modo seguro para pruebas locales
SCRAPING_DEBUG_LIMIT=1          # procesar solo 1 item
TELEGRAM_ENABLED=false           # no enviar notificaciones
WP_CACHE_DUMP=true              # guardar snapshot del cache WP
SCRAPING_FETCH_DETAIL_PAGES=true # enriquecer con páginas de detalle
```

---

## Campos meta de WordPress

Los meta fields del post se definen en `src/wp.py` → `publish_post()`:

| Meta key | Tipo | Fuente en ConvocatoriaV2 |
|----------|------|--------------------------|
| `conv_fecha_fin` | date string | `application.fecha_fin` |
| `conv_vacantes` | int | `employment.vacantes` |
| `conv_remuneracion` | string | `salary.monto` |
| `conv_colegiatura` | bool | `requirements.colegiatura` |
| `conv_enlaces` | JSON | `application.url_convocatoria` |
| `conv_modalidad` | string | `location.modalidad` |

Para agregar un campo nuevo:
1. Agregar atributo a `ConvocatoriaV2` (o substructura relevante)
2. Rellenar en `from_source()` con fallbacks
3. Agregar a `meta` dict en `publish_post()`
4. Registrar el meta key en WordPress (functions.php del tema)

---

## Anti-patrones a evitar

| Anti-patrón | Alternativa |
|-------------|-------------|
| Lógica de dominio en `main.py` | Mover a módulo `src/` apropiado |
| Leer WP API en loops de items | Usar `wp_cache` |
| Duplicar normalización de texto | Usar `src/utils/text_utils.py` |
| Crear nuevos helpers en `main.py` | Crear en `src/utils/` |
| Hardcodear URLs de fuentes en código | Usar `src/data/sources.json` |
| `print()` para debug | `logger.debug()` |
| `time.sleep()` manual entre items | Usar `source.batch_delay` |
| Parsear salary/fechas inline | Usar `src/utils/data_utils.py` |
