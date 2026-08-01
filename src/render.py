import os

from jinja2 import Environment, FileSystemLoader



def render_convocatoria_html(data, output_path="output/output.html"):
    """
    Renderiza el template convocatoria.html con los datos dados y guarda el HTML en output_path.
    """
    env = Environment(loader=FileSystemLoader("src/templates"))
    template = env.get_template("convocatoria.html")
    html_result = template.render(**data)

    # print("\n======================= HTML GENERADO =======================\n")
    # print(html_result)

    # Si se provee output_path, úsalo; si no, usa el título para el nombre del archivo
    if output_path:
        path = output_path
    else:
        title = data.get("convocatoria", {}).get("title", "Convocatoria")
        # Sanitiza el título para nombre de archivo
        import re
        safe_title = re.sub(r'[^\w\-]+', '_', title)
        path = f"{safe_title}.html"
    
    file_path = os.path.join("output", "html", path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_result)

    # print(f"\n✅ Archivo '{output_path}' generado correctamente.\nÁbrelo en tu navegador para visualizar el resultado.\n")
    return html_result