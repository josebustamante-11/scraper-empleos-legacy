import json

from src.parser import slugify
# from src.data.careers import CAREER_KEYWORDS_MAP

CAREER_KEYWORDS_MAP = {
    "01_educacion": {
        "Educación": ["educacion", "educacion general", "ciencias de la educacion","pedagogia", "formacion docente"],
        "Educación Inicial": ["educacion inicial", "docente de inicial", "profesora de inicial","maestra de inicial", "preescolar", "estimulación temprana","estimulacion temprana", "psicomotricidad", "didactica de inicial","neurociencia en educacion inicial", "comunicacion integral"],
        "Educación Primaria": ["educacion primaria", "docente de primaria", "profesora de primaria","maestra de primaria", "alfabetizacion de adultos","educacion basica alternativa", "didactica de matematica","didactica de ciencias naturales", "didactica de comunicacion","informatica educativa", "educacion bilingue primaria"],
        "Educación Secundaria": ["educacion secundaria", "docente de secundaria", "profesor de secundaria","especialista en secundaria", "educacion por areas","historia y geografia", "ciencias sociales", "ciencias naturales","ciencias biologicas", "comunicacion", "religion","idiomas originarios", "persona familia y relaciones humanas"],
        "Educación con Asignatura de Especialización": ["educacion con asignatura de especializacion","educacion matematica", "educacion historia y geografia","educacion ciencias sociales", "educacion comunicacion","educacion ciencias biologicas", "educacion religion","educacion idiomas", "educacion ciencias naturales"],
        "Educación Física": ["educacion fisica", "profesor de educacion fisica","actividad fisica", "deporte escolar", "cultura fisica","ciencias del deporte", "entrenamiento deportivo","gestion deportiva"],
        "Educación Artística": ["educacion artistica", "docencia en arte", "pedagogia artistica","educacion musical", "educacion en danza", "educacion teatral","didactica del arte", "docente de arte"],
        "Educación Superior y Tecnológica": ["educacion superior y tecnologica", "docencia superior","docencia universitaria", "docencia tecnica", "pedagogia superior","tecnologia educativa", "informatica educativa","entornos virtuales de aprendizaje", "educacion para el trabajo"],
        "Educación Especial": ["educacion especial", "docente de educacion especial","educacion inclusiva", "discapacidad", "atencion a la diversidad","audicion y lenguaje", "discapacidad fisica","discapacidad visual", "discapacidad intelectual","multidiscapacidad", "aprendizaje especial"],
        "Educación Intercultural Bilingüe": ["educacion intercultural", "educacion bilingue","docente intercultural", "educacion eib","educacion en lenguas originarias", "quechua", "aimara","lenguas originarias", "educacion intercultural bilingue","gestion de educacion bilingue"],
        "Gestión y Calidad Educativa": ["gestion y calidad educativa", "gestion educativa","gestion universitaria", "gestion estrategica educativa","calidad educativa", "acreditacion educativa","certificacion educativa", "planificacion educativa","liderazgo educativo"],
        "Otros Programas en Educación": ["otros programas en educacion", "educacion general","formacion pedagogica general"]
    },
    "02_arte_y_humanidades": {
        "Comunicación Audiovisual": ["comunicacion audiovisual", "produccion audiovisual","medios audiovisuales", "cinematografia", "fotografia publicitaria","radio y television", "cine y television","produccion para medios de comunicacion", "multimedia","edicion electronica", "medios interactivos"],
        "Diseño Gráfico": ["diseno grafico", "disenador grafico", "comunicacion visual","diseno digital", "arte digital", "diseno publicitario","diseno editorial", "diseno visual"],
        "Diseño Industrial": ["diseno industrial", "disenador industrial","productos industriales", "innovacion de productos","ingenieria de diseno", "diseno de producto", "diseno profesional"],
        "Diseño de Modas": ["diseno de modas", "moda", "disenador de modas","industria textil", "alta costura", "gestion de modas","confecciones", "vestuario"],
        "Diseño de Interiores": ["diseno de interiores", "interiores", "interiorismo","espacios interiores", "ambientacion interior"],
        "Arte": ["arte", "historia del arte", "gestion cultural","conservacion y restauracion", "patrimonio cultural","artes visuales", "artes plasticas", "pintura", "escultura","grabado", "acuarela", "difusion cultural"],
        "Artes Plásticas": ["artes plasticas", "bellas artes", "pintura", "escultura","artista plastico", "grabado", "artes visuales"],
        "Artesanía y Manualidades": ["artesania", "manualidades", "arte popular", "orfebreria","joyeria", "plateria", "tallado en madera", "tejido artesanal","pirograbado", "ceramica artesanal", "artesania de vidrio","fabricacion de instrumentos musicales", "reparacion de instrumentos"],
        "Artes Escénicas": ["artes escenicas", "teatro", "actuacion", "actor", "actriz","escenografia", "produccion escenica", "teatro y danza","folklore", "arte dramatico"],
        "Música": ["musica", "musico", "instrumentista", "composicion musical","educacion musical", "interpretacion musical", "canto","musicologia", "etnomusicologia", "produccion musical","direccion de orquesta", "direccion de coro"],
        "Danza": ["danza", "bailarin", "bailarina", "coreografia","danza contemporanea", "danza folklorica", "danza peruana"],
        "Filosofía": ["filosofia", "filosofo", "filosofa", "pensamiento critico","etica", "filosofia y psicologia", "filosofia y teologia","antropologia filosofica"],
        "Historia": ["historia", "historiador", "historiadora","estudios historicos", "historia y geografia","historia y gestion cultural", "patrimonio historico","preservacion del patrimonio historico"],
        "Arqueología": ["arqueologia", "arqueologo", "arqueologa","estudios prehispanicos", "patrimonio arqueologico"],
        "Religión y Teología": ["religion", "teologia", "teologo", "ministerio pastoral","estudios religiosos", "vocacion religiosa"],
        "Idiomas": ["idiomas", "ingles", "frances", "portugues", "quechua","enseñanza de idiomas", "ensenanza de idiomas","idiomas y turismo", "lenguas extranjeras"],
        "Traducción e Interpretación": ["traduccion", "interpretacion", "traductor", "interprete","traduccion e interpretacion", "interpretacion de idiomas","traduccion de documentos"],
        "Lingüística": ["linguistica", "linguista", "estudios del lenguaje","filologia", "linguistica aplicada", "comprension de textos","produccion de textos", "lengua", "linguistica inglesa","linguistica andina"],
        "Literatura": ["literatura", "letras", "escritor", "escritora","analisis literario", "literatura hispanica","literatura comparada", "literatura infantil y juvenil","escritura creativa", "literatura peruana","literatura hispanoamericana"]
    },
    "03_ciencias_sociales_periodismo_e_informacion": {
        "Ciencias de la Comunicación": ["comunicacion", "comunicaciones", "comunicacion social","periodismo", "publicidad", "relaciones publicas","comunicador social", "ciencias de la comunicacion","comunicacion masiva", "periodismo televisivo","locucion", "edicion", "informacion redaccion y contenido"],
        "Bibliotecología y Archivística": ["bibliotecologia", "bibliotecario", "archivo", "archivistica","archivologia", "gestion documental", "ciencias de la informacion","estudios bibliotecarios", "museologia"],
        "Sociología": ["sociologia", "sociologo", "sociologa", "ciencias sociales","sociologia y estudios culturales", "estudios culturales","gerencia social", "desarrollo social", "demografia","poblacion", "estudios de genero"],
        "Antropología": ["antropologia", "antropologo", "antropologa","cultura social", "antropologia social","antropologia ambiental", "antropologia turismo"],
        "Psicología": ["psicologia", "psicologo", "psicologa","psicologia clinica", "psicologia educativa", "salud mental","psicologia organizacional", "psicologia industrial","psicologia comunitaria", "neuropsicologia","psicoterapia", "psicoanalisis", "ciencia cognitiva"],
        "Ciencia Política": ["ciencia politica", "politica", "analista politico","ciencias politicas", "politologia", "gobierno","gobernabilidad", "politica publica", "estudios de politica publica","derechos humanos", "historia politica"],
        "Economía": ["economia", "economista", "analisis economico","ciencias economicas", "econometria", "economia politica","historia economica", "economia agraria", "economia internacional","economia publica", "microfinanzas", "finanzas corporativas"],
        "Ingeniería Económica": ["ingenieria economica"]
    },
    "04_ciencias_administrativas_y_derecho": {
        "Derecho": ["derecho", "abogado", "abogada", "ciencias juridicas","jurisprudencia", "derecho administrativo", "derecho penal","derecho procesal", "investigacion juridica", "derecho corporativo","derecho bancario", "derecho privado", "derecho comercial","derecho empresarial", "derecho de los negocios","derecho internacional economico", "derecho laboral","derecho civil", "derecho familiar", "derecho notarial y registral","derecho minero", "diplomacia", "mediacion juridica","criminalistica", "ciencias forenses"],
        "Administración": ["administracion", "administrador", "administradora","gestion empresarial", "gestion de negocios","administracion general", "gestion y alta direccion","gestion estrategica", "ciencias de la administracion","emprendimiento", "ingenieria empresarial","ingenieria comercial", "ingenieria de negocios"],
        "Administración de Empresas": ["administracion de empresas", "gerencia de empresas","empresa privada", "direccion empresarial","gerencia empresarial", "direccion de empresas"],
        "Contabilidad": ["contabilidad", "contador", "contadora","contabilidad financiera", "auditoria", "finanzas contables","ciencias contables", "impuestos", "contabilidad tributaria","contabilidad gerencial", "contabilidad administrativa","gestion fiscal", "costos y presupuestos", "teneduria de libros"],
        "Marketing": ["marketing", "mercadotecnia", "comercializacion","publicidad comercial", "gestion de marketing", "mercadeo","publicidad", "investigacion de mercado","comportamiento del consumidor", "relaciones publicas", "ventas"],
        "Negocios Internacionales": ["negocios internacionales", "comercio internacional","negociacion internacional", "relaciones comerciales","negocios globales", "relaciones internacionales","logistica internacional", "puertos y aduanas"],
        "Comercio Exterior": ["comercio exterior", "comercio internacional", "exportaciones","importaciones", "negocios globales", "aduanas"],
        "Banca y Finanzas": ["banca", "finanzas", "gestion financiera","analista financiero", "finanzas empresariales","sector bancario", "banca y finanzas","analisis de inversiones", "inversiones y valores","teoria financiera", "microfinanzas"],
        "Seguros": ["seguros", "banca y seguros", "seguro social","riesgos financieros"],
        "Gestión Pública": ["gestion publica", "administracion publica", "sector publico","gestion estatal", "funcion publica", "gerencia publica","gestion municipal", "gobiernos regionales y locales","auditoria gubernamental", "gobernabilidad","planificacion economica regional", "control gubernamental"],
        "Gestión de Recursos Humanos": ["recursos humanos", "gestion de talento", "rrhh","administracion de personal", "capital humano","direccion de personas", "direccion del talento humano","administracion de recursos humanos", "relaciones laborales","relaciones industriales", "gestion del conocimiento"],
        "Logística y Cadena de Suministro": ["logistica", "cadena de suministro", "supply chain","abastecimiento", "gestion de suministro","ingenieria logistica", "gestion logistica", "almacen"],
        "Gestión de Seguridad y Riesgos": ["gestion de seguridad y riesgos", "gestion de riesgos","seguridad corporativa", "seguridad empresarial"],
        "Cooperativismo": ["cooperativismo", "cooperativa", "economia social"],
        "Administración Bancaria": ["administracion bancaria", "banca", "negocios bancarios"],
        "Contabilidad Técnica": ["contabilidad tecnica", "tecnico contable"],
        "Marketing Técnico": ["marketing tecnico"],
        "Secretariado": ["secretariado", "secretariado ejecutivo", "secretaria","secretario", "servicios secretariales", "secretariado legal","secretariado medico", "asistente ejecutivo", "taquigrafia","mecanografia", "recepcionista", "operacion de equipos de oficina"]
    },
    "05_ciencias_naturales_matematicas_y_estadistica": {
        "Matemática": ["matematica", "matematicas", "matematico","matematica pura", "analisis matematico","estadistica matematica", "algebra", "geometria","analisis numerico", "ciencias actuariales"],
        "Estadística": ["estadistica", "estadistico", "analisis estadistico","estadistica aplicada", "ciencias estadisticas","bioestadistica", "diseno de encuestas", "muestreo de encuestas","analitica", "estadistica teorica"],
        "Investigación Operativa": ["investigacion operativa", "programacion lineal","programacion no lineal", "programacion dinamica","simulacion", "teoria de grafos", "teoria de inventarios"],
        "Física": ["fisica", "fisico", "ciencias fisicas", "fisica teorica","fisica aplicada", "astronomia", "astrofisica","fisica medica", "optica", "fisica nuclear"],
        "Química": ["quimica", "quimico", "quimica pura","quimica aplicada", "quimica industrial","quimica inorganica", "quimica organica","quimica fisica", "quimica matematica","quimica ambiental", "quimica textil", "procesos quimicos"],
        "Biología": ["biologia", "biologo", "biologia celular","biologia molecular", "ciencias biologicas", "botanica","zoologia", "genetica", "microbiologia","oceanografia", "entomologia", "micologia","bioquimica de organismos vivos"],
        "Ciencias Ambientales": ["ciencias ambientales", "medio ambiente", "gestion ambiental","ecologia", "desarrollo ambiental", "conservacion de la naturaleza","desarrollo rural y ambiental", "investigacion sobre el clima"],
        "Ingeniería Ambiental": ["ingenieria ambiental", "ingeniero ambiental", "medio ambiente","gestion ambiental", "impacto ambiental","conservacion de suelos y aguas", "recursos naturales","prevencion de riesgos ambientales", "bosques tropicales"],
        "Recursos Hídricos": ["recursos hidricos", "hidrologia", "gestion del agua","riego y drenaje", "tratamiento de agua", "ingenieria hidraulica"],
        "Ciencias de la Tierra": ["ciencias de la tierra", "geografia", "geologia","geomatica", "meteorologia", "geodesia", "geotecnia","ingenieria aerofotografica"],
        "Ingeniería Geológica": ["ingenieria geologica", "geologia", "ingeniero geologo","exploracion geologica", "geotecnia", "geomatica"]
    },
    "06_tecnologia_de_la_informacion_y_la_comunicacion": {
        "Ciencias de la Computación": ["ciencias de la computacion", "computacion","computacion cientifica", "ciencia computacional"],
        "Ingeniería de Sistemas": ["ingenieria de sistemas", "sistemas", "ingeniero de sistemas","sistemas informaticos", "sistemas computacionales","sistemas de informacion", "modelamiento de sistemas"],
        "Ingeniería Informática": ["ingenieria informatica", "informatica", "ingeniero informatico","administracion de tecnologia de informacion"],
        "Ingeniería de Software": ["ingenieria de software", "desarrollador de software","ingeniero de software", "programador", "desarrollo de software"],
        "Sistemas y Cómputo": ["sistemas y computo", "gestion y administracion de sistemas de informacion","administrador de bases de datos", "bases de datos","auditoria informatica", "auditoria de sistemas","arquitectura de plataformas", "soporte de sistemas y redes"],
        "Computación e Informática": ["computacion e informatica", "tecnico en computacion","ofimatica", "digitacion", "operacion de computadoras","operacion de programas de computacion"],
        "Ciencia de Datos": ["ciencia de datos", "data science", "analitica de datos","ingenieria de datos"],
        "Ciberseguridad": ["ciberseguridad", "seguridad informatica","seguridad en tecnologia informatica", "seguridad de la informacion"],
        "Redes y Comunicaciones": ["redes y comunicaciones", "administracion de red","diseno de redes", "instalacion y mantenimiento de redes informaticas","teleinformatica"],
        "Ingeniería de Telecomunicaciones": ["ingenieria en telecomunicaciones", "telecomunicaciones","redes de comunicacion", "comunicaciones digitales","telematica", "procesamiento de señales", "control de transito aereo"]
    },
    "07_ingenieria_industria_y_construccion": {
        "Ingeniería Civil": ["ingenieria civil", "ingeniero civil", "construccion","estructuras", "obras civiles", "ingenieria estructural","ingenieria hidraulica", "ingenieria vial", "gerencia de obras","suelos concreto y asfaltos"],
        "Construcción Civil": ["construccion civil", "constructor civil", "ingenieria de la construccion","tecnologia de la construccion", "direccion y administracion de la construccion","albanileria", "gasfiteria", "mantenimiento de edificaciones"],
        "Arquitectura": ["arquitectura", "arquitecto", "arquitecta","diseno arquitectonico", "proyectos arquitectonicos","arquitectura estructural", "restauracion de monumentos historicos","arquitectura de interiores"],
        "Urbanismo y Diseño Urbano": ["urbanismo", "diseno urbano", "planificacion urbana","desarrollo urbano", "gestion territorial","ordenamiento territorial", "regeneracion urbana","territorio y urbanismo sostenible"],
        "Paisajismo": ["paisajismo", "diseno del paisaje", "arquitectura del paisaje","espacios verdes", "diseno ambiental"],
        "Topografía": ["topografia", "agrimensura", "ingenieria topografica","levantamiento topografico"],
        "Edificaciones": ["edificaciones", "edificaciones inteligentes","gestion inmobiliaria", "desarrollo inmobiliario", "vivienda colectiva"],
        "Ingeniería Sanitaria": ["ingenieria sanitaria", "gestion de residuos solidos","eliminacion de desechos", "aguas residuales","abastecimiento de agua potable", "alcantarillado sanitario"],
        "Ingeniería Industrial": ["ingenieria industrial", "ingeniero industrial","procesos industriales", "gestion industrial","ingenieria de procesos", "direccion y gerencia de operaciones","productividad", "aseguramiento de la calidad","sistemas integrados para la calidad","cadena de suministro", "procesos de produccion industrial"],
        "Ingeniería Electrónica": ["ingenieria electronica", "ingeniero electronico","circuitos", "electronica aplicada", "microelectronica","electronica", "ingenieria de control","procesamiento digital de señales"],
        "Electrónica Industrial": ["electronica industrial", "instrumentacion industrial","mantenimiento electronico industrial","controlista de maquinas y procesos industriales"],
        "Mecatrónica y Automatización": ["mecatronica", "automatizacion", "automatizacion y control","robotica", "ingenieria de control", "edificios inteligentes","control de procesos", "bioingenieria", "biomedica"],
        "Ingeniería Eléctrica": ["ingenieria electrica", "ingeniero electrico","electricidad industrial", "sistemas electricos","sistemas electricos de potencia", "generacion de energia electrica","electrotecnia", "instalacion y mantenimiento de lineas electricas"],
        "Electricista": ["electricista", "instalacion electrica", "electrotecnica","electricidad comercial", "electricista industrial","mantenimiento electrico"],
        "Ingeniería en Energías Renovables": ["energias renovables", "ingeniero en energias","energia solar", "energia eolica", "tecnologias limpias","tecnologia energetica", "gestion de la energia","energia hidraulica", "energia termica"],
        "Ingeniería Química": ["ingenieria quimica", "ingeniero quimico","procesos quimicos", "industria quimica"],
        "Ingeniería Mecánica": ["ingenieria mecanica", "ingeniero mecanico","mecanica industrial", "mecanica de maquinas","mantenimiento de maquinaria", "mecanica de fluidos", "motores"],
        "Ingeniería Electromecánica": ["ingenieria electromecanica", "electromecanica","maquinas electricas", "sistemas electromecanicos"],
        "Mecánica de Producción": ["mecanica de produccion", "tecnico mecanico","manufactura", "mecanizado", "torneado", "cnc","fabricacion de herramientas y troqueles"],
        "Mecánica Automotriz": ["mecanica automotriz", "automotriz", "autotronica","mantenimiento de vehiculos motorizados", "motores y vehiculos"],
        "Ingeniería de Materiales y Metalúrgica": ["ingenieria de materiales", "ingenieria metalurgica","metalurgia", "geometalurgia", "materiales metalicos","materiales no metalicos"],
        "Soldadura y Metalmecánica": ["soldadura", "metalmecanica", "construcciones metalicas","modeleria y fundicion", "matriceria", "metal laminado"],
        "Ingeniería Agroindustrial": ["ingenieria agroindustrial", "agroindustria","ingeniero agroindustrial", "procesamiento de alimentos","agroalimentaria"],
        "Ingeniería en Industrias Alimentarias": ["industrias alimentarias", "ingenieria en alimentos","tecnologia de alimentos", "procesamiento de alimentos","ciencia y tecnologia de los alimentos", "seguridad alimentaria","control alimentario", "conservacion de alimentos"],
        "Ingeniería Textil y Confecciones": ["ingenieria textil", "confecciones", "industria textil","produccion textil", "diseno y produccion textil","tecnologia textil", "gestion de modas y confecciones","tapiceria", "tintoreria textil", "hilado", "bordados"],
        "Ingeniería de Minas": ["ingenieria de minas", "mineria", "ingeniero de minas","operaciones mineras", "geomecanica minera", "gestion minera","tecnologia minera", "explotacion minera", "concentracion de minerales"],
        "Ingeniería de Petróleo": ["ingenieria de petroleo", "ingeniero de petroleo","extraccion de petroleo", "industria petrolera","petroleo y gas natural", "petroquimica","extraccion de gas", "operaciones de perforacion"],
        "Ingeniería Naval y Aeronáutica": ["ingenieria naval", "ingenieria maritima","ingenieria aeronautica", "ingenieria aeroespacial","marina mercante", "construccion naval", "avionica","mantenimiento de aeronaves", "maquinas navales"],
        "Operación de Maquinaria Pesada": ["maquinaria pesada", "operador de maquinaria pesada","supervision de equipos de mineria"]
    },
    "08_agricultura_silvicultura_pesca_y_veterinaria": {
        "Agronomía": ["agronomia", "ingeniero agronomo", "agricultura","produccion agricola", "ciencias agrarias", "agroforestal","manejo integrado de plagas", "sanidad vegetal", "fruticultura","caficultura", "viticultura", "desarrollo agrario"],
        "Ingeniería Agrícola": ["ingenieria agricola", "ingeniero agricola","tecnologia agricola", "infraestructura agricola","riego drenaje", "manejo de instalaciones y equipos agricolas"],
        "Agropecuaria": ["agropecuaria", "produccion agricola y ganadera","ciencias pecuarias", "produccion animal","produccion y salud animal", "ganaderia"],
        "Zootecnia": ["zootecnia", "zootecnista", "produccion animal","ganaderia", "nutricion animal", "ciencia animal","produccion de rumiantes", "avicultura"],
        "Horticultura": ["horticultura", "floricultura", "jardineria","conservacion verde", "tecnicas horticolas","manejo de viveros", "cultivo de cesped"],
        "Ingeniería Forestal": ["ingenieria forestal", "ingeniero forestal","manejo forestal", "bosques", "conservacion forestal","ciencias forestales", "productos forestales"],
        "Silvicultura": ["silvicultura", "forestacion", "reforestacion","explotacion forestal", "tala de arboles","bosque y gestion de recursos forestales"],
        "Ingeniería Agrónoma": ["ingenieria agronoma"],
        "Ingeniería Pesquera": ["ingenieria pesquera", "pesca industrial", "pesqueria","recursos hidrobiologicos", "tecnologia pesquera","ciencia y tecnologia de la pesca", "gestion pesquera","hidrobiologia", "ciencias del mar"],
        "Acuicultura": ["acuicultura", "ingenieria acuicola", "sanidad acuicola","ecosistemas y recursos acuaticos", "extraccion pesquera"],
        "Veterinaria": ["veterinaria", "medico veterinario", "veterinario","salud animal", "medicina veterinaria", "ciencia veterinaria","asistencia veterinaria", "patologia veterinaria","epidemiologia de origen animal"]
    },
    "09_salud_y_bienestar": {
        "Medicina Humana": ["medicina", "medicina humana", "medico", "doctora","doctor", "salud general", "salud humana","medicina integral", "medicina rural", "medicina legal y forense","medicina quirurgica", "anestesiologia", "cirugia","infectologia", "enfermedades infecciosas y tropicales","paramedico", "ciencias de la salud"],
        "Enfermería": ["enfermeria", "enfermera", "enfermero","cuidados de salud", "auxiliar de enfermeria","enfermeria familiar y comunitaria","enfermeria en la salud de la mujer y el niño","enfermeria en cuidados intensivos","terapia intensiva en enfermeria", "gestion en enfermeria","inyectables y primeros auxilios"],
        "Odontología": ["odontologia", "odontologo", "odontologa", "dentista","cirujano dental", "estomatologia", "ciencias estomatologicas","implantologia oral", "odontopediatria", "periodoncia","ortodoncia", "protesis dental", "higiene dental","asistencia dental", "rehabilitacion oral", "cirugia bucal"],
        "Obstetricia": ["obstetricia", "obstetra", "partos", "atencion materna","salud reproductiva", "puericultura", "salud materno perinatal","psicoprofilaxis obstetrica", "emergencias obstetricas","riesgo obstetrico", "bienestar fetal"],
        "Tecnología Médica": ["tecnologia medica", "tecnologo medico","laboratorio clinico", "imagenologia", "radiologia","tecnologia de diagnostico", "banco de sangre y hemoterapia","optometria", "patologia", "medicina nuclear","radiodiagnostico", "ecografia", "tecnologia de laboratorio clinico","resonancia magnetica", "tomografia", "radioterapia","equipos electromedicos"],
        "Terapia y Rehabilitación": ["terapia y rehabilitacion", "terapia fisica","rehabilitacion fisica", "fisioterapia", "terapia ocupacional","terapia del lenguaje", "fonoaudiologia", "medicina fisica","rehabilitacion", "ortopedia"],
        "Farmacia y Bioquímica": ["farmacia", "bioquimica", "farmaceutico","quimico farmaceutico", "farmacia clinica","ciencias farmaceuticas", "farmacologia","tecnologia farmaceutica", "farmacocinetica","regulacion farmaceutica", "productos naturales terapeuticos","toxicologia", "bromatologia"],
        "Nutrición": ["nutricion", "nutricionista", "alimentacion saludable","nutricion clinica", "dietetica", "soporte nutricional","manejo nutricional", "diabetes y obesidad","gestion alimentaria", "bromatologia y nutricion"],
        "Salud Pública": ["salud publica", "epidemiologia", "gestion en salud","promocion de la salud", "sanidad publica","salud colectiva", "salud global", "promocion comunal","prevencion de its", "prevencion de vih"],
        "Trabajo Social": ["trabajo social", "asistente social", "trabajador social","trabajadora social", "intervencion social","servicio social", "bienestar social", "inclusion social","familia y redes sociales", "asesoramiento familiar","desarrollo local"],
        "Gerontología y Cuidado del Adulto Mayor": ["gerontologia", "gerontologia social", "geriatria","cuidado del adulto mayor", "asistente del adulto mayor","cuidado personal del adulto mayor","personas con discapacidad", "enfermeria en cuidado del adulto mayor"],
        "Cuidado Infantil y Servicios para Jóvenes": ["desarrollo integral del niño", "cuidado de niños","guarderia", "servicios para jovenes","salud mental del niño y adolescente","cuidado no medico de niños", "asistente de niños","crecimiento y desarrollo", "adolescente"],
        "Ingeniería Biomédica": ["ingenieria biomedica", "equipos electromedicos","bioinformatica", "ingenieria biotecnologica molecular","genetica y biotecnologia"],
        "Administración y Gestión en Salud": ["administracion hospitalaria", "direccion y gestion de servicios de salud","gestion de servicios de salud", "atencion integral en salud","auditoria medica", "proyectos de salud", "salud intercultural"],
        "Enfermería Técnica": ["enfermeria tecnica", "tecnico en enfermeria"],
        "Farmacia Técnica": ["farmacia tecnica", "tecnico en farmacia"]
    },
    "00_servicios": {
        "Cosmetología y Estética": ["cosmetologia", "cosmiatria", "barberia", "peluqueria","manicura", "pedicura", "terapia de la belleza","maquillaje", "estetica facial", "cuidado de manos y pies"],
        "Ciencias del Deporte": ["ciencias del deporte", "actividad fisica", "cultura fisica","gestion deportiva", "entrenamiento deportivo", "kinesiologia","arbitraje deportivo", "tecnicas y habilidades deportivas"],
        "Saneamiento y Salud Comunitaria": ["saneamiento de la comunidad", "investigacion epidemiologica","epidemiologia", "salud publica y salud global","salud colectiva", "promocion comunal", "inmunologia","prevencion de its", "prevencion de vih"],
        "Seguridad y Salud en el Trabajo": ["seguridad y salud en el trabajo", "seguridad y salud ocupacional","seguridad laboral", "higiene y seguridad industrial","ergonomia laboral", "prevencion de riesgos laborales","gestion integral en seguridad ocupacional","proteccion del trabajador"],
        "Ciencias Militares y Defensa": ["educacion militar y de defensa", "ciencias militares","ciencias navales", "ciencias aeroespaciales","desarrollo y defensa nacional", "geopolitica","ingenieria de armas", "inteligencia estrategica","seguridad e instruccion militar", "infanteria de marina","fuerzas especiales", "submarinos", "artilleria"],
        "Ciencias Policiales": ["ciencias policiales", "policiales", "administracion y ciencias policiales","seguridad y defensa civil", "guardacostas","buceo y salvamento", "investigacion privada"],
        "Administración Hotelera": ["administracion hotelera", "gestion hotelera", "hotel y turismo","gerencia hotelera", "hoteleria", "hosteleria","recepcion hotelera", "servicios hoteleros", "hospitalidad"],
        "Administración en Turismo": ["administracion en turismo", "gestion turistica","turismo y hoteleria", "gestion en turismo","turismo", "ecoturismo", "promocion turistica","guia turistica", "turismo cultural", "operaciones hoteleras y de viajes"],
        "Ingeniería de Transporte": ["ingenieria de transporte", "transportes","gestion aeroportuaria", "estudios de transporte","transporte maritimo"],
        "Cocina y Gastronomía": ["gastronomia", "cocina", "chef", "arte culinario","gestion de restaurantes", "barman", "servicio de restaurante y bar","asistencia de cocina", "servicio de mesa"],
        "Panadería y Pastelería": ["panaderia", "pasteleria", "panadero", "pastelero","reposteria", "confiteria"]
    },
    "99_otros": {
        "Secundaria Completa": ["x secundaria", "secundaria completa"],
        "Todas Las Carreras": ["todas las carreras"]
    }
}

def build_career_structure(raw_map: dict):
    careers = []
    auto_id = 1

    for category, items in raw_map.items():
        for name, keywords in items.items():
            careers.append({
                "id": auto_id,
                "name": name,
                "slug": slugify(name),
                "category": category,
                "keywords": list(set([k.lower() for k in keywords])),

                # 🔐 FLAG DE CONTROL
                "allow_update": False
            })
            auto_id += 1

    return careers#"careers": careers}

def save_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    data = build_career_structure(CAREER_KEYWORDS_MAP)
    save_json(data, "careers.json")
