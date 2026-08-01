# import requests
import httpx
# import config
import base64
from loguru import logger
from src.config import settings

SITE_WEB = settings.WP_URL
USERNAME = settings.WP_USER
APP_PASSWORD = settings.WP_APP_PASSWORD  # contraseña de aplicación generada

class WordPressAPI:
      
    def __init__(self):
        credentials = f"{USERNAME}:{APP_PASSWORD}"
        token = base64.b64encode(credentials.encode()).decode()
        self.base_url = SITE_WEB.rstrip('/')  # quita barra final si existe
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Basic {token}"
        }

    def _request(self, method, endpoint, **kwargs):
        """
        Realiza una petición HTTP. Siempre devuelve el cuerpo JSON (o un dict
        con 'error'), nunca lanza excepción al llamador.
        Callers deben revisar 'status_code' o la clave 'error' para detectar fallos.
        """
        url = f"{self.base_url}/wp-json/wp/v2/{endpoint}"
        try:
            response = httpx.request(method, url, headers=self.headers, verify=False, **kwargs)
            try:
                body = response.json()
            except ValueError:
                body = {"error": "Invalid JSON response", "content": response.text}
            body["_status_code"] = response.status_code
            return body
        except httpx.RequestError as e:
            return {"error": str(e), "_status_code": None}

    def _get_all_pages(self, endpoint, params=None):
        """Trae todos los resultados paginados de un endpoint GET."""
        params = dict(params or {})
        params.setdefault('per_page', 100)
        params['page'] = 1
        all_items = []

        while True:
            url = f"{self.base_url}/wp-json/wp/v2/{endpoint}"
            try:
                response = httpx.request("GET", url, headers=self.headers, verify=False, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.warning(f"WP API [{endpoint}] HTTP {e.response.status_code}: {e.response.text[:200]}")
                break
            except (httpx.RequestError, ValueError) as e:
                logger.warning(f"WP API [{endpoint}] error: {e}")
                break

            if not isinstance(data, list):
                logger.warning(f"WP API [{endpoint}] respuesta inesperada (no es lista): {str(data)[:200]}")
                break
            if len(data) == 0:
                break

            all_items.extend(data)
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if params['page'] >= total_pages:
                break
            params['page'] += 1

        return all_items

    # ---------- OPERACIONES CRUD ---------- #
    def insert_category(self, payload):
        return self._request("POST", "categories", json=payload)
    
    def insert_entities(self, payload):
        return self._request("POST", "entidad", json=payload)

    def insert_contrato(self, payload):
        return self._request("POST", "contrato", json=payload)

    def insert_departamento(self, payload):
        return self._request("POST", "departamento", json=payload)
    
    def insert_post(self, payload):
        return self._request("POST", "posts", json=payload)

    def update_post(self, post_id, payload):
        return self._request("POST", f"posts/{post_id}", json=payload)

    def get_posts(self, params=None):
        return self._request("GET", "posts", params=params or {})

    def get_post_by_id(self, post_id):
        return self._request("GET", f"posts/{post_id}")

    def get_categories(self):
        return self._get_all_pages("categories", params={'_fields': 'id,name,slug'})
    
    def get_entities(self):
        return self._get_all_pages("entidad", params={'_fields': 'id,name,slug'})
    
    def get_contracts(self):
        return self._get_all_pages("contrato", params={'_fields': 'id,name,slug'})
    
    def get_academic_levels(self):
        return self._get_all_pages("nivel_academico", params={'_fields': 'id,name,slug'})
    
    def get_careers(self):
        return self._get_all_pages("carrera", params={'_fields': 'id,name,slug'})
    
    def get_departments(self):
        return self._get_all_pages("departamento", params={'_fields': 'id,name,slug'})
    
    def get_medias(self):
        return self._get_all_pages("media", params={'_fields': 'id,title,slug'})

    def find_category_by_name(self, name: str) -> dict | None:
        """Busca una categoría en WP por nombre exacto. Retorna {id, name, slug} o None."""
        results = self._get_all_pages("entidad", params={'search': name, '_fields': 'id,name,slug'})
        name_lower = name.strip().lower()
        for item in results:
            if item.get('name', '').strip().lower() == name_lower:
                return item
        return None


API_WORDPRESS = WordPressAPI()