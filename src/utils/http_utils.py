

import os

from loguru import logger


def _get_ssl_verify_config() -> bool | str:
    """
    Configura verify para httpx desde variables de entorno.

    Prioridad:
    1) SCRAPING_CA_BUNDLE: ruta a archivo .pem/.crt con CA custom
    2) SCRAPING_VERIFY_SSL=false: desactiva validación (solo para debugging)
    3) True por defecto
    """
    ca_bundle = os.environ.get("SCRAPING_CA_BUNDLE")
    if ca_bundle:
        logger.info(f"Usando CA bundle custom: {ca_bundle}")
        return ca_bundle

    verify_ssl = os.environ.get("SCRAPING_VERIFY_SSL", "true").strip().lower()
    if verify_ssl in {"0", "false", "no", "off"}:
        logger.warning("SCRAPING_VERIFY_SSL=false: SSL verification desactivado")
        return False

    return True