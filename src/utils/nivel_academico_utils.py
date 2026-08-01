import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache


CAREERS_JSON_PATH = Path("src/data/nivel_academico.json")


def normalizar_texto(texto: str) -> str:
    """
    Convierte a minúsculas, elimina tildes y limpia espacios.
    """
    if not isinstance(texto, str):
        return ""

    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto


@lru_cache(maxsize=1)
def load_careers_index() -> list[dict]:
    """
    Carga careers.json una sola vez y deja los keywords ya normalizados.
    """
    with CAREERS_JSON_PATH.open("r", encoding="utf-8") as f:
        careers = json.load(f)

    index = []

    for career in careers:
        keywords = career.get("keywords", [])
        raw_patterns = career.get("patterns", [])

        normalized_keywords = sorted(
            {
                normalizar_texto(k)
                for k in keywords
                if isinstance(k, str) and k.strip()
            },
            key=len,
            reverse=True  # más largos primero, ayuda a evitar match débiles
        )

        compiled_patterns = []
        for p in raw_patterns:
            try:
                compiled_patterns.append(re.compile(p))
            except re.error:
                pass

        index.append({
            "id": career.get("id"),
            "name": career.get("name"),
            "slug": career.get("slug"),
            "allow_update": career.get("allow_update", False),
            "keywords": normalized_keywords,
            "patterns": compiled_patterns,
        })

    return index


def extract_academic_level_from_education(education_list: list[str]) -> list[str]:
    """
    Busca coincidencias de niveles académicos dentro de los textos de education_list.
    Devuelve una lista de nombres de niveles académicos encontrados, sin duplicados.
    """
    found = set()
    careers_index = load_careers_index()

    for edu in education_list:
        if not isinstance(edu, str) or not edu.strip():
            continue

        edu_normalizado = normalizar_texto(edu)

        for career in careers_index:
            matched = False
            for keyword in career["keywords"]:
                if keyword in edu_normalizado:
                    found.add(career["name"])
                    matched = True
                    break

            if not matched:
                for pattern in career["patterns"]:
                    if pattern.search(edu_normalizado):
                        found.add(career["name"])
                        break

    return sorted(found)