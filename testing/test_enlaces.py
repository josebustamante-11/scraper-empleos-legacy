from src.utils.wp_utils import clasificar_enlaces

# Ejemplo 1: MUNICIPALIDAD DE ACOSTAMBO
docs1 = [
    {"label": "Ver aquí Bases (convocatoria completa, cronograma y anexos)", "url": "https://drive.google.com/...", "type": "annex"},
    {"label": "Sigue AQUÍ los comunicados de las convocatorias de MUNICIPALIDAD DE ACOSTAMBO", "url": "https://www.facebook.com/...", "type": "bases"}
]
print("== Ejemplo 1 ==")
for e in clasificar_enlaces(docs1):
    print(f"  {e['label']} -> {e['url'][:50]}")

# Ejemplo 2: Variedad de documentos
docs2 = [
    {"label": "Ver aquí Cronograma", "url": "https://example.com/crono"},
    {"label": "Ver aquí Bases", "url": "https://example.com/bases"},
    {"label": "Ver aquí ANEXO N° 05 – Ficha de resumen Curricular", "url": "https://example.com/anexo5"},
    {"label": "Ver aquí ANEXO N° 11 al 14 – Declaraciones Juradas", "url": "https://example.com/anexo11"},
    {"label": "Sigue AQUÍ los comunicados de las convocatorias de AGROIDEAS", "url": "https://example.com/comunicados"},
    {"label": "Documento sin categoria conocida", "url": "https://example.com/otro"},
]
print("\n== Ejemplo 2 ==")
for e in clasificar_enlaces(docs2):
    print(f"  {e['label']} -> {e['url']}")
