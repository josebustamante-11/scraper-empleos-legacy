"""
sources.py — Registro de fuentes de scraping.

Cada ScrapingSource define cómo y dónde scrapear (URL, paginación,
delay entre items, headers, etc.).

Las fuentes se cargan desde src/data/sources.json.
Si el archivo no existe o tiene errores, se usa SCRAPING_TARGET_URL del .env
como fallback de fuente única (compatibilidad con configuraciones existentes).

Para agregar una nueva fuente (sitio oficial de una entidad):
    1. Editar src/data/sources.json
    2. Agregar un objeto con al menos {id, name, base_url}
    3. Reiniciar el scraper — no se requieren cambios en el código

El campo base_url soporta referencias a variables de entorno:
    "base_url": "${MI_URL}"  →  se resuelve automáticamente al cargar
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import settings

SOURCES_FILE = Path("src/data/sources.json")


# ─────────────────────────────────────────────────────────────────────────────
# MODELO
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ScrapingSource:
    """Define una fuente de scraping (sitio web / entidad pública)."""

    id: str
    name: str
    base_url: str
    max_pages: int = 10
    enabled: bool = True

    # Paginación (se construye con page_url())
    page_param: str = "page"
    sort_param: Optional[str] = "sort=1-id"

    # Rate limiting — segundos de espera entre cada item procesado
    batch_delay: float = 1.0

    # Headers extra (útil para sitios con autenticación o cookies)
    extra_headers: dict = field(default_factory=dict)

    def page_url(self, page: int) -> str:
        """Genera la URL para una página numerada."""
        if page == 1:
            return self.base_url
        params = [f"{self.page_param}={page}"]
        if self.sort_param:
            params.append(self.sort_param)
        return f"{self.base_url}?{'&'.join(params)}"

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingSource":
        """Crea una instancia desde un dict, ignorando claves desconocidas."""
        valid = set(cls.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in valid}
        # Resolver ${VAR} en todos los campos que pueden referenciar variables de entorno
        resolvable = ("base_url", "id", "name", "page_param", "sort_param",
                      "max_pages", "batch_delay")
        for key in resolvable:
            if isinstance(filtered.get(key), str):
                filtered[key] = _resolve_env_refs(filtered[key])
        # Convertir campos numéricos (pueden venir como strings tras resolver env vars)
        for key, cast in (("max_pages", int), ("batch_delay", float)):
            if isinstance(filtered.get(key), str):
                try:
                    filtered[key] = cast(filtered[key])
                except (ValueError, TypeError):
                    logger.warning(f"No se pudo convertir '{key}' a número: {filtered[key]!r}")
        return cls(**filtered)


# ─────────────────────────────────────────────────────────────────────────────
# LOADER
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_env_refs(value: str) -> str:
    """Reemplaza ${VAR_NAME} por el valor de la variable de entorno correspondiente."""
    return re.sub(
        r"\$\{(\w+)\}",
        lambda m: os.environ.get(m.group(1), m.group(0)),
        value,
    )


def load_sources() -> list[ScrapingSource]:
    """
    Carga las fuentes habilitadas desde src/data/sources.json.

    Si el archivo no existe o está vacío, usa SCRAPING_TARGET_URL del .env
    como fuente única (modo compatibilidad).

    Raises:
        RuntimeError: si no hay fuentes configuradas de ninguna forma.
    """
    if SOURCES_FILE.exists():
        try:
            raw: list[dict] = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
            sources = [ScrapingSource.from_dict(s) for s in raw]
            # Descartar fuentes deshabilitadas o con URL vacía tras resolver env vars
            enabled = [s for s in sources if s.enabled and s.base_url]
            disabled = len(sources) - len(enabled)
            logger.info(
                f"Fuentes cargadas: {len(enabled)} habilitadas"
                + (f", {disabled} deshabilitadas" if disabled else "")
            )
            if enabled:
                return enabled
            logger.warning(f"{SOURCES_FILE} no tiene fuentes habilitadas con URL válida.")
        except Exception as exc:
            logger.error(f"Error al leer {SOURCES_FILE}: {exc}. Usando fallback.")

    # Fallback: variable de entorno (configuración anterior)
    fallback_url = settings.SCRAPING_TARGET_URL
    if not fallback_url:
        raise RuntimeError(
            "No hay fuentes de scraping configuradas. "
            "Crea src/data/sources.json o define SCRAPING_TARGET_URL en el .env"
        )

    logger.warning(
        f"Usando SCRAPING_TARGET_URL como fuente única (fallback). "
        f"Para agregar más fuentes, edita {SOURCES_FILE}."
    )
    return [
        ScrapingSource(
            id="default",
            name="Fuente principal",
            base_url=fallback_url,
            max_pages=settings.SCRAPING_MAX_PAGES,
        )
    ]
