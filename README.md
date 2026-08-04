# mi-scraper

Scraper diario que extrae datos de una página HTML, valida duplicados
contra PostgreSQL (Supabase) y publica los registros nuevos en WordPress
via REST API. Corre automáticamente cada día a las 2am con GitHub Actions.

---

## Estructura del proyecto

```
mi-scraper/
├── .github/workflows/sync.yml   ← schedule y configuración del job
├── src/
│   ├── fetcher.py               ← descarga el HTML de la URL objetivo
│   ├── parser.py                ← extrae los datos del HTML ← MODIFICÁ ESTO
│   ├── db.py                    ← operaciones con PostgreSQL (Supabase)
│   └── wp.py                    ← publica posts en WordPress REST API
├── scraper.py                   ← punto de entrada — orquesta todo
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Setup local (primera vez)

### 1. Clonar el repo y crear entorno virtual

```bash
git clone https://github.com/TU-USUARIO/mi-scraper.git
cd mi-scraper

python --version
Python 3.11.9

python -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciales

```bash
cp .env.example .env
# Abrí .env y completá los valores reales
```

Variables necesarias en `.env`:

| Variable | Descripción |
|---|---|
| `SCRAPING_TARGET_URL` | URL de la página a scrapear |
| `DB_URL` | Connection string de Supabase (PostgreSQL) |
| `WP_URL` | URL de tu sitio WordPress |
| `WP_USER` | Usuario de WordPress |
| `WP_APP_PASSWORD` | Application Password de WP |
| `TELEGRAM_ENABLED` | `true` para activar notificaciones importantes |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID (grupo/canal/usuario) para recibir avisos |

### Notificaciones por Telegram (HTML)

El scraper ahora puede enviar avisos por Telegram usando Bot API con `parse_mode=HTML`.
Solo se notifica cuando hay eventos relevantes:

- Nuevos insertados en DB
- Fallidos de mapeo
- Errores de publicación en WordPress
- Fallo crítico (DB o fetch principal)

### 4. Adaptar el parser

Abrí `src/parser.py` y modificá la sección **CONFIGURACIÓN**:

```python
ITEM_SELECTOR    = ".item"   # selector del contenedor de cada item
TITLE_SELECTOR   = "h2"      # selector del título
CONTENT_SELECTOR = "p"       # selector del contenido
LINK_SELECTOR    = "a"       # selector del link
IMAGE_SELECTOR   = "img"     # selector de la imagen
DATE_SELECTOR    = "time"    # selector de la fecha
```

**Cómo encontrar los selectores:**
1. Abrí la página en Chrome → Click derecho → Inspeccionar
2. Identificá el elemento contenedor de cada item
3. Copiá su clase o selector CSS

**Probar selectores rápidamente:**
```bash
python -c "
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
load_dotenv()
html = httpx.get(os.environ['SCRAPING_TARGET_URL']).text
soup = BeautifulSoup(html, 'lxml')
print(soup.select('.tu-selector')[:2])
"
```

---

## Correr en local

```bash
# Simulación — no toca DB ni WordPress
python scraper.py --dry-run

# Flujo completo — publica en WP y guarda en DB
python scraper.py
```

## Verificar conexión con WordPress

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()

"
```

---

## Configurar GitHub Actions

### 1. Subir el código al repo de GitHub

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

### 2. Cargar los Secrets en GitHub

GitHub → tu repo → **Settings → Secrets and variables → Actions → New repository secret**

Crear uno por uno:

| Secret | Valor |
|---|---|
| `SCRAPING_TARGET_URL` | URL de la página |
| `DB_URL` | Connection string Supabase |
| `WP_URL` | URL de tu WordPress |
| `WP_USER` | Tu usuario WP |
| `WP_APP_PASSWORD` | Application Password |

### 3. Primer test manual

GitHub → tu repo → **Actions → Daily Scraping Sync → Run workflow → Run workflow**

Revisá los logs para verificar que todo funciona antes de esperar el run nocturno.

### 4. Ajustar la hora

En `.github/workflows/sync.yml`, la línea:
```yaml
- cron: '0 7 * * *'   # 2am Lima (UTC-5)
```

Ajustala a tu zona horaria (GitHub usa UTC).

---

## Escalar en el futuro

El proyecto está diseñado para crecer sin reescribir:

- **Agregar OCR**: crear `src/ocr.py` y llamarlo desde `parser.py`
- **Segunda fuente**: crear `src/parser_b.py` con selectores distintos
- **Paginación**: usar `fetch_page_with_pagination()` en `fetcher.py`
- **Mover a VPS**: el mismo código, solo cambia cómo se dispara

---

## Dependencias

| Librería | Uso |
|---|---|
| `httpx` | Requests HTTP con timeout y retry |
| `beautifulsoup4` + `lxml` | Parsear HTML |
| `psycopg2-binary` | Conexión a PostgreSQL |
| `python-dotenv` | Leer variables de entorno del `.env` |
| `loguru` | Logging legible en consola y en los logs de Actions |
| `tenacity` | Retry automático con backoff exponencial |
