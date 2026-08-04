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


def obtener_sueldo_old(texto: Any) -> float | None:
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



def obtener_sueldo(texto: Any) -> float | None:
    """
    Extrae y convierte el primer importe monetario válido encontrado en el texto.

    Descripción:
        Función robusta para procesar montos provenientes de scraping,
        independientemente de la moneda utilizada y del formato de
        separadores de miles y decimales.

    Soporta, entre otros, los siguientes formatos:

        S/ 5,000.00
        S/ 5.000,00
        S/ 5000.00
        S/ 5000
        $ 5,000.00
        $5,000.00
        USD 5,000.00
        EUR 1.500,50
        € 1.500,50
        PEN 5,000.00
        5,000.00
        5.000,00

    También maneja valores provenientes de:
        - str
        - dict
        - list
        - tuple
        - set
        - valores numéricos

    Criterios de interpretación:
        - Si existen coma y punto, se determina el separador decimal
          utilizando la posición y cantidad de dígitos posteriores.
        - Si solo existe un separador:
            * 1 o 2 dígitos después → se considera decimal.
            * 3 dígitos después → se considera separador de miles.
        - Si existen múltiples puntos o comas, se interpreta el último
          separador como decimal cuando el formato es consistente.
        - Se eliminan símbolos de moneda y espacios.
        - Se rechazan valores claramente inválidos o corruptos.
        - No depende de una moneda específica.

    Ejemplos:
        "S/ 5,000.00"   → 5000.0
        "S/ 5.000,00"   → 5000.0
        "$ 5,000.00"    → 5000.0
        "€ 1.500,50"    → 1500.5
        "USD 2500"      → 2500.0
        "5,000"         → 5000.0
        "5.000"         → 5000.0
        "5,50"          → 5.5
        "5.50"          → 5.5

    Args:
        texto: Texto, colección o valor numérico que contiene el importe.

    Returns:
        float | None:
            Importe convertido a float o None cuando no se encuentra
            un importe válido.
    """

    if texto is None:
        return None

    # ---------------------------------------------------------
    # 1. Normalización del valor de entrada
    # ---------------------------------------------------------

    if isinstance(texto, bool):
        return None

    if isinstance(texto, (int, float)):
        return float(texto)

    if isinstance(texto, dict):
        texto = " ".join(
            str(v) for v in texto.values()
            if v is not None and str(v).strip()
        )

    elif isinstance(texto, (list, tuple, set)):
        texto = " ".join(
            str(v) for v in texto
            if v is not None and str(v).strip()
        )

    elif not isinstance(texto, str):
        texto = str(texto)

    texto = texto.strip()

    if not texto:
        return None

    # ---------------------------------------------------------
    # 2. Buscar un posible importe
    # ---------------------------------------------------------
    #
    # Se permite encontrar:
    #
    #   S/ 5,000.00
    #   $5,000.00
    #   USD 5000
    #   EUR 1.500,50
    #   5000.00
    #
    # No se obliga a que exista un símbolo de moneda.

    patron = r"""
        (?:
            [A-Za-z]{3}\s* |
            [^\d\s.,]+\s*
        )?
        (
            \d[\d.,]*
        )
    """

    match = re.search(patron, texto, flags=re.VERBOSE)

    if not match:
        return None

    monto = match.group(1).strip()

    if not monto:
        return None

    # ---------------------------------------------------------
    # 3. Validación básica
    # ---------------------------------------------------------

    if not re.fullmatch(r"\d[\d.,]*", monto):
        logger.warning(
            f"Formato de monto no válido: {monto!r}"
        )
        return None

    # Evitar formatos obviamente corruptos.
    #
    # Ejemplo:
    #   .3300.00
    #
    # Este valor no debería llegar al parser porque comienza
    # con un separador.
    if monto.startswith((".", ",")):
        logger.warning(
            f"Formato de monto sospechoso: {monto!r}"
        )
        return None

    # ---------------------------------------------------------
    # 4. Determinar separadores
    # ---------------------------------------------------------

    cantidad_puntos = monto.count(".")
    cantidad_comas = monto.count(",")

    # ---------------------------------------------------------
    # 5. Punto y coma presentes
    # ---------------------------------------------------------

    if cantidad_puntos > 0 and cantidad_comas > 0:

        ultimo_punto = monto.rfind(".")
        ultima_coma = monto.rfind(",")

        # El separador que aparece último se considera decimal.
        if ultimo_punto > ultima_coma:
            # Ejemplo:
            # 5,000.00
            monto = monto.replace(",", "")

        else:
            # Ejemplo:
            # 5.000,00
            monto = monto.replace(".", "")
            monto = monto.replace(",", ".")

    # ---------------------------------------------------------
    # 6. Solo puntos
    # ---------------------------------------------------------

    elif cantidad_puntos > 0:

        partes = monto.split(".")

        if cantidad_puntos == 1:

            parte_entera, parte_decimal = partes

            # 5.50 → decimal
            # 5.00 → decimal
            # 5.5  → decimal
            if len(parte_decimal) in (1, 2):
                monto = f"{parte_entera}.{parte_decimal}"

            # 5.000 → separador de miles
            elif len(parte_decimal) == 3:
                monto = monto.replace(".", "")

            else:
                # Formato poco habitual.
                # Se conserva el último punto como decimal.
                monto = (
                    "".join(partes[:-1])
                    + "."
                    + partes[-1]
                )

        else:
            # Ejemplo:
            # 1.500.00 → 1500.00
            #
            # Los primeros puntos se consideran separadores
            # de miles y el último punto decimal.

            parte_entera = "".join(partes[:-1])
            parte_decimal = partes[-1]

            if len(parte_decimal) in (1, 2):
                monto = f"{parte_entera}.{parte_decimal}"

            elif len(parte_decimal) == 3:
                # Ejemplo:
                # 1.500.000
                #
                # Todos son separadores de miles.
                monto = "".join(partes)

            else:
                logger.warning(
                    f"Formato de monto sospechoso: {monto!r}"
                )
                return None

    # ---------------------------------------------------------
    # 7. Solo comas
    # ---------------------------------------------------------

    elif cantidad_comas > 0:

        partes = monto.split(",")

        if cantidad_comas == 1:

            parte_entera, parte_decimal = partes

            # 5,50 → decimal
            # 5,00 → decimal
            if len(parte_decimal) in (1, 2):
                monto = f"{parte_entera}.{parte_decimal}"

            # 5,000 → miles
            elif len(parte_decimal) == 3:
                monto = monto.replace(",", "")

            else:
                logger.warning(
                    f"Formato de monto sospechoso: {monto!r}"
                )
                return None

        else:
            # Ejemplo:
            # 1,500,000 → miles
            #
            # Se considera el último separador decimal
            # solamente si tiene 1 o 2 dígitos.

            parte_decimal = partes[-1]

            if len(parte_decimal) in (1, 2):
                parte_entera = "".join(partes[:-1])
                monto = f"{parte_entera}.{parte_decimal}"

            elif len(parte_decimal) == 3:
                monto = "".join(partes)

            else:
                logger.warning(
                    f"Formato de monto sospechoso: {monto!r}"
                )
                return None

    # ---------------------------------------------------------
    # 8. Conversión final
    # ---------------------------------------------------------

    try:
        resultado = float(monto)

        if resultado < 0:
            return None

        return resultado

    except (ValueError, TypeError):
        logger.warning(
            f"No se pudo convertir monto a float: {monto!r}"
        )
        return None