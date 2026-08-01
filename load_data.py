
import json
import os
from src.services.wp_api import API_WORDPRESS

data_dir = os.path.join(os.path.dirname(__file__), 'src', 'data')
os.makedirs(data_dir, exist_ok=True)

def wp_cargar_datos(update_entidades=True, update_contratos=True, update_departamentos=True, update_medias=True):
    """
    Actualiza los archivos de datos indicados. Por defecto, actualiza todos.
    Puedes elegir actualizar solo algunos pasando False a los parámetros que no quieras actualizar.
    """
    if update_entidades:
        entidades = API_WORDPRESS.get_entities()
        with open(os.path.join(data_dir, 'entidades.json'), 'w', encoding='utf-8') as f:
            json.dump(entidades, f, ensure_ascii=False, indent=2)
    if update_contratos:
        contratos = API_WORDPRESS.get_contracts()
        with open(os.path.join(data_dir, 'contratos.json'), 'w', encoding='utf-8') as f:
            json.dump(contratos, f, ensure_ascii=False, indent=2)
    if update_departamentos:
        departamentos = API_WORDPRESS.get_departments()
        with open(os.path.join(data_dir, 'departamentos.json'), 'w', encoding='utf-8') as f:
            json.dump(departamentos, f, ensure_ascii=False, indent=2)
    if update_medias:
        medias = API_WORDPRESS.get_medias()
        with open(os.path.join(data_dir, 'medias.json'), 'w', encoding='utf-8') as f:
            json.dump(medias, f, ensure_ascii=False, indent=2)
    
def cargar_instituciones():
        # Leer instituciones desde el archivo JS
    instituciones_json_path = os.path.join(data_dir, 'instituciones.json')
    with open(instituciones_json_path, 'r', encoding='utf-8') as f:
        instituciones = json.load(f)
    # Mostrar solo los primeros 3 valores para verificar
    print(instituciones[:1])

    return
    # Obtener categorías existentes de WordPress (por slug)
    categorias_wp = API_WORDPRESS.get_entities()
    slugs_wp = set(cat.get('slug') for cat in categorias_wp if 'slug' in cat)

    # Preparar y filtrar instituciones a insertar
    nuevas_categorias = []
    for inst in instituciones:
        slug = inst.get('alias')
        if not slug or slug in slugs_wp:
            continue  # Ya existe o no tiene alias
        nueva_cat = {
            'name': inst.get('nombre', ''),
            'slug': slug,
            'description': inst.get('nombre_completo', '')
        }
        nuevas_categorias.append(nueva_cat)

    print(f"A insertar: {len(nuevas_categorias)} categorías nuevas")

    # Insertar cada nueva categoría en WordPress
    # for cat in nuevas_categorias:
    #     try:
    #         API_WORDPRESS.insert_category(cat)
    #         print(f"Insertada: {cat['slug']}")
    #     except Exception as e:
    #         print(f"Error insertando {cat['slug']}: {e}")


if __name__ == "__main__":
    wp_cargar_datos()
    # cargar_instituciones()
