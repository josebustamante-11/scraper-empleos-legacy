"""
wp_cache.py — Cache en memoria de taxonomías de WordPress.

Se carga una sola vez al inicio desde la API de WP.
Permite buscar IDs y crear nuevos términos sin depender de archivos JSON locales.

Dump a archivo temporal:
    Controlado por la variable de entorno WP_CACHE_DUMP.
    - WP_CACHE_DUMP=true  → guarda snapshot en output/wp_cache_dump.json
    - WP_CACHE_DUMP=false (o no definido) → no guarda nada
"""

import json
import os
from datetime import datetime

from loguru import logger
from src.utils.text_utils import normalizar_texto
from src.utils.file_utils import load_json_file
from src.services.wp_api import API_WORDPRESS


CACHE_DUMP_PATH = os.path.join("temp", "wp_cache_dump.json")


class WPCache:
    def __init__(self):
        self._entidades: list[dict] = []
        self._contratos: list[dict] = []
        self._departamentos: list[dict] = []
        self._medias: list[dict] = []
        self._instituciones: list[dict] = []
        self._carreras: list[dict] = []
        self._nivel_academico: list[dict] = []

    # ─── Carga inicial ───────────────────────────────────────
    def cargar(self):
        """Carga todas las taxonomías desde la API de WordPress + instituciones locales."""
        logger.info("Cargando taxonomías desde WordPress API...")
        self._entidades = API_WORDPRESS.get_entities() or []
        self._contratos = API_WORDPRESS.get_contracts() or []
        self._carreras = API_WORDPRESS.get_careers() or []
        self._nivel_academico = API_WORDPRESS.get_academic_levels() or []
        self._departamentos = API_WORDPRESS.get_departments() or []
        self._medias = API_WORDPRESS.get_medias() or []
        self._instituciones = load_json_file('static/scraping/instituciones.json')
        logger.info(
            f"Cache cargado: {len(self._entidades)} entidades, "
            f"{len(self._contratos)} contratos, "
            f"{len(self._carreras)} carreras, "
            f"{len(self._nivel_academico)} niveles académicos, "
            f"{len(self._departamentos)} departamentos, "
            f"{len(self._medias)} medias, "
            f"{len(self._instituciones)} instituciones"
        )
        self._dump()

    # ─── Dump opcional a archivo ─────────────────────────────
    def _is_dump_enabled(self) -> bool:
        return os.environ.get("WP_CACHE_DUMP", "false").strip().lower() == "true"

    def _dump(self):
        """Guarda el snapshot completo del cache al inicio de la ejecución."""
        if not self._is_dump_enabled():
            return
        data = {
            "_timestamp": datetime.now().isoformat(),
            "entidades": self._entidades,
            "contratos": self._contratos,
            "carreras": self._carreras,
            "departamentos": self._departamentos,
            "medias": self._medias,
            "nivel_academico": self._nivel_academico,
        }
        os.makedirs(os.path.dirname(CACHE_DUMP_PATH), exist_ok=True)
        with open(CACHE_DUMP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Cache dump guardado en {CACHE_DUMP_PATH}")

    def _dump_addition(self, taxonomy: str, entry: dict) -> None:
        """Actualiza el dump con una nueva entrada: la añade al array principal y al audit log."""
        if not self._is_dump_enabled():
            return
        try:
            os.makedirs(os.path.dirname(CACHE_DUMP_PATH), exist_ok=True)
            if os.path.exists(CACHE_DUMP_PATH):
                with open(CACHE_DUMP_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}

            # Actualizar el array principal del taxonomy (igual que el estado en memoria)
            main_list = data.setdefault(taxonomy, [])
            entry_id = entry.get("id")
            if entry_id is not None and not any(e.get("id") == entry_id for e in main_list):
                main_list.append(entry)

            # Guardar audit trail de adiciones en esta ejecución
            additions = data.setdefault("_additions", {})
            additions.setdefault(taxonomy, []).append({**entry, "_added_at": datetime.now().isoformat()})
            data["_last_update"] = datetime.now().isoformat()

            with open(CACHE_DUMP_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cache dump actualizado: nueva {taxonomy} → {entry}")
        except Exception as exc:
            logger.debug(f"No se pudo actualizar dump con adición: {exc}")

    # ─── Lookup por slug/nombre ──────────────────────────────
    def _get_store(self, taxonomy_type: str) -> list:
        stores = {
            "entidades": self._entidades,
            "contratos": self._contratos,
            "carreras": self._carreras,
            "departamentos": self._departamentos,
            "medias": self._medias,
            "nivel_academico": self._nivel_academico,
        }
        if taxonomy_type not in stores:
            raise ValueError(f"Taxonomía no válida: {taxonomy_type}")
        return stores[taxonomy_type]

    def get_id_by_slug(self, slug: str, taxonomy_type: str):
        """Busca el ID en el cache en memoria. Retorna None si no encuentra."""
        if not slug:
            return None
        store = self._get_store(taxonomy_type)
        slug_norm = normalizar_texto(slug)
        for item in store:
            item_slug = item.get('slug', '')
            item_name = normalizar_texto(item.get('name', ''))
            if slug_norm == item_name or slug_norm == item_slug:
                return item['id']
        return None
    
    def get_ids_by_slugs(self, slugs: list, taxonomy_type: str):
        """Devuelve una lista de IDs según una lista de slugs"""
        if not slugs:
            return []

        store = self._get_store(taxonomy_type)
        result = []

        for slug in slugs:
            slug_norm = normalizar_texto(slug)

            for item in store:
                item_slug = normalizar_texto(item.get('slug', ''))
                item_name = normalizar_texto(item.get('name', ''))

                if slug_norm == item_slug or slug_norm == item_name:
                    result.append(item['id'])
                    break  # evita duplicados

        return result

    def get_slug_by_id(self, id: int, taxonomy_type: str):
        """Busca el slug en el cache en memoria. Retorna None si no encuentra."""
        if not id:
            return None
        store = self._get_store(taxonomy_type)
        for item in store:
            if item.get('id') == id:
                return item.get('slug')
        return None

    # ─── Get or Create para entidades ────────────────────────
    def get_or_create_entidad(self, nombre_entidad: str):
        """
        Busca la entidad en cache. Si no existe, la crea en WP.
        Usa instituciones.json para obtener datos enriquecidos (alias, nombre completo).
        Si no está en el archivo, la crea directamente con el nombre disponible.
        """
        if not nombre_entidad:
            return None

        # 1. Buscar en cache
        entidad_id = self.get_id_by_slug(nombre_entidad, "entidades")
        if entidad_id:
            return entidad_id

        # 2. Buscar datos enriquecidos en instituciones.json (ya en memoria)
        nombre_normalizado = nombre_entidad.strip().lower()
        institucion = next(
            (inst for inst in self._instituciones
             if inst.get('nombre', '').strip().lower() == nombre_normalizado),
            None,
        )

        # 3. Construir payload — si no está en instituciones.json, usar el nombre directamente
        if institucion:
            payload = {
                'name': institucion.get('nombre', nombre_entidad),
                'slug': institucion.get('alias', '') or normalizar_texto(nombre_entidad).replace(' ', '-'),
                'description': institucion.get('nombre_completo', ''),
            }
        else:
            logger.warning(
                f"Entidad '{nombre_entidad}' no encontrada en instituciones.json — "
                "se creará con datos mínimos."
            )
            payload = {
                'name': nombre_entidad,
                'slug': normalizar_texto(nombre_entidad).replace(' ', '-'),
                'description': '',
            }
        # 4. Insertar en WordPress
        response = API_WORDPRESS.insert_entities(payload)
        status_code = response.get("_status_code")
        entidad_id = response.get("id")

        # 4a. Creación exitosa (201)
        if entidad_id:
            self._cache_entidad(entidad_id, payload["name"], payload["slug"])
            logger.info(f"Entidad '{nombre_entidad}' creada en WP con ID {entidad_id} y agregada al cache")
            self._dump_addition("entidades", {"id": entidad_id, "name": payload["name"], "slug": payload["slug"]})
            return entidad_id

        # 4b. WP indica que el término ya existe (400 term_exists)
        term_id_from_wp = None
        if isinstance(response.get("data"), dict):
            term_id_from_wp = response["data"].get("term_id")
        if term_id_from_wp:
            self._cache_entidad(term_id_from_wp, payload["name"], payload["slug"])
            logger.info(f"Entidad '{nombre_entidad}' ya existía en WP con ID {term_id_from_wp} — agregada al cache")
            self._dump_addition("entidades", {"id": term_id_from_wp, "name": payload["name"], "slug": payload["slug"]})
            return term_id_from_wp

        # 4c. Timeout u otro error — buscar en WP por nombre (la entidad pudo haberse creado).
        #     Se busca primero por payload["name"] (lo que se envió a WP) y luego por
        #     nombre_entidad (el nombre original). Ambos pueden diferir cuando hay un
        #     registro en instituciones.json con nombre canónico distinto.
        if "error" in response or (status_code and status_code >= 400):
            log_fn = logger.warning if "error" in response else logger.error
            log_fn(f"Entidad '{nombre_entidad}' — respuesta inesperada de WP: {response}")
            logger.info(f"Entidad '{nombre_entidad}' — buscando en WP por nombre como fallback...")
            try:
                candidates = [payload["name"]]
                if nombre_entidad != payload["name"]:
                    candidates.append(nombre_entidad)
                found = None
                for candidate in candidates:
                    found = API_WORDPRESS.find_category_by_name(candidate)
                    if found and found.get("id"):
                        break
                if found and found.get("id"):
                    self._cache_entidad(found["id"], found.get("name", payload["name"]), found.get("slug", payload["slug"]))
                    logger.info(
                        f"Entidad '{nombre_entidad}' recuperada de WP con ID {found['id']} — agregada al cache"
                    )
                    self._dump_addition("entidades", {"id": found["id"], "name": found.get("name", payload["name"]), "slug": found.get("slug", payload["slug"])})
                    return found["id"]
                logger.warning(f"Entidad '{nombre_entidad}' no encontrada en WP — se publicará sin categoría.")
            except Exception as lookup_exc:
                logger.error(f"Entidad '{nombre_entidad}' — error en búsqueda fallback: {lookup_exc}")

        return None

    def _cache_entidad(self, entidad_id: int, name: str, slug: str) -> None:
        """Agrega una entidad al cache en memoria si no está ya presente."""
        if not any(e.get("id") == entidad_id for e in self._entidades):
            self._entidades.append({"id": entidad_id, "name": name, "slug": slug})

    # ─── Get or Create para contratos ────────────────────────
    def get_or_create_contrato(self, nombre: str) -> int | None:
        """
        Busca el contrato en cache. Si no existe, lo crea en WP y actualiza el cache.
        Ejemplo: 'CAS', 'SNP', 'Locación de Servicios'.
        """
        if not nombre:
            return None

        term_id = self.get_id_by_slug(nombre, "contratos")
        if term_id:
            return term_id

        slug = normalizar_texto(nombre).replace(" ", "-")
        response = API_WORDPRESS.insert_contrato({"name": nombre, "slug": slug})
        term_id = response.get("id") or (
            response.get("data", {}).get("term_id")
            if isinstance(response.get("data"), dict) else None
        )

        if term_id:
            self._contratos.append({"id": term_id, "name": nombre, "slug": slug})
            logger.info(f"Contrato '{nombre}' creado/encontrado en WP con ID {term_id}")
            self._dump_addition("contratos", {"id": term_id, "name": nombre, "slug": slug})
        else:
            logger.error(f"Contrato '{nombre}' — respuesta inesperada de WP: {response}")

        return term_id

    # ─── Get or Create para departamentos ────────────────────
    def get_or_create_departamento(self, nombre: str) -> int | None:
        """
        Busca el departamento en cache. Si no existe, lo crea en WP y actualiza el cache.
        Ejemplo: 'Lima', 'Callao', 'Arequipa'.
        """
        if not nombre:
            return None

        term_id = self.get_id_by_slug(nombre, "departamentos")
        if term_id:
            return term_id

        slug = normalizar_texto(nombre).replace(" ", "-")
        response = API_WORDPRESS.insert_departamento({"name": nombre, "slug": slug})
        term_id = response.get("id") or (
            response.get("data", {}).get("term_id")
            if isinstance(response.get("data"), dict) else None
        )

        if term_id:
            self._departamentos.append({"id": term_id, "name": nombre, "slug": slug})
            logger.info(f"Departamento '{nombre}' creado/encontrado en WP con ID {term_id}")
            self._dump_addition("departamentos", {"id": term_id, "name": nombre, "slug": slug})
        else:
            logger.error(f"Departamento '{nombre}' — respuesta inesperada de WP: {response}")

        return term_id


# Singleton — se importa desde donde se necesite
WP_CACHE = WPCache()
