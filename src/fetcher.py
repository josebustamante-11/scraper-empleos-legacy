"""
fetcher.py — Responsable de traer el HTML de la página externa

Cambiá SOLO:
    - La URL en el .env (SCRAPING_TARGET_URL)
    - Los headers si el sitio requiere autenticación o cookies especiales
"""

import os
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.http_utils import _get_ssl_verify_config
from src.config import settings

# ─────────────────────────────────────────
# CONFIGURACIÓN — ajustá si es necesario
# ─────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ─────────────────────────────────────────


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def fetch_page(url: str = None) -> str | None:
    """
    Descarga el HTML de la URL objetivo.
    Reintenta automáticamente hasta 3 veces si hay error de red.

    Args:
        url: URL a fetchear. Si es None, usa SCRAPING_TARGET_URL del .env

    Returns:
        HTML como string, o None si falló
    """
    target_url = url or settings.SCRAPING_TARGET_URL

    if not target_url:
        raise ValueError(
            "No hay URL configurada. "
            "Definí SCRAPING_TARGET_URL en el .env o en los GitHub Secrets."
        )

    logger.info(f"Fetching: {target_url}")

    response = httpx.get(
        target_url,
        headers=HEADERS,
        timeout=30,
        verify=_get_ssl_verify_config(),
        # follow_redirects=True,
    )
    response.raise_for_status()

    logger.info(f"Respuesta: {response.status_code} | {len(response.text)} caracteres")
    return response.text


def fetch_page_with_pagination(base_url: str, max_pages: int = 5) -> list[str]:
    """
    Útil si la página tiene paginación (?page=1, ?page=2, etc.)
    Retorna lista de HTMLs — uno por página.

    Ejemplo de uso en parser.py:
        pages = fetch_page_with_pagination("https://ejemplo.com/noticias", max_pages=3)
        items = []
        for html in pages:
            items.extend(parse_items(html))

    Ajustá el parámetro de paginación según el sitio:
        ?page=N, ?p=N, &offset=N*10, etc.
    """
    htmls = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}?page={page}"  # <-- ajustá el parámetro de paginación
        try:
            html = fetch_page(url)
            if html:
                htmls.append(html)
        except Exception as e:
            logger.warning(f"Falló página {page}: {e}. Continuando...")
            break
    return htmls
