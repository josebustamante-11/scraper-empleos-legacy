import re
from datetime import datetime
from typing import Any, Optional
from src.utils.text_utils import normalizar_texto
from loguru import logger


def _parse_datetime(value: Optional[str]) -> Optional[str]:
    """
    Normaliza fechas a ISO-8601 si vienen como 'YYYY-MM-DD HH:MM:SS'.
    Devuelve string ISO o None si no se puede parsear.
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        return int(value)
    except Exception:
        return default


def _format_spanish_date(iso_date: str) -> str:
    """
    Convierte una fecha ISO (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS) a formato '29 de marzo del 2026'.
    Si el valor es inválido, retorna 'No especificado'.
    """
    meses = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    if not iso_date or not isinstance(iso_date, str):
        return 'No especificado'
    try:
        fecha = iso_date[:10].split('-')
        anio = fecha[0]
        mes = int(fecha[1])
        dia = int(fecha[2])
        return f"{dia} de {meses[mes-1]} del {anio}"
    except Exception:
        return 'No especificado'


def _extract_codigo_from_title(title: str) -> str:
    """
    Extrae el código de un título de convocatoria a partir del marcador de número.
    Soporta variantes como 'N° 006 - 09', 'Nº 123', 'No. 45', 'Nro 020', etc.
    Devuelve el primer match encontrado o una cadena vacía si no hay coincidencia.
    """
    import re

    if not isinstance(title, str):
        return ""

    pattern = re.compile(
        r"\b(N(?:[°º]|ro\.?|ro|o\.?|umero|úmero)\s*\d+(?:\s*[-/]\s*[A-Za-z0-9]+)*)\b",
        flags=re.IGNORECASE,
    )
    match = pattern.search(title)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()

    return ""


def tiene_colegiatura(educations: list[str]) -> str:
    """
    Clasifica el requisito de colegiatura en una de estas opciones:
    - 'No requerida'
    - 'Requerida'
    - 'Colegiado y habilitado'
    """
    keywords_requerida = [
        "colegiatura",
        "colegiado",
        "matricula profesional",
        "registro profesional",
        "inscripcion en colegio",
        "registro en colegio",
        "colegiacion",
        "habilitacion profesional",
        "habilitacion",
    ]
    keywords_colegiado = ["colegiado", "colegiatura", "colegiacion"]
    keywords_habilitado = ["habilitado", "habilitacion", "habilitacion profesional"]

    requiere = False
    es_colegiado = False
    es_habilitado = False

    for edu in educations:
        if not isinstance(edu, str):
            continue

        edu_normalizado = normalizar_texto(edu)

        if any(normalizar_texto(kw) in edu_normalizado for kw in keywords_requerida):
            requiere = True
        if any(normalizar_texto(kw) in edu_normalizado for kw in keywords_colegiado):
            es_colegiado = True
        if any(normalizar_texto(kw) in edu_normalizado for kw in keywords_habilitado):
            es_habilitado = True

        if es_colegiado and es_habilitado:
            return "Colegiado y habilitado"

    if requiere:
        return "Requerida"

    return "No requerida"


def obtener_sueldo(texto: Any) -> float | None:
    """
    Extrae el primer monto en soles (S/) del texto y lo convierte en float.
    Soporta entradas no ideales (dict, list, None).
    Devuelve None si no encuentra ningún monto válido.
    """

    if not texto:
        return None

    # ✅ Normalización defensiva (scraping real)
    if isinstance(texto, dict):
        # unir valores del dict en una sola cadena
        texto = " ".join(str(v) for v in texto.values() if v)

    elif isinstance(texto, (list, tuple, set)):
        texto = " ".join(str(v) for v in texto if v)

    elif not isinstance(texto, str):
        texto = str(texto)

    # Seguridad extra
    texto = texto.strip()
    if not texto:
        return None

    patron = r"S/\s*([\d.,]+)"
    match = re.search(patron, texto)

    if not match:
        return None

    monto = match.group(1).strip()
    if not monto:
        return None

    # ✅ eliminar separadores de miles
    monto = monto.replace(",", "")

    try:
        return float(monto)
    except ValueError:
        logger.warning(f"No se pudo convertir monto a float: {monto!r}")
        return None

