
import json
import os
from typing import Literal

from src.utils.text_utils import normalizar_texto


TaxonomyType = Literal["departamentos", "contratos", "entidades", "medias"]



def load_taxonomy_json(name: TaxonomyType):
    """
    Loads and returns the taxonomy list from src/data/<name>.json
    Only allowed: 'departamentos', 'contratos', 'entidades', 'medias'
    """   
    path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{name}.json')
    path = os.path.abspath(path)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── Clasificación de enlaces por palabras clave ──

# Orden de prioridad y palabras clave para clasificar documentos
_KEYWORDS_CONFIG = [
    {"category": "bases",        "keywords": ["bases"],        "label_tpl": "Bases del proceso"},
    {"category": "cronograma",   "keywords": ["cronograma"],   "label_tpl": "Cronograma"},
    {"category": "anexo",        "keywords": ["anexo"],        "label_tpl": "Anexos"},
    {"category": "comunicados",  "keywords": ["comunicado", "comunicados"], "label_tpl": "Comunicados"},
]

_CATEGORY_ORDER = {"bases": 0, "cronograma": 1, "anexo": 2, "comunicados": 3, "otros": 4}


def _classify_document(label: str) -> tuple[str, str]:
    """
    Clasifica un documento por su label y devuelve (category, display_label).
    Para anexos extrae el texto descriptivo del label original.
    """
    label_lower = label.lower()
    for cfg in _KEYWORDS_CONFIG:
        for kw in cfg["keywords"]:
            if kw in label_lower:
                if cfg["category"] == "anexo":
                    # Extraer texto descriptivo después de separadores comunes
                    detail = _extract_anexo_detail(label)
                    display = f"Anexos - {detail}" if detail else "Anexos"
                    return cfg["category"], display
                return cfg["category"], cfg["label_tpl"]
    return "otros", "Otros"


def _extract_anexo_detail(label: str) -> str:
    """
    Intenta extraer la descripción del anexo del label.
    Ej: 'Ver aquí ANEXO N° 05 – Ficha de resumen Curricular'
        → 'Ficha de resumen Curricular'
    """
    import re
    # Buscar texto después de '–' o '-' que sigue al número de anexo
    match = re.search(r'anexo\s*n[°º]?\s*\d+[^–\-]*[–\-]\s*(.+)', label, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Si no hay separador, buscar texto después de "ANEXO N° XX"
    match = re.search(r'anexo\s*n[°º]?\s*[\d]+\s+al\s+[\d]+\s*[–\-]\s*(.+)', label, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: quitar prefijo "Ver aquí" y devolver lo que queda
    cleaned = re.sub(r'^ver\s+aqu[ií]\s*', '', label, flags=re.IGNORECASE).strip()
    if cleaned.lower() != label.lower():
        return cleaned
    return ""


def clasificar_enlaces(documents: list[dict]) -> list[dict]:
    """
    Recibe la lista de documentos (application.documents) y devuelve
    una lista ordenada de enlaces clasificados para conv_enlaces.

    Cada elemento: {"label": str, "url": str, "category": str}

    Orden: bases → cronograma → anexos → comunicados → otros
    """
    result = []
    for doc in documents:
        label = doc.get("label", "")
        url = doc.get("url", "")
        if not url:
            continue
        category, display_label = _classify_document(label)
        result.append({"label": display_label, "url": url, "category": category})

    # Ordenar por prioridad de categoría
    result.sort(key=lambda x: _CATEGORY_ORDER.get(x["category"], 99))
    return result


def get_id_by_slug(slug, taxonomy_type: TaxonomyType):
    """
    Returns the id for a slug in the given taxonomy ('departamentos', 'contratos', 'entidades', 'medias').
    Strictly enforces allowed taxonomy types.
    """
    allowed = {"departamentos", "contratos", "entidades", "medias"}
    if taxonomy_type not in allowed:
        raise ValueError(f"Only allowed: {', '.join(allowed)}. Got: {taxonomy_type}")
    
    taxonomy_list = load_taxonomy_json(taxonomy_type)
    slug_norm = normalizar_texto(slug)
    for item in taxonomy_list:
        slug_item_norm = item['slug']
        name_norm = normalizar_texto(item['name'])
        if slug_norm == name_norm or slug_norm == slug_item_norm:
            return item['id']
    return None  # Default to "Uncategorized"