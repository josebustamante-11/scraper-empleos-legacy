
from src.utils.text_utils import normalizar_texto

# 🎓 CARRERAS UNIVERSITARIAS (PROFESIONALES)
CAREER_KEYWORDS_MAP = {
    
    # 🧠 1. Ciencias Sociales y Humanidades
    "Derecho": ["derecho", "abogado", "abogada", "ciencias juridicas", "jurisprudencia"],
    "Ciencias de la Comunicación": ["comunicacion", "comunicaciones", "comunicacion social", "periodismo", "publicidad", "relaciones publicas", "comunicador social"],
    "Sociología": ["sociologia", "sociologo", "sociologa", "ciencias sociales"],
    "Antropología": ["antropologia", "antropologo", "antropologa", "cultura social"],
    "Filosofía": ["filosofia", "filosofo", "filosofa", "pensamiento critico"],
    "Historia": ["historia", "historiador", "historiadora", "estudios historicos"],
    "Trabajo Social": ["trabajo social", "asistente social", "trabajador social", "trabajadora social", "intervencion social"],
    "Psicología": ["psicologia", "psicologo", "psicologa", "salud mental", "psicologia clinica", "psicologia educativa"],
    "Lingüística": ["linguistica", "linguista", "estudios del lenguaje"],
    "Literatura": ["literatura", "letras", "escritor", "escritora", "analisis literario"],
    "Ciencia Política": ["ciencia politica", "politica", "analista politico", "ciencias politicas"],
    "Arqueología": ["arqueologia", "arqueologo", "arqueologa", "estudios prehispanicos"],
    "Ciencias Policiales": ["ciencias policiales", "policiales", "fuerzas armadas"],
    
    # 📊 2. Ciencias Económicas, Administrativas y Contables
    "Administración": ["administracion", "administrador", "administradora", "gestion empresarial", "gestion de negocios", "administracion general"],
    "Contabilidad": ["contabilidad", "contador", "contadora", "contabilidad financiera", "auditoria", "finanzas contables"],
    "Economía": ["economia", "economista", "analisis economico", "ciencias economicas"],
    "Marketing": ["marketing", "mercadotecnia", "comercializacion", "publicidad comercial", "gestion de marketing", "mercadeo"],
    "Negocios Internacionales": ["negocios internacionales", "comercio internacional", "negociacion internacional", "relaciones comerciales"],
    "Banca y Finanzas": ["banca", "finanzas", "gestion financiera", "analista financiero", "finanzas empresariales", "sector bancario"],
    "Gestión Pública": ["gestion publica", "administracion publica", "sector publico", "gestion estatal", "funcion publica"],
    "Administración de Empresas": ["administracion de empresas", "gerencia de empresas", "empresa privada", "direccion empresarial"],
    "Administración Hotelera": ["administracion hotelera", "gestion hotelera", "hotel y turismo", "gerencia hotelera"],
    "Administración en Turismo": ["administracion en turismo", "gestion turistica", "turismo y hoteleria", "gestion en turismo"],
    "Comercio Exterior": ["comercio exterior", "comercio internacional", "exportaciones", "importaciones", "negocios globales"],
    "Gestión de Recursos Humanos": ["recursos humanos", "gestion de talento", "rrhh", "administracion de personal", "capital humano"],    
    
    # 🧪 3. Ciencias Básicas
    "Matemática": ["matematica", "matematicas", "matematico", "matematica pura", "analisis matematico", "estadistica matematica"],
    "Física": ["fisica", "fisico", "ciencias fisicas", "fisica teorica", "fisica aplicada"],
    "Química": ["quimica", "quimico", "quimica pura", "quimica aplicada", "quimica industrial"],
    "Biología": ["biologia", "biologo", "biologia celular", "biologia molecular", "ciencias biologicas"],
    "Estadística": ["estadistica", "estadistico", "analisis estadistico", "estadistica aplicada", "ciencias estadisticas"],
    "Ciencias Ambientales": ["ciencias ambientales", "medio ambiente", "gestion ambiental", "ecologia", "ingenieria ambiental"],

    # 🧬 4. Ciencias de la Salud
    "Medicina Humana": ["medicina", "medicina humana", "medico", "doctora", "doctor", "salud general", "salud humana"],
    "Enfermería": ["enfermeria", "enfermera", "enfermero", "cuidados de salud", "auxiliar de enfermeria"],
    "Odontología": ["odontologia", "odontologo", "odontologa", "dentista", "cirujano dental"],
    "Obstetricia": ["obstetricia", "obstetra", "partos", "atencion materna", "salud reproductiva"],
    "Psicología": ["psicologia", "psicologo", "psicologa", "psicologia clinica", "psicologia educativa", "salud mental"],
    "Tecnología Médica": ["tecnologia medica", "tecnologo medico", "laboratorio clinico", "imagenologia", "radiologia", "rehabilitacion fisica"],
    "Farmacia y Bioquímica": ["farmacia", "bioquimica", "farmaceutico", "quimico farmaceutico", "farmacia clinica"],
    "Nutrición": ["nutricion", "nutricionista", "alimentacion saludable", "nutricion clinica", "dietetica"],
    "Veterinaria": ["veterinaria", "medico veterinario", "veterinario", "salud animal"],
    "Salud Pública": ["salud publica", "epidemiologia", "gestion en salud", "promocion de la salud", "sanidad publica"],

    # 🧑‍🏫 5. Educación y Pedagogía
    "Educación": ["educacion"],
    "Educación Inicial": ["educacion inicial", "docente de inicial", "profesora de inicial", "maestra de inicial", "preescolar"],
    "Educación Primaria": ["educacion primaria", "docente de primaria", "profesora de primaria", "maestra de primaria"],
    "Educación Secundaria": ["educacion secundaria", "docente de secundaria", "profesor de secundaria", "especialista en secundaria", "educacion por areas"],
    "Educación Física": ["educacion fisica", "profesor de educacion fisica", "actividad fisica", "deporte escolar"],
    "Educación Especial": ["educacion especial", "docente de educacion especial", "educacion inclusiva", "discapacidad", "atencion a la diversidad"],
    "Educación Intercultural Bilingüe": ["educacion intercultural", "educacion bilingue", "docente intercultural", "educacion eib", "educacion en lenguas originarias"],
    "Traducción e Interpretación": ["traduccion", "interpretacion", "traductor", "ensenanza de ingles", "docente de ingles", "profesor de ingles"],

    # 🖥️ 6. Ingeniería y Tecnología
    "Ingeniería Civil": ["ingenieria civil", "ingeniero civil", "construccion", "estructuras", "obras civiles"],
    "Ingeniería de Sistemas": ["ingenieria de sistemas", "sistemas", "ingeniero de sistemas", "sistemas informaticos", "sistemas computacionales"],
    "Ingeniería Informática": ["ingenieria informatica"],
    "Ingeniería Industrial": ["ingenieria industrial", "ingeniero industrial", "procesos industriales", "gestion industrial"],
    "Ingeniería Electrónica": ["ingenieria electronica", "ingeniero electronico", "circuitos", "electronica aplicada"],
    "Ingeniería Eléctrica": ["ingenieria electrica", "ingeniero electrico", "electricidad industrial", "sistemas electricos"],
    "Ingeniería Ambiental": ["ingenieria ambiental", "ingeniero ambiental", "medio ambiente", "gestion ambiental", "impacto ambiental"],
    "Ingeniería Química": ["ingenieria quimica", "ingeniero quimico", "procesos quimicos", "industria quimica"],
    "Ingeniería Mecánica": ["ingenieria mecanica", "ingeniero mecanico", "mecanica industrial", "mecanica de maquinas"],
    "Ingeniería de Telecomunicaciones": ["ingenieria en telecomunicaciones", "telecomunicaciones", "redes de comunicacion", "comunicaciones digitales"],
    "Ingeniería Agroindustrial": ["ingenieria agroindustrial", "agroindustria", "ingeniero agroindustrial", "procesamiento de alimentos"],
    "Ingeniería de Software": ["ingenieria de software", "desarrollador de software", "ingeniero de software", "programador"],
    "Ingeniería Geológica": ["ingenieria geologica", "geologia", "ingeniero geologo", "exploracion geologica"],
    "Ingeniería de Minas": ["ingenieria de minas", "mineria", "ingeniero de minas", "operaciones mineras"],
    "Ingeniería de Petróleo": ["ingenieria de petroleo", "ingeniero de petroleo", "extraccion de petroleo", "industria petrolera"],
    "Ingeniería en Energías Renovables": ["energias renovables", "ingeniero en energias", "energia solar", "energia eolica", "tecnologias limpias"],
    "Ingeniería de Transporte": ["ingenieria de transporte"],
    "Ingeniería Económica": ["ingenieria economica"],

    # 🌾 7. Ciencias Agrarias y Forestales
    "Agronomía": ["agronomia", "ingeniero agronomo", "agricultura", "produccion agricola", "ciencias agrarias"],
    "Ingeniería Agrícola": ["ingenieria agricola", "ingeniero agricola", "tecnologia agricola", "infraestructura agricola"],
    "Ingeniería Forestal": ["ingenieria forestal", "ingeniero forestal", "manejo forestal", "bosques", "conservacion forestal"],
    "Ingeniería Agrónoma": ["ingenieria agronoma"],
    "Zootecnia": ["zootecnia", "zootecnista", "produccion animal", "ganaderia", "nutricion animal"],
    "Ingeniería Pesquera": ["ingenieria pesquera", "pesca industrial", "pesqueria", "recursos hidrobiologicos", "tecnologia pesquera"],
    "Ingeniería en Industrias Alimentarias": ["industrias alimentarias", "ingenieria en alimentos", "tecnologia de alimentos", "procesamiento de alimentos"],
    
    # 🏗️ 8. Arquitectura y Urbanismo
    "Arquitectura": ["arquitectura", "arquitecto", "arquitecta", "diseno arquitectonico", "proyectos arquitectonicos"],
    "Urbanismo y Diseño Urbano": ["urbanismo", "diseno urbano", "planificacion urbana", "desarrollo urbano", "gestion territorial"],
    "Paisajismo": ["paisajismo", "diseno del paisaje", "arquitectura del paisaje", "espacios verdes", "diseno ambiental"],
    "Topografía": ["topografia"],
    "Edificaciones": ["edificaciones"],

    # 🎨 9. Artes y Diseño
    "Artes Plásticas": ["artes plasticas", "bellas artes", "pintura", "escultura", "artista plastico"],
    "Artes Escénicas": ["artes escenicas", "teatro", "actuacion", "actor", "actriz", "escenografia"],
    "Música": ["musica", "musico", "instrumentista", "composicion musical", "educacion musical"],
    "Danza": ["danza", "bailarin", "bailarina", "coreografia", "danza contemporanea", "danza folklorica"],
    "Diseño Gráfico": ["diseno grafico", "disenador grafico", "comunicacion visual", "diseno digital", "arte digital"],
    "Diseño de Modas": ["diseno de modas", "moda", "disenador de modas", "industria textil", "alta costura"],
    "Diseño Industrial": ["diseno industrial", "disenador industrial", "productos industriales", "innovacion de productos"],
    
    # ⚙️ Carreras Técnicas
    "Computación e Informática": ["tecnico en computacion"],
    "Administración Bancaria": ["administracion bancaria", "banca"],
    "Enfermería Técnica": ["enfermeria tecnica", "tecnico en enfermeria"],
    "Farmacia Técnica": ["farmacia tecnica", "tecnico en farmacia"],

    # "Electricidad Industrial": ["electricidad industrial", "electricista"],
    "Mecánica de Producción": ["mecanica de produccion", "tecnico mecanico"],
    "Mecánica Automotriz": ["mecanica automotriz", "automotriz"],
    "Construcción Civil": ["construccion civil", "constructor civil"],
    "Electrónica Industrial": ["electronica industrial"],
    "Operación de Maquinaria Pesada": ["maquinaria pesada", "operador de maquinaria pesada"],
    "Contabilidad Técnica": ["contabilidad tecnica", "tecnico contable"],
    "Marketing Técnico": ["marketing tecnico"],
    "Cocina y Gastronomía": ["gastronomia", "cocina", "chef"],
    "Panadería y Pastelería": ["panaderia", "pasteleria", "panadero", "pastelero"],

    # ⚙️ Carreras Técnicas
    "Secretariado": ["secretariado", "secretariado ejecutivo", "secretaria", "secretario"],
    "Electricista": ["electronica", "electricidad"],
    
    # ⚙️ Secundaria
    "Secundaria Completa": ["x secundaria", "secundaria completa"],

    # Otros
    "Todas Las Carreras": ["todas las carreras"]
}


# Careers: Extraer carreras asociadas a los textos de education
def extract_careers_from_educationX(education_list: list[str]) -> list[str]:
    """
    Busca coincidencias de nombres de carreras en los textos de education.
    Devuelve una lista de carreras encontradas (sin duplicados).
    """
    found = set()
    for edu in education_list:
        if not isinstance(edu, str):
            continue
        edu_lower = normalizar_texto(edu)
        for career, variants in CAREER_KEYWORDS_MAP.items():
            for variant in variants:
                if variant in edu_lower:
                    found.add(career)
    return sorted(found)