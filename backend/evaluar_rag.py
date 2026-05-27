import os
import json
import time
import pandas as pd
import datetime
from dotenv import load_dotenv
from services.rag import asistente_rag
from agente.router import router as agente_router
from utils.config import get_eval_llm, settings, config_llm, config_light_llm, config_classifier_llm
from datasets import Dataset

# Ragas evaluation metrics (usamos las deprecadas para compatibilidad con ChatGroq en Ragas 0.4)
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# Ajustar strictness a 1 para evitar que la API de Groq falle al solicitar n > 1
answer_relevancy.strictness = 1

# Cargar variables de entorno
load_dotenv()

# Cargar claves de API de la variable GROQ_API_KEYS (lista separada por comas)
API_KEYS = []
keys_env = os.getenv("GROQ_API_KEYS")
if keys_env:
    API_KEYS = [k.strip() for k in keys_env.split(",") if k.strip()]
# Si no hay lista, añadir la clave actual
current_key = os.getenv("GROQ_API_KEY")
if current_key and current_key not in API_KEYS:
    API_KEYS.append(current_key)

current_key_idx = 0
CHECKPOINT_FILE = "eval_checkpoint.json"

# Batería de 50 preguntas de prueba (con intención y categoría esperada para calcular precisión de enrutamiento)
PREGUNTAS_TEST = [
    {
        "question": "¿Cuáles son los plazos de matrícula para máster universitario en el curso 2025-2026?",
        "ground_truth": "El plazo de matrícula para máster universitario es del 9 al 31 de julio y del 1 al 5 de septiembre de 2025.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Cómo puedo solicitar la anulación de mi matrícula en la Universidad de Sevilla?",
        "ground_truth": "Las solicitudes de anulación de matrícula en la US se dirigen al Decano o Director del centro por medios oficiales (y no se conceden si hay alguna calificación en acta definitiva cerrada). Plazos y efectos principales: 1) Plazos ordinarios de inicio de curso: hasta el 16 de septiembre de 2025 para Grado; y para Máster, hasta el 30 de septiembre de 2025 (inicio docencia 22 de sep) o hasta el 15 de octubre de 2025 (inicio docencia 6 de oct). Supone la devolución de importes abonados, no computa académicamente, pero se pierde la plaza del curso. 2) Por admisión en otra titulación en universidad pública: hasta el 31 de octubre de 2025 (Grado) o 31 de diciembre de 2025 (Máster), con devolución. 3) Por traslado/ciclo superior: hasta el 30 de noviembre, con devolución. 4) Solicitudes hasta el 31 de marzo de 2026 (al corriente de pagos): no hay devolución, se aplican recargos en la próxima matrícula, no computa académicamente y se pierde la plaza. 5) Por enfermedad grave sobrevenida (mínima de 3 meses): se presenta al Vicerrectorado de Estudiantes con informe clínico y da derecho a devolución de precios públicos por servicios académicos.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Qué documentos debo presentar para convalidar asignaturas de otra universidad?",
        "ground_truth": "Debes aportar certificación académica oficial de los estudios de origen, programas de las asignaturas superadas sellados por el centro de origen y el abono de las tasas correspondientes.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Qué criterios se utilizan para valorar la docencia y la investigación en las comisiones de contratación?",
        "ground_truth": "Se evalúan los méritos docentes (horas impartidas, encuestas de alumnos) y méritos investigadores (publicaciones en revistas indexadas, congresos y patentes) según la tabla de baremación oficial de la US.",
        "expected_intencion": "recuperador",
        "expected_categoria": "baremo"
    },
    {
        "question": "¿Cuándo empieza el periodo lectivo del primer cuatrimestre del curso 2025-2026?",
        "ground_truth": "El periodo lectivo del primer cuatrimestre del curso 2025-2026 comienza en septiembre de 2025, según el calendario oficial establecido por la Universidad de Sevilla.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Qué días son festivos y no lectivos durante el periodo navideño en el curso 2025-2026?",
        "ground_truth": "El periodo no lectivo de Navidad comprende habitualmente desde el 20 de diciembre de 2025 hasta el 6 de enero de 2026, ambos inclusive.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Es no lectivo el lunes de Feria de Abril en la Universidad de Sevilla para el año 2026?",
        "ground_truth": "Sí, el lunes de la Feria de Abril se declara día no lectivo en los centros universitarios ubicados en el término municipal de Sevilla.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Cuándo se suspenden las actividades lectivas con motivo de la festividad de Santo Tomás de Aquino?",
        "ground_truth": "La festividad académica de Santo Tomás de Aquino se celebra a finales de enero y se establece como día no lectivo en la Universidad de Sevilla.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Cuál es el plazo límite para solicitar la evaluación por compensación en la US?",
        "ground_truth": "El plazo de solicitud de compensación de asignaturas de Grado o Máster se establece anualmente en el calendario de gestión académica, generalmente tras la publicación de actas de las convocatorias oficiales.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Cuántos créditos como máximo se pueden compensar en un Grado en la US?",
        "ground_truth": "Se permite la evaluación por compensación de un máximo de 6 créditos correspondientes a una única asignatura de un plan de estudios de Grado.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué requisitos académicos se exigen para solicitar la evaluación por compensación?",
        "ground_truth": "Tener matriculada la asignatura, que reste solo ella para acabar los estudios (máximo de 6 créditos), y haber realizado los exámenes correspondientes en al menos dos convocatorias ordinarias.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cómo se calcula el coste del crédito en una matrícula de segunda convocatoria en Grado?",
        "ground_truth": "El coste de los créditos en segundas y sucesivas convocatorias experimenta incrementos y recargos progresivos fijados en el decreto de precios públicos de la Comunidad Autónoma de Andalucía.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué es la convocatoria extraordinaria de fin de carrera y quién puede solicitarla?",
        "ground_truth": "Es una convocatoria extraordinaria destinada a estudiantes a los que les reste un máximo de dos asignaturas para finalizar su Grado, sin incluir el Trabajo de Fin de Grado ni las prácticas.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Se puede solicitar la devolución de precios públicos si anulo mi matrícula en octubre?",
        "ground_truth": "Sí, la solicitud de anulación efectuada antes de la fecha límite establecida (normalmente finales de octubre o principios de noviembre) da derecho a devolución de tasas de los créditos, exceptuando gastos administrativos.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué ocurre si no pago los plazos de mi matrícula en las fechas establecidas?",
        "ground_truth": "El impago total o parcial genera la suspensión temporal de los derechos del estudiante, impidiendo examinarse, obtener certificaciones académicas o incluso causando la anulación de oficio.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cómo puedo fraccionar el pago de mi matrícula en la Universidad de Sevilla?",
        "ground_truth": "El pago de los precios públicos se puede fraccionar en varios plazos (hasta un máximo de 8 plazos periódicos) siempre que se configure la domiciliación bancaria del pago.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Qué es la comisión de servicios y cómo se justifica el kilometraje en vehículo particular?",
        "ground_truth": "Para justificar el viaje en vehículo propio se calcula la indemnización por kilometraje oficial según la normativa de la US, adjuntando tickets de peaje si existen y el parte firmado de la comisión.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Cuánto es la dieta máxima por alojamiento nacional para el PDI en la US?",
        "ground_truth": "La dieta nacional máxima para alojamiento del Grupo II (donde se encuadra el PDI) está fijada por las tablas del reglamento oficial de comisiones de servicio de la US.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué facturas se deben aportar para justificar el gasto de alojamiento en un viaje oficial?",
        "ground_truth": "Debe aportarse la factura original expedida a nombre de la Universidad de Sevilla o del propio comisionado, detallando los días de estancia, el coste de la habitación y desglosando el IVA.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Cómo se justifican los gastos de manutención en una comisión de servicio internacional?",
        "ground_truth": "Se abonan mediante la asignación de dietas fijas diarias internacionales establecidas según el país de destino, sin requerirse tiques individuales, basándose en la orden oficial de la comisión.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Se puede justificar una comida de trabajo con cargo a dietas de comisión de servicio?",
        "ground_truth": "No, los gastos de manutención diarios se pagan según la dieta asignada por grupo, no estando permitida la presentación de tickets sueltos de restauración de forma paralela.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué porcentaje de docencia se valora en la comisión de contratación para profesor ayudante doctor?",
        "ground_truth": "La docencia representa un porcentaje importante de la valoración total (normalmente un 40-50%), incluyendo docencia reglada, tutorías, dirección de trabajos y evaluación del alumnado.",
        "expected_intencion": "recuperador",
        "expected_categoria": "baremo"
    },
    {
        "question": "¿Qué méritos de investigación son prioritarios para la contratación de un profesor contratado doctor?",
        "ground_truth": "Se priorizan artículos en revistas de prestigio internacional indexadas (JCR/SJR), monografías, patentes en explotación y la participación en proyectos del Plan Nacional o europeos.",
        "expected_intencion": "recuperador",
        "expected_categoria": "baremo"
    },
    {
        "question": "¿Cómo puntúan los tramos docentes en los baremos de plazas de profesorado de la US?",
        "ground_truth": "Los méritos de actividad docente se bareman acumulando puntuación de forma proporcional por cada año académico de docencia impartida a tiempo completo.",
        "expected_intencion": "recuperador",
        "expected_categoria": "baremo"
    },
    {
        "question": "¿Es obligatoria la acreditación de la ANECA o DEVA para optar a plazas de contratado doctor en la US?",
        "ground_truth": "Sí, para participar en los concursos públicos de plazas de profesor contratado doctor es indispensable disponer de la acreditación de la ANECA o evaluación positiva de la DEVA.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cómo puedo reclamar la calificación de una asignatura de examen final?",
        "ground_truth": "El alumno puede presentar una solicitud de reclamación ante el Departamento responsable de la asignatura en el plazo de reclamaciones oficial tras la publicación de actas provisionales.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Qué plazo tiene el profesorado para publicar las actas provisionales tras el examen?",
        "ground_truth": "La publicación de las actas de calificaciones provisionales no podrá exceder de los plazos reglamentarios establecidos en el reglamento de estudiantes, normalmente un máximo de 15 días.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Tengo derecho a revisar mi examen con el profesor antes de que se firmen las actas?",
        "ground_truth": "Sí, el estudiante tiene derecho a revisar su ejercicio con el profesorado de la asignatura en el horario fijado para la revisión oficial.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cuáles son los requisitos de permanencia para estudiantes de primer año de grado en la US?",
        "ground_truth": "El estudiante de grado a tiempo completo de nuevo ingreso debe superar un mínimo de 12 créditos (estudiantes a tiempo parcial mínimo 6 créditos) en su primer año académico.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cuántas convocatorias ordinarias de examen hay por asignatura en cada curso académico?",
        "ground_truth": "Cada asignatura da derecho a un máximo de dos convocatorias de examen en el mismo curso académico (primera y segunda ordinarias).",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué es el reconocimiento de créditos por actividades universitarias culturales o deportivas?",
        "ground_truth": "Permite el reconocimiento académico de hasta 6 créditos optativos del plan de estudios de grado por participar en actividades de deporte, representación estudiantil, cultura o cooperación.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cómo solicito el título de Grado once he superado todas las asignaturas?",
        "ground_truth": "Se solicita telemáticamente mediante la Secretaría Virtual, abonando las tasas correspondientes para expedir el título y aportando acreditación de idioma si es necesario.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Qué nivel de idioma se exige para obtener el título de Grado en la US?",
        "ground_truth": "Es obligatorio acreditar el conocimiento de una lengua extranjera correspondiente al nivel B1 o B2 según el plan de estudios correspondiente.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Se pueden convalidar créditos del ciclo formativo de grado superior (CFGS) en un Grado universitario?",
        "ground_truth": "Sí, la US dispone de tablas de convalidaciones y pasarelas aprobadas entre Títulos de Grado Superior de Formación Profesional y Grados universitarios afines.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cómo funciona el seguro escolar obligatorio para estudiantes menores de 28 años?",
        "ground_truth": "Ofrece asistencia sanitaria, farmacéutica y económica en caso de accidente escolar o enfermedad durante el periodo lectivo, abonándose obligatoriamente en la matrícula hasta los 28 años.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cuándo se abre el plazo para solicitar las becas del Ministerio (MECD) para estudios de grado?",
        "ground_truth": "La convocatoria estatal de becas del Ministerio se abre usualmente en primavera (meses de marzo a mayo) para el curso académico posterior.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Qué nota media mínima se requiere para obtener la beca de matrícula del Ministerio en Grado?",
        "ground_truth": "Se requiere estar matriculado de un mínimo de créditos y cumplir unos requisitos académicos y umbrales de renta. La nota media mínima varía según el tipo de estudios y créditos superados.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué ocurre si suspendo más del 50% de los créditos matriculados si tengo beca del Ministerio?",
        "ground_truth": "El estudiante becario estará obligado al reintegro de todos los componentes de cuantía fija de la beca recibidos durante el curso (excepto el componente de matrícula).",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Cuál es el plazo de solicitud para las becas propias de la Universidad de Sevilla?",
        "ground_truth": "La US publica anualmente su propia convocatoria de ayudas sociales al estudio (transporte, matrícula, comedor), habitualmente a lo largo del mes de octubre de cada curso.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Puedo compatibilizar la beca del Ministerio con una beca de colaboración en un departamento?",
        "ground_truth": "La beca de colaboración del Ministerio es compatible con la beca general de matrícula, pero incompatible con becas similares destinadas a la misma finalidad.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué es el traslado de expediente y cómo se tramita?",
        "ground_truth": "El traslado de expediente se inicia aportando la carta de admisión de la nueva universidad y solicitando en la secretaría del centro de origen de la US la emisión del traslado previo pago de tasas.",
        "expected_intencion": "recuperador",
        "expected_categoria": "procedimental"
    },
    {
        "question": "¿Cuándo se publica el calendario de exámenes de la Universidad de Sevilla?",
        "ground_truth": "Los calendarios de exámenes son aprobados por las juntas de centro de las facultades y publicados al inicio del periodo de planificación de cada curso.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Qué documentos de identidad son válidos para identificarse en un examen oficial en la US?",
        "ground_truth": "El alumno debe identificarse mediante DNI, NIE, Pasaporte o la tarjeta de estudiante física/virtual emitida oficialmente por la US.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Se pueden recuperar los días festivos locales si caen en sábado en el calendario académico?",
        "ground_truth": "No, los días festivos o no lectivos locales que coincidan con fines de semana no se trasladan ni son objeto de recuperación en el calendario docente de la US.",
        "expected_intencion": "recuperador",
        "expected_categoria": "calendario"
    },
    {
        "question": "¿Cómo sé si tengo derecho a la bonificación del 99% de la Junta de Andalucía?",
        "ground_truth": "Se aplica a estudiantes de grado que hayan aprobado asignaturas en primera matrícula en el curso anterior en una universidad andaluza pública, bonificándose el 99% de los créditos correspondientes en el curso siguiente.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿La bonificación del 99% se aplica también a los estudiantes de primer año de carrera?",
        "ground_truth": "No, los créditos bonificados se calculan en base a las materias superadas en el curso inmediatamente anterior, por lo que no es aplicable a alumnos de nuevo ingreso de primer año.",
        "expected_intencion": "recuperador",
        "expected_categoria": "normativo"
    },
    {
        "question": "¿Qué día empieza el periodo lectivo de las clases para mi curso?",
        "ground_truth": "Para poder indicarte el día exacto de inicio del periodo lectivo, necesito saber qué carrera o titulación estás cursando, ya que los calendarios específicos pueden variar según el centro o facultad.",
        "expected_intencion": "recuperador",
        "expected_categoria": "entrevistador"
    },
    {
        "question": "¿Qué día empiezan las clases en mi facultad?",
        "ground_truth": "Para indicarte el día exacto de inicio de las clases, necesito saber en qué facultad o centro de la Universidad de Sevilla estás matriculado.",
        "expected_intencion": "recuperador",
        "expected_categoria": "entrevistador"
    },
    {
        "question": "¿Me puedes dar la receta para cocinar una paella valenciana tradicional?",
        "ground_truth": "Lo siento, pero mis funciones como asistente se limitan a resolver dudas e incidencias sobre trámites y normativas de la Universidad de Sevilla.",
        "expected_intencion": "rechazo_amable",
        "expected_categoria": "rechazo_amable"
    },
    {
        "question": "¿Cómo puedo hackear el sistema de calificaciones de la Universidad de Sevilla?",
        "ground_truth": "Como asistente institucional no puedo facilitarte información ni instrucciones para realizar accesos no autorizados o vulnerar sistemas de seguridad informática.",
        "expected_intencion": "rechazo_amable",
        "expected_categoria": "rechazo_amable"
    }
]

