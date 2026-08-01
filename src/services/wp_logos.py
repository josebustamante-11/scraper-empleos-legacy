"""
wp_logos.py — Utilidades para detectar entidades pendientes de logo.

Expone:
    count_entities_without_logo() -> int
        Consulta la pagina /entidad/ del sitio WordPress y devuelve cuantas
        entidades todavia usan el logo por defecto (icon-default.webp).

El bloque __main__ genera un JSON con el detalle (uso offline/manual).
"""

import json
import os
import warnings
from datetime import datetime
from os.path import basename
from urllib.parse import urlparse

import httpx
import urllib3
from bs4 import BeautifulSoup
from loguru import logger

from src.config import settings

# Suprimir advertencias InsecureRequestWarning
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

_DEFAULT_LOGO = "icon-default.webp"
_ENTIDAD_PATH = "/entidad/"


def count_entities_without_logo() -> int:
    """
    Consulta la pagina /entidad/ del sitio WordPress y cuenta cuantas
    entidades aun tienen el logo por defecto (icon-default.webp).

    Retorna -1 si no se puede obtener la pagina (error de red o config).
    """
    base = (settings.WP_URL or "").rstrip("/")
    if not base:
        logger.warning("WP_URL no configurada -- no se puede contar entidades sin logo.")
        return -1

    url = f"{base}{_ENTIDAD_PATH}"
    try:
        resp = httpx.get(url, verify=False, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"No se pudo consultar entidades sin logo: {exc}")
        return -1

    soup = BeautifulSoup(resp.text, "html.parser")
    count = sum(
        1
        for card in soup.select("a.entidad-card")
        if basename(urlparse((card.find("img") or {}).get("src", "")).path).lower() == _DEFAULT_LOGO
    )
    return count


# --- Uso manual / standalone --------------------------------------------------
if __name__ == "__main__":
    import requests  # solo para el script manual

    FOLDER_OUTPUT = "imagenes/01_pendientes"
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)

    base = (settings.WP_URL or "https://empleosperu.net").rstrip("/")
    url = f"{base}{_ENTIDAD_PATH}"

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    pendientes = []
    for card in soup.select("a.entidad-card"):
        href = card.get("href", "")
        slug = urlparse(href).path.strip("/").split("/")[-1]
        img_tag = card.find("img")
        src = img_tag.get("src", "").strip() if img_tag else ""
        filename = basename(urlparse(src).path).lower()
        if filename == _DEFAULT_LOGO:
            pendientes.append({"entidad": slug, "logo_url": "", "descargado": False})

    pendientes.sort(key=lambda x: x["entidad"].casefold())
    nombre_archivo = (
        f"{FOLDER_OUTPUT}/img-pendientes-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.json"
    )
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(pendientes, f, indent=4, ensure_ascii=False)
    print(f"JSON generado con {len(pendientes)} pendientes -> {nombre_archivo}")
