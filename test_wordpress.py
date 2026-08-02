"""
test_wordpress.py — Prueba de conexión a la API de WordPress

Requisitos en tu .env:
    WP_URL=https://tu-sitio.com
    WP_USER=tu-usuario
    WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx   (Application Password de WP)

Uso:
    python test_wordpress.py
"""

from src.config import settings
from src.services.wp_api import API_WORDPRESS  # ajustá el import según dónde tengas la clase


def main():
    print("Config actual:")
    print(f"  WP_URL          = {settings.WP_URL}")
    print(f"  WP_USER         = {settings.WP_USER}")
    print(f"  WP_APP_PASSWORD = {'(seteado)' if settings.WP_APP_PASSWORD else '(vacío)'}")
    print()

    print("Probando conexión con GET /posts...")
    result = API_WORDPRESS.get_posts(params={"per_page": 1})

    status = result.get("_status_code")

    if status == 200:
        print("✅ Conexión exitosa")
        if isinstance(result, list) and result:
            print(f"Ejemplo de post encontrado: {result[0].get('title', {}).get('rendered', '(sin título)')}")
        else:
            print("El sitio respondió OK pero no hay posts para mostrar.")
    elif status == 401:
        print("❌ Error 401: credenciales inválidas (usuario o Application Password incorrectos)")
        print(result)
    elif status is None:
        print("❌ No se pudo conectar al sitio (error de red o URL incorrecta)")
        print(result)
    else:
        print(f"❌ Error inesperado [{status}]")
        print(result)


if __name__ == "__main__":
    main()