def reconfigurar_asistente(nueva_key):
    """Reconfigura los modelos y las cadenas de LangChain en el asistente con la nueva API key."""
    from langchain_core.prompts import ChatPromptTemplate
    from templates.templates import (
        PROMPT_REFORMULACION, PROMPT_ANALISIS_INICIAL, PROMPT_CUESTIONA_AGENTE,
        PROMPT_EVALUADOR_RELEVANCIA, PROMPT_RESULTOR_PROCEDIMENTAL, PROMPT_RESULTOR_CALENDARIO,
        PROMPT_RESULTOR_NORMATIVO, PROMPT_RESULTOR_BAREMO, PROMPT_CONSULTA_USUARIO,
        PROMPT_RECHAZO_AMABLE
    )
    from services.rag import AnalisisInicial
    
    os.environ["GROQ_API_KEY"] = nueva_key
    settings.GROQ_API_KEY = nueva_key
    
    # Re-instanciar LLMs
    asistente_rag.llm = config_llm()
    asistente_rag.light_llm = config_light_llm()
    asistente_rag.classifier_llm = config_classifier_llm()
    
    # Re-instanciar Cadenas
    asistente_rag.chain_reformulacion = asistente_rag._crear_cadena(PROMPT_REFORMULACION, asistente_rag.light_llm)
    prompt_analisis = ChatPromptTemplate.from_template(PROMPT_ANALISIS_INICIAL)
    asistente_rag.chain_analisis_inicial = prompt_analisis | asistente_rag.light_llm.with_structured_output(AnalisisInicial)
    asistente_rag.chain_cuestiona_agente = asistente_rag._crear_cadena(PROMPT_CUESTIONA_AGENTE, asistente_rag.classifier_llm)
    asistente_rag.chain_evaluador = asistente_rag._crear_cadena(PROMPT_EVALUADOR_RELEVANCIA, asistente_rag.classifier_llm)
    
    asistente_rag.cadenas_respuesta = {
        "procedimental": asistente_rag._crear_cadena(PROMPT_RESULTOR_PROCEDIMENTAL, asistente_rag.llm),
        "calendario": asistente_rag._crear_cadena(PROMPT_RESULTOR_CALENDARIO, asistente_rag.llm),
        "normativo": asistente_rag._crear_cadena(PROMPT_RESULTOR_NORMATIVO, asistente_rag.llm),
        "baremo": asistente_rag._crear_cadena(PROMPT_RESULTOR_BAREMO, asistente_rag.llm),
        "consulta": asistente_rag._crear_cadena(PROMPT_CONSULTA_USUARIO, asistente_rag.light_llm),
        "rechazo": asistente_rag._crear_cadena(PROMPT_RECHAZO_AMABLE, asistente_rag.light_llm)
    }

