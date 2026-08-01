import re
from typing import Dict, List, Optional, Any


# Marcadores de sección conocidos (orden importa para delimitar fronteras).
# Cada tupla: (clave_interna, patrón regex).
# Las claves que empiezan con "_" son stop-markers y se descartan.
SECTION_MARKERS = [
    ("vacancies",  r"N[úu]mero\s+de\s+vacantes\s*:"),
    ("education",  r"Formaci[oó]n\s+Acad[eé]mica\s*:"),
    ("experience", r"Experiencia\s*:"),
    ("knowledge",  r"Conocimiento(?:s)?(?:\s+t[eé]cnico(?:s)?)?\s*:"),
    ("courses",    r"Cursos(?:\s+y/?o?\s+programas\s+de\s+especializaci[oó]n)?\s*:"),
    ("_stop",      r"Lugar\s+de\s+prestaci[oó]n\s+del\s+servicio\s*:"),
    ("_stop",      r"Remuneraci[oó]n\s*:"),
    ("_stop",      r"Plazo\s+para\s+postular\s*:"),
    ("_stop",      r"C[OÓ]MO\s+POSTULAR\s*:"),
]

_MARKERS_PATTERN = "|".join(f"(?P<m{i}>{pat})" for i, (_, pat) in enumerate(SECTION_MARKERS))
_MARKERS_RE = re.compile(_MARKERS_PATTERN, flags=re.IGNORECASE)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_requirements_blob(standardized: Dict[str, Any]) -> str:
    """
    Obtiene el texto más completo de requisitos disponible en el JSON estandarizado.
    Prioriza `visible_sections.Requisitos` y `sections.requirements` porque
    contienen solo la parte de requisitos (sin condiciones de contrato ni postulación).
    """
    raw = (standardized.get("raw") or {})
    visible = (raw.get("visible_sections") or {}).get("Requisitos", "")
    sections_req = (standardized.get("sections") or {}).get("requirements", "")
    profile = standardized.get("profile") or {}
    academic = profile.get("academic_requirements") or ""

    candidates = [visible, sections_req, academic]
    best = ""
    for c in candidates:
        if isinstance(c, str):
            normalized = _normalize(c)
            if len(normalized) > len(best):
                best = normalized
    return best


def split_sections(blob: str) -> Dict[str, str]:
    """
    Divide un texto de requisitos en secciones etiquetadas usando los marcadores conocidos.
    Retorna un dict con claves como 'education', 'experience', 'courses', 'knowledge'.
    """
    if not blob:
        return {}

    matches = list(_MARKERS_RE.finditer(blob))
    if not matches:
        return {}

    result: Dict[str, str] = {}
    for idx, match in enumerate(matches):
        # Determinar a qué marcador pertenece
        marker_index = next(i for i in range(len(SECTION_MARKERS)) if match.group(f"m{i}") is not None)
        key = SECTION_MARKERS[marker_index][0]

        if key.startswith("_"):
            continue

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(blob)
        section_text = _normalize(blob[start:end]).strip(" .;:-")

        if key == "vacancies":
            continue

        if section_text and key not in result:
            result[key] = section_text

    return result


def parse_education(blob: str, profile: Dict[str, Any]) -> List[str]:
    """
    Extrae la formación académica con tres niveles de fallback:
    1. Blob segmentado (marcador "Formación Académica:").
    2. profile.academic_requirements.
    3. Preamble del blob: texto antes de la primera oración de experiencia,
       cubriendo el patrón "Requisitos: <título académico>. Experiencia general..."
    """
    sections = split_sections(blob)
    edu = sections.get("education", "")

    if not edu:
        raw = profile.get("academic_requirements") or ""
        if isinstance(raw, str) and raw.strip():
            edu = _normalize(raw.split("Experiencia:")[0]).strip(" .;:-")

    if not edu and blob:
        prefix = re.compile(r"(?i)^(requisitos?|perfil\s+del\s+puesto)\s*:\s*")
        cleaned = prefix.sub("", _normalize(blob))
        exp_match = re.search(
            r"\bExperiencia\s+(?:general|espec[ií]fica|laboral|en\s+el|m[ií]nima)\b",
            cleaned,
            re.IGNORECASE,
        )
        if exp_match:
            candidate = cleaned[:exp_match.start()].strip(" .;:-")
        else:
            period = re.search(r"\.\s+[A-ZÁÉÍÓÚÑ]", cleaned)
            candidate = cleaned[:period.start() + 1].strip(" .;:-") if period else ""
        if candidate:
            edu = candidate

    return [edu] if edu else []


