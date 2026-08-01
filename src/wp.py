"""
wp.py — Publica posts en WordPress via REST API

Cómo obtener el Application Password de WordPress:
    1. Entrá a tu WP admin → Usuarios → Tu perfil
    2. Bajá hasta "Contraseñas de aplicación"
    3. Nombre: "GitHub Scraper" → Agregar
    4. WP te genera algo como: "xxxx xxxx xxxx xxxx xxxx xxxx"
    5. Guardalo — no lo vas a ver de nuevo
    6. Pegalo en el .env como WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

Requisitos:
    - WordPress 5.6 o superior
    - HTTPS habilitado en tu sitio (obligatorio para App Passwords)
    - REST API habilitada (está habilitada por defecto)
"""

import json
import os
import httpx

from base64 import b64encode
from loguru import logger
from src.render import render_convocatoria_html
from src.utils.http_utils import _get_ssl_verify_config
from src.services.wp_cache import WP_CACHE
from src.utils.wp_utils import clasificar_enlaces


def obtener_meta_data(item: dict) -> dict:
    # fecha_inicio = item.get("application_period", {}).get("start_date")
    fecha_fin = item.get("dates", {}).get("deadline")
    # Si la fecha tiene formato tipo '2026-03-29T23:59:00', extraer solo la parte de la fecha
    if isinstance(fecha_fin, str) and 'T' in fecha_fin:
        fecha_fin = fecha_fin.split('T')[0]
    nro_vacantes = item.get("vacancies", 1)
    nivel_educativo = ", ".join(item.get("requirements", {}).get("education", [])) or "No especificado"

    remuneracion = item.get("salary", {}).get("amount", "No especificado")
    # Si remuneracion es un número float y termina en .0, convertir a int
    if isinstance(remuneracion, float):
        if remuneracion.is_integer():
            remuneracion = int(remuneracion)
    # Si es un string que representa un número float, intentar convertir
    elif isinstance(remuneracion, str):
        try:
            remuneracion_float = float(remuneracion)
            if remuneracion_float.is_integer():
                remuneracion = int(remuneracion_float)
            else:
                remuneracion = remuneracion_float
        except Exception:
            pass
    lugar_trabajo = item.get("location", {}).get("city", "No especificado")
    formacion_academica = ", ".join(item.get("requirements", {}).get("careers", [])) or "No especificado"
    estado = item.get("status", "vigente")
    colegiatura = item.get("requirements", {}).get("colegiatura", 'No requerida')
    enlaces_raw = item.get("application", {}).get("documents", [])
    enlaces = clasificar_enlaces(enlaces_raw)

    # Experiencia: lista de strings bajo requirements.experience.details
    experiencia_items = (
        item.get("requirements", {}).get("experience", {}).get("details") or []
    )
    experiencia = "\n".join(experiencia_items) if experiencia_items else ""

    # Cursos y programas de especialización
    cursos_items = item.get("requirements", {}).get("courses") or []
    cursos = "\n".join(cursos_items) if cursos_items else ""

    # Conocimientos técnicos
    conocimientos_items = item.get("requirements", {}).get("knowledge") or []
    conocimientos = "\n".join(conocimientos_items) if conocimientos_items else ""

    meta_data = {
        "conv_fecha_fin": fecha_fin or "",
        "conv_vacantes": str(nro_vacantes),
        "conv_nivel_educativo": nivel_educativo,
        "conv_remuneracion": str(remuneracion),
        "conv_lugar_trabajo": lugar_trabajo or "No especificado",
        "conv_formacion_academica": formacion_academica,
        "conv_estado": estado or "vigente",
        "conv_colegiatura": colegiatura or "No requerida",
        "conv_enlaces": json.dumps(enlaces, ensure_ascii=False),
        "conv_experiencia": experiencia,
        "conv_cursos": cursos,
        "conv_conocimientos": conocimientos,
    }
    return meta_data
# ─────────────────────────────────────────
# CONFIGURACIÓN — ajustá si es necesario
# ─────────────────────────────────────────

# Estado del post al publicar
# "publish" = publicado inmediatamente
# "draft"   = borrador (recomendado para pruebas)
# "pending" = pendiente de revisión
WP_STATUS_PUBLISH = "publish"
WP_STATUS_DRAFT = "draft"
WP_STATUS_PENDING = "pending"
DEFAULT_STATUS = WP_STATUS_PUBLISH

# Categoría por defecto (ID numérico de la categoría en WP)
# None = sin categoría (usa la categoría por defecto de WP)
# Para encontrar el ID: WP Admin → Posts → Categorías → pasa el mouse sobre la categoría
DEFAULT_CATEGORY_ID = 1  # Ejemplo: 5