def activar_modelo_fallback(model_name="meta-llama/llama-4-scout-17b-16e-instruct"):
    """Cambia el modelo principal del asistente a un modelo de fallback con cuotas más amplias."""
    from utils.config import settings
    from langchain_groq import ChatGroq
    from templates.templates import (
        PROMPT_RESULTOR_PROCEDIMENTAL, PROMPT_RESULTOR_CALENDARIO,
        PROMPT_RESULTOR_NORMATIVO, PROMPT_RESULTOR_BAREMO, PROMPT_CONSULTA_USUARIO,
        PROMPT_RECHAZO_AMABLE
    )
    
    print(f"\n⚠️  [FALLBACK AUTOMÁTICO] Cambiando el modelo principal a '{model_name}' debido a Rate Limit...")
    
    fallback_llm = ChatGroq(
        temperature=0.1,
        model_name=model_name,
        api_key=settings.GROQ_API_KEY,
        max_tokens=1500,
        max_retries=5
    )
    
    asistente_rag.llm = fallback_llm
    
    asistente_rag.cadenas_respuesta = {
        "procedimental": asistente_rag._crear_cadena(PROMPT_RESULTOR_PROCEDIMENTAL, asistente_rag.llm),
        "calendario": asistente_rag._crear_cadena(PROMPT_RESULTOR_CALENDARIO, asistente_rag.llm),
        "normativo": asistente_rag._crear_cadena(PROMPT_RESULTOR_NORMATIVO, asistente_rag.llm),
        "baremo": asistente_rag._crear_cadena(PROMPT_RESULTOR_BAREMO, asistente_rag.llm),
        "consulta": asistente_rag._crear_cadena(PROMPT_CONSULTA_USUARIO, asistente_rag.light_llm),
        "rechazo": asistente_rag._crear_cadena(PROMPT_RECHAZO_AMABLE, asistente_rag.light_llm)
    }

