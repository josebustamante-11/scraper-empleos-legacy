
import json
import os


DEFAULT_JSON_PATH = os.path.join("output", "last_extraction.json")


def export_items_json(items: list[dict], output_path: str = DEFAULT_JSON_PATH) -> str:
    """Guarda la extracción normalizada en un archivo JSON legible."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(items, file, ensure_ascii=False, indent=2)
    return output_path

def load_json_file(path: str):
    """Carga y retorna el contenido de un archivo JSON como lista o dict."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)