# Media por defecto (ID numérico de la media en WP)
# Default: ícono genérico (ID=DEFAULT_MEDIA_ID) — reemplazar por el ID de tu media genérica en WP
DEFAULT_MEDIA_ID = 431  # Ejemplo: 5
# ─────────────────────────────────────────


def _get_auth_header() -> dict:
    """Construye el header de autenticación Basic para la WP REST API."""
    wp_user = os.environ.get("WP_USER")
    wp_password = os.environ.get("WP_APP_PASSWORD")

    if not wp_user or not wp_password:
        raise ValueError(
            "WP_USER o WP_APP_PASSWORD no están configurados. "
            "Definílos en el .env o en los GitHub Secrets."
        )

    credentials = f"{wp_user}:{wp_password}"
    encoded = b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


def _get_wp_url() -> str:
    """Retorna la URL base de la WP REST API."""
    wp_url = os.environ.get("WP_URL")
    if not wp_url:
        raise ValueError("WP_URL no está configurado.")
    # Asegura que no tenga slash al final
    return wp_url.rstrip("/")


def publish_post(item: dict) -> int:

    content = render_convocatoria_html({'convocatoria': item}, output_path=None)
    meta_data = obtener_meta_data(item)

    departamento_slug = item.get("location", {}).get("region", None)
    departamento_id = WP_CACHE.get_or_create_departamento(departamento_slug)

    carrera_slugs = item.get("requirements", {}).get("careers", [])
    carrera_ids = WP_CACHE.get_ids_by_slugs(carrera_slugs, "carreras")

    nivel_academico_slugs = item.get("requirements", {}).get("academic_level", [])
    nivel_academico_ids = WP_CACHE.get_ids_by_slugs(nivel_academico_slugs, "nivel_academico")

    logger.debug(f"nivel_academico_slugs: {nivel_academico_slugs} → ids: {nivel_academico_ids}")

    contrato_slug = item.get("employment", {}).get("contract_mode", None)
    contrato_id = WP_CACHE.get_or_create_contrato(contrato_slug)

    entidad_name = item.get("organization", {}).get("name", None)
    entidad_id = WP_CACHE.get_or_create_entidad(entidad_name)
    entidad_slug = WP_CACHE.get_slug_by_id(entidad_id, "entidades") if entidad_id else None

    media_id = WP_CACHE.get_id_by_slug(f"icon-{entidad_slug}", "medias") if entidad_slug else None
    if not media_id and DEFAULT_MEDIA_ID:
        media_id = DEFAULT_MEDIA_ID

    title = item.get("title", "Convocatoria sin título")

    # El post siempre se publica. Las taxonomías se añaden si están disponibles;
    # si falta alguna se omite ese campo pero NO se bloquea la publicación.
    payload = {
        "title": title,
        "status": WP_STATUS_PUBLISH,
        "meta": meta_data,
    }

    if media_id:
        payload["featured_media"] = media_id

    if entidad_id:
        payload["entidad"] = [entidad_id]
    if contrato_id:
        payload["contrato"] = [contrato_id]
    if departamento_id:
        payload["departamento"] = [departamento_id]
    if carrera_ids:
        payload["carrera"] = carrera_ids
    if nivel_academico_ids:
        payload["nivel_academico"] = nivel_academico_ids

    if content:
        payload["content"] = content
    else:
        payload["content"] = "No se pudo generar el contenido de la convocatoria."
        logger.warning(f"El item '{title}' no tiene contenido HTML generado.")

    # return 1 # Simulación: retorna un ID de post ficticio para pruebas
    wp_url = _get_wp_url()
    headers = {
        **_get_auth_header(),
        "Content-Type": "application/json",
    }

    response = httpx.post(
        f"{wp_url}/wp-json/wp/v2/empleos-cpt",
        headers=headers,
        json=payload,
        timeout=30,
        verify=_get_ssl_verify_config(),
    )

    if response.is_error:
        try:
            error_body = response.json()
            wp_message = error_body.get("message") or error_body.get("data", {}).get("details") or str(error_body)
        except Exception:
            wp_message = response.text[:500]
        logger.error(f"WordPress rechazó el post '{title}': [{response.status_code}] {wp_message}")
        response.raise_for_status()

    post_data = response.json()
    post_id = post_data["id"]
    post_link = post_data.get("link", "")

    logger.info(f"Post creado en WP: ID={post_id} | URL={post_link}")
    
    return post_id
 