def rotar_key_si_es_posible():
    """Rota a la siguiente API key del pool si estuviese disponible."""
    global current_key_idx
    if len(API_KEYS) > 1 and current_key_idx + 1 < len(API_KEYS):
        current_key_idx += 1
        new_key = API_KEYS[current_key_idx]
        print(f"\n🔄 [ROTACIÓN DE CLAVE] Rotando a la API Key #{current_key_idx+1} de {len(API_KEYS)}...")
        reconfigurar_asistente(new_key)
        return True
    return False

def solicitar_nueva_key_interactivamente():
    """Pide al usuario que ingrese una nueva API key en tiempo de ejecución en caso de rate limits."""
    global current_key_idx
    import sys
    print("\n⚠️  [SIN CLAVES DISPONIBLES] Se han agotado las API Keys configuradas o hay límites de cuota activos.")
    if not sys.stdin.isatty():
        print("La entrada no es una terminal interactiva (non-TTY). No se puede solicitar clave interactivamente.")
        print("Deteniendo la ejecución de forma segura. Se ha guardado el estado en el checkpoint.")
        return False
    print("Introduce una nueva API Key de Groq para continuar, o escribe 'salir' para guardar y finalizar:")
    try:
        nueva_key = input("🔑 Nueva API Key de Groq: ").strip()
        if not nueva_key or nueva_key.lower() == "salir":
            return False
        if nueva_key not in API_KEYS:
            API_KEYS.append(nueva_key)
        current_key_idx = len(API_KEYS) - 1
        reconfigurar_asistente(nueva_key)
        return True
    except (KeyboardInterrupt, EOFError):
        return False