def _split_experience_items(text: str) -> List[str]:
    """
    Divide un bloque de experiencia en sub-items individuales.
    Detecta sub-etiquetas como:
      - 'Experiencia laboral general:'
      - 'Experiencia específica en la función o materia:'
      - 'Experiencia específica en el puesto o cargo:'
      - 'Experiencia en el sector público:'
      - 'Experiencia general:'
      - 'Experiencia Especifica:'
    """
    if not text:
        return []

    # Patrón que detecta el inicio de cada sub-etiqueta de experiencia
    split_re = re.compile(
        r"(?=\bExperiencia\s+(?:laboral\s+)?(?:general|espec[ií]fica|en\s+el\s+sector)\b)",
        flags=re.IGNORECASE,
    )

    parts = split_re.split(text)
    items = []
    for part in parts:
        cleaned = _normalize(part).strip(" .;:-")
        if not cleaned:
            continue
        items.append(cleaned)
    return items


def parse_experience(blob: str, profile: Dict[str, Any]) -> List[str]:
    """
    Extrae la experiencia.
    1. Intenta desde el blob segmentado.
    2. Fallback: profile.experience (lista), limpiando prefijos y contaminación.
    En ambos casos, subdivide en items individuales por sub-etiqueta.
    """
    sections = split_sections(blob)
    exp = sections.get("experience", "")

    if exp:
        return _split_experience_items(exp)

    raw_list = profile.get("experience")
    if not isinstance(raw_list, list):
        return []

    # Marcadores que indican contaminación (otra sección metida en experience)
    contamination = re.compile(
        r"(?i)(?:Conocimiento(?:s)?\s*(?:t[eé]cnico)?|Cursos\s+y/?o?\s+programas|Formaci[oó]n\s+Acad[eé]mica)\s*:",
    )

    merged = ""
    for item in raw_list:
        if not isinstance(item, str):
            continue
        cleaned = _normalize(item)
        if not cleaned:
            continue
        # Remover prefijo suelto "Experiencia:"
        if cleaned.lower().startswith("experiencia:"):
            cleaned = cleaned[len("Experiencia:"):].strip()
        # Cortar si hay contaminación
        m = contamination.search(cleaned)
        if m:
            cleaned = cleaned[:m.start()].strip(" .;:-")
        if cleaned:
            merged = f"{merged} {cleaned}" if merged else cleaned

    return _split_experience_items(merged)


def parse_courses(blob: str, profile: Dict[str, Any]) -> List[str]:
    """
    Extrae cursos y/o programas de especialización.
    1. Intenta desde el blob segmentado.
    2. Fallback: profile.courses (lista), limpiando prefijos.
    """
    sections = split_sections(blob)
    courses = sections.get("courses", "")

    if courses:
        return [courses]

    raw_list = profile.get("courses")
    if not isinstance(raw_list, list):
        return []

    prefix_re = re.compile(r"(?i)^cursos\s+y/?o?\s+programas\s+de\s+especializaci[oó]n\s*:\s*")
    result = []
    for item in raw_list:
        if not isinstance(item, str):
            continue
        cleaned = _normalize(item)
        cleaned = prefix_re.sub("", cleaned).strip(" .;:-")
        if cleaned:
            result.append(cleaned)

    return result


def parse_knowledge(blob: str, profile: Dict[str, Any]) -> List[str]:
    """
    Extrae conocimientos.
    1. Intenta desde el blob segmentado.
    2. Fallback: profile.knowledge (lista), limpiando contaminación.
    """
    sections = split_sections(blob)
    knowledge = sections.get("knowledge", "")

    if knowledge:
        return [knowledge]

    raw_list = profile.get("knowledge")
    if not isinstance(raw_list, list):
        return []

    # Marcadores que indican contaminación
    contamination = re.compile(
        r"(?i)(?:Experiencia|Cursos\s+y/?o?\s+programas|Formaci[oó]n\s+Acad[eé]mica)\s*:",
    )

    result = []
    for item in raw_list:
        if not isinstance(item, str):
            continue
        cleaned = _normalize(item)
        if not cleaned:
            continue
        # Remover prefijo "Conocimiento técnico:"
        prefix = re.match(r"(?i)^conocimiento(?:s)?(?:\s+t[eé]cnico(?:s)?)?\s*:\s*", cleaned)
        if prefix:
            cleaned = cleaned[prefix.end():]
        # Cortar si hay contaminación
        m = contamination.search(cleaned)
        if m:
            cleaned = cleaned[:m.start()].strip(" .;:-")
        if cleaned:
            result.append(cleaned)

    return result
