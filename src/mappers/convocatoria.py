import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config import settings
from src.fetcher import fetch_page
from src.parser import enrich_item_with_detail
from src.schemas.convocatoria import ConvocatoriaV2
from src.utils.file_utils import export_items_json


OUTPUT_DIR = Path("output")
DEFAULT_ITEMS_JSON_PATH = OUTPUT_DIR / "03_convocatorias_origen.json"
DEFAULT_V2_JSON_PATH = OUTPUT_DIR / "04_convocatorias_formateada_v2.json"


def export_convocatorias_debug(
    convocatorias_v2: List[Dict[str, Any]],
    items_enriquecidos: List[Dict[str, Any]],
) -> None:
    """
    Exporta archivos debug:
    - output/04_convocatorias_formateada_v2.json
    - output/03_convocatorias_origen.json
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(DEFAULT_V2_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(convocatorias_v2, f, ensure_ascii=False, indent=2, default=str)
    logger.debug(f"JSON ConvocatoriaV2 actualizado: {DEFAULT_V2_JSON_PATH} ({len(convocatorias_v2)} items)")

    json_path = export_items_json(items_enriquecidos, str(DEFAULT_ITEMS_JSON_PATH))
    logger.debug(f"JSON de items enriquecidos actualizado: {json_path} ({len(items_enriquecidos)} items)")


def enrich_single(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Descarga la página de detalle y enriquece el item con sus datos completos.
    Si SCRAPING_FETCH_DETAIL_PAGES está deshabilitado, devuelve el item sin cambios.
    Lanza excepción si el fetch falla, para que el caller decida si aborta o no.
    """
    item_slug = item.get("slug") or item.get("url") or "?"
    with logger.contextualize(item_id=item.get("id", "?"), slug=item_slug):
        if settings.SCRAPING_FETCH_DETAIL_PAGES:
            logger.info(f"Enriqueciendo desde detalle: {item_slug}")
            return enrich_item_with_detail(item, fetch_page)
        return item


def map_to_v2(item_enriquecido: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte un item ya enriquecido al esquema ConvocatoriaV2 (sin HTTP)."""
    return ConvocatoriaV2.from_source(item_enriquecido).to_dict()