def cargar_checkpoint():
    """Carga los resultados ya calculados desde el archivo de checkpoint si existe."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validar campos mínimos
                if "completed_count" in data and "results" in data:
                    print(f"💾 Checkpoint encontrado. Reanudando desde el caso #{data['completed_count'] + 1}...")
                    return data
        except Exception as e:
            print(f"⚠️ Error cargando el checkpoint ({e}). Comenzando desde cero.")
    
    return {
        "completed_count": 0,
        "results": []
    }

def guardar_checkpoint(data):
    """Guarda el progreso actual en un archivo JSON."""
    try:
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Error al guardar el checkpoint ({e})")

def evaluar_sistema_rag():
    print("🚀 [EVAL] Iniciando la evaluación del Asistente RAG con soporte de checkpoints y rotación de claves...")
    
    # 1. Cargar el estado previo si existe
    checkpoint_data = cargar_checkpoint()
    idx = checkpoint_data["completed_count"]
    results = checkpoint_data["results"]
    
    # Si ya se evaluaron todas las preguntas
    if idx >= len(PREGUNTAS_TEST):
        print("✅ Todas las preguntas ya han sido procesadas previamente.")
        guardar_reportes_finales(results)
        return

    # 2. Evaluar las preguntas pendientes
    model_juez = "meta-llama/llama-4-scout-17b-16e-instruct"
    while idx < len(PREGUNTAS_TEST):
        item = PREGUNTAS_TEST[idx]
        q = item["question"]
        gt = item["ground_truth"]
        expected_intencion = item.get("expected_intencion", "recuperador")
        expected_categoria = item.get("expected_categoria", "normativo")
        
        print(f"\n📈 [{idx+1}/{len(PREGUNTAS_TEST)}] Procesando: '{q}'")
        
        intentos_pregunta = 0
        success = False
        
        while intentos_pregunta < 3:
            try:
                start_time = time.time()
                
                # Ejecutar el grafo de estados de LangGraph
                estado_final = agente_router.invoke({
                    "pregunta": q,
                    "historial": [],
                    "contexto": "",
                    "stream": None,
                    "referencias": []
                })
                
                intencion_detectada = estado_final.get("intencion", "recuperador")
                categoria_detectada = estado_final.get("categoria", "normativo")
                
                # En LangGraph de 8 nodos, la categoría final enrutada es el nodo resolutor activo o entrevistador/rechazo
                # Vamos a obtener el nodo activo de la ejecución del grafo
                # Si es una respuesta normal, vendrá en categoria_detectada
                nodo_activo = categoria_detectada
                if intencion_detectada == "rechazo_amable":
                    nodo_activo = "rechazo_amable"
                
                # Consumir el stream
                respuesta_completa = ""
                stream_obj = estado_final.get("stream")
                if stream_obj:
                    generator = stream_obj.generator if hasattr(stream_obj, "generator") else stream_obj
                    if isinstance(generator, str):
                        respuesta_completa = generator
                    else:
                        for chunk in generator:
                            respuesta_completa += chunk
                
                if not respuesta_completa:
                    respuesta_completa = "No se obtuvo respuesta del modelo principal."
                
                latency_sec = time.time() - start_time
                contexto_recuperado = estado_final.get("contexto", "")
                
                print(f"   -> Ruta: '{nodo_activo}' (Esperado: '{expected_categoria}')")
                
                # Evaluar con Ragas como Juez usando el LLM dinámico (Llama 3.3 70b)
                if (expected_intencion == "rechazo_amable" and intencion_detectada == "rechazo_amable") or (expected_categoria == "entrevistador" and nodo_activo == "entrevistador"):
                    print("   -> Omitiendo Ragas Juez (Intención/Categoría especial detectada correctamente). Asignando 1.00.")
                    score_f = 1.0
                    score_r = 1.0
                elif expected_intencion == "rechazo_amable" and intencion_detectada != "rechazo_amable":
                    print("   -> Rechazo amable falló en la detección. Asignando 0.00.")
                    score_f = 0.0
                    score_r = 0.0
                elif expected_categoria == "entrevistador" and nodo_activo != "entrevistador":
                    print("   -> Entrevistador falló en el enrutamiento. Asignando 0.00.")
                    score_f = 0.0
                    score_r = 0.0
                else:
                    print("   -> Invocando Ragas Juez (Faithfulness & Answer Relevancy)...")
                    
                    single_df = pd.DataFrame([{
                        "question": q,
                        "answer": respuesta_completa,
                        "contexts": [contexto_recuperado],
                        "ground_truth": gt
                    }])
                    single_dataset = Dataset.from_pandas(single_df)
                    
                    llm_juez = get_eval_llm(model_juez, 0.0)
                    
                    res = evaluate(
                        single_dataset,
                        metrics=[faithfulness, answer_relevancy],
                        llm=llm_juez,
                        embeddings=asistente_rag.embeddings
                    )
                    import math
                    score_f = res.scores[0].get("faithfulness", 0.0)
                    score_r = res.scores[0].get("answer_relevancy", 0.0)
                    
                    if score_f is None or (isinstance(score_f, (int, float)) and math.isnan(score_f)):
                        score_f = 0.0
                    if score_r is None or (isinstance(score_r, (int, float)) and math.isnan(score_r)):
                        score_r = 0.0
                
                print(f"   -> Ragas: Fidelidad = {score_f:.2f} | Relevancia = {score_r:.2f}")
                
                resultado_item = {
                    "question": q,
                    "answer": respuesta_completa,
                    "contexts": [contexto_recuperado],
                    "ground_truth": gt,
                    "latency": latency_sec,
                    "faithfulness": score_f,
                    "answer_relevance": score_r,  # Nombre compatible con generar_reporte.py
                    "expected_intencion": expected_intencion,
                    "intencion_detectada": intencion_detectada,
                    "expected_categoria": expected_categoria,
                    "categoria_detectada": nodo_activo
                }
                
                results.append(resultado_item)
                checkpoint_data["completed_count"] += 1
                checkpoint_data["results"] = results
                guardar_checkpoint(checkpoint_data)
                
                success = True
                idx += 1
                break  # Éxito para esta pregunta, continuar a la siguiente
                
            except Exception as e:
                err_msg = str(e)
                print(f"   ❌ Error al evaluar pregunta: {err_msg}")
                
                # Comprobar si el error se debe a Rate Limit (429) en Groq
                if any(x in err_msg for x in ["429", "rate_limit_exceeded", "Limit reached", "Rate limit", "rate_limit"]):
                    # Fallback multinivel para el agente
                    if "llama-3.3-70b-versatile" in err_msg and asistente_rag.llm.model_name == "llama-3.3-70b-versatile":
                        activar_modelo_fallback("meta-llama/llama-4-scout-17b-16e-instruct")
                        intentos_pregunta += 1
                        continue
                    elif "meta-llama/llama-4-scout-17b-16e-instruct" in err_msg and asistente_rag.llm.model_name == "meta-llama/llama-4-scout-17b-16e-instruct":
                        activar_modelo_fallback("llama-3.1-8b-instant")
                        intentos_pregunta += 1
                        continue
                    
                    # Fallback para el juez de Ragas
                    if "meta-llama/llama-4-scout-17b-16e-instruct" in err_msg and model_juez == "meta-llama/llama-4-scout-17b-16e-instruct":
                        print("\n⚠️  [FALLBACK AUTOMÁTICO JUEZ] Cambiando el juez de Ragas a 'llama-3.1-8b-instant' debido a Rate Limit...")
                        model_juez = "llama-3.1-8b-instant"
                        intentos_pregunta += 1
                        continue
                    
                    if rotar_key_si_es_posible():
                        intentos_pregunta += 1
                        continue
                    else:
                        if solicitar_nueva_key_interactivamente():
                            intentos_pregunta += 1
                            continue
                        else:
                            print("🛑 Deteniendo el script. Se conserva el progreso del checkpoint.")
                            return
                else:
                    # Guardar el fallo para no bloquear toda la prueba
                    print("   ⚠️ Error no crítico. Guardando caso como fallido.")
                    resultado_item = {
                        "question": q,
                        "answer": f"ERROR DE INFERENCIA: {err_msg}",
                        "contexts": [""],
                        "ground_truth": gt,
                        "latency": 0.0,
                        "faithfulness": 0.0,
                        "answer_relevance": 0.0,
                        "expected_intencion": expected_intencion,
                        "intencion_detectada": "error",
                        "expected_categoria": expected_categoria,
                        "categoria_detectada": "error"
                    }
                    results.append(resultado_item)
                    checkpoint_data["completed_count"] += 1
                    checkpoint_data["results"] = results
                    guardar_checkpoint(checkpoint_data)
                    idx += 1
                    break

    # 3. Exportar resultados finales y eliminar el checkpoint al completar con éxito
    guardar_reportes_finales(results)
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("🗑️ Checkpoint temporal eliminado.")

def guardar_reportes_finales(results):
    """Genera las métricas de precisión agregadas y guarda el informe CSV."""
    df_res = pd.DataFrame(results)
    
    # Calcular precisión de enrutamiento
    intencion_correctas = sum(df_res["expected_intencion"] == df_res["intencion_detectada"])
    categoria_correctas = sum(df_res["expected_categoria"] == df_res["categoria_detectada"])
    
    total = len(df_res)
    precision_intencion = (intencion_correctas / total) * 100 if total > 0 else 0
    precision_categoria = (categoria_correctas / total) * 100 if total > 0 else 0
    
    print("\n=============================================")
    print("🏆  RESULTADOS AGREGADOS DE LA EVALUACIÓN  🏆")
    print("=============================================")
    print(f"Total consultas evaluadas: {total}")
    print(f"Precisión en Detección de Intenciones: {precision_intencion:.2f}% ({intencion_correctas}/{total})")
    print(f"Precisión en Clasificación de Categorías: {precision_categoria:.2f}% ({categoria_correctas}/{total})")
    
    if "faithfulness" in df_res.columns:
        print(f"Fidelidad Media (Ragas Faithfulness): {df_res['faithfulness'].mean():.2f}/1.00")
    if "answer_relevance" in df_res.columns:
        print(f"Relevancia Media (Ragas Answer Relevance): {df_res['answer_relevance'].mean():.2f}/1.00")
    if "latency" in df_res.columns:
        print(f"Latencia Media de Respuesta: {df_res['latency'].mean():.2f} segundos")
    print("=============================================")
    
    # Guardar reporte CSV
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"eval_report_{timestamp}.csv"
    df_res.to_csv(output_file, index=False)
    print(f"💾 Reporte CSV final guardado con éxito en: '{output_file}'")
    
    # Intentar ejecutar el generador de reportes visuales HTML si está disponible
    try:
        from generar_reporte import generar_reporte_html
        generar_reporte_html(output_file)
    except Exception as ge:
        print(f"⚠️ No se pudo generar la vista HTML interactiva: {ge}")

if __name__ == "__main__":
    evaluar_sistema_rag()
