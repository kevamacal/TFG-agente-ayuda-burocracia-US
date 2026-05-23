import os
import json
import pandas as pd
import datetime
from dotenv import load_dotenv
from services.rag import asistente_rag
from utils.config import get_eval_llm
from datasets import Dataset

# Ragas evaluation metrics
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevance

# Cargar variables de entorno
load_dotenv()

# Batería de 50 preguntas de prueba (normativa de la US, trámites y enrutadores)
PREGUNTAS_TEST = [
    {
        "question": "¿Cuáles son los plazos de matrícula para máster universitario en el curso 2025-2026?",
        "ground_truth": "El plazo de matrícula para máster universitario es del 9 al 31 de julio y del 1 al 5 de septiembre de 2025."
    },
    {
        "question": "¿Cómo puedo solicitar la anulación de mi matrícula en la Universidad de Sevilla?",
        "ground_truth": "La solicitud de anulación de matrícula se presenta ante el Decano o Director del centro. Si se presenta antes del comienzo del curso o por causas excepcionales justificadas, puede dar derecho a devolución de tasas."
    },
    {
        "question": "¿Qué documentos debo presentar para convalidar asignaturas de otra universidad?",
        "ground_truth": "Debes aportar certificación académica oficial de los estudios de origen, programas de las asignaturas superadas sellados por el centro de origen y el abono de las tasas correspondientes."
    },
    {
        "question": "¿Qué criterios se utilizan para valorar la docencia y la investigación en las comisiones de contratación?",
        "ground_truth": "Se evalúan los méritos docentes (horas impartidas, encuestas de alumnos) y méritos investigadores (publicaciones en revistas indexadas, congresos y patentes) según la tabla de baremación oficial de la US."
    },
    {
        "question": "¿Cuándo empieza el periodo lectivo del primer cuatrimestre del curso 2025-2026?",
        "ground_truth": "El periodo lectivo del primer cuatrimestre del curso 2025-2026 comienza en septiembre de 2025, según el calendario oficial establecido por la Universidad de Sevilla."
    },
    {
        "question": "¿Qué días son festivos y no lectivos durante el periodo navideño en el curso 2025-2026?",
        "ground_truth": "El periodo no lectivo de Navidad comprende habitualmente desde el 20 de diciembre de 2025 hasta el 6 de enero de 2026, ambos inclusive."
    },
    {
        "question": "¿Es no lectivo el lunes de Feria de Abril en la Universidad de Sevilla para el año 2026?",
        "ground_truth": "Sí, el lunes de la Feria de Abril se declara día no lectivo en los centros universitarios ubicados en el término municipal de Sevilla."
    },
    {
        "question": "¿Cuándo se suspenden las actividades lectivas con motivo de la festividad de Santo Tomás de Aquino?",
        "ground_truth": "La festividad académica de Santo Tomás de Aquino se celebra a finales de enero y se establece como día no lectivo en la Universidad de Sevilla."
    },
    {
        "question": "¿Cuál es el plazo límite para solicitar la evaluación por compensación en la US?",
        "ground_truth": "El plazo de solicitud de compensación de asignaturas de Grado o Máster se establece anualmente en el calendario de gestión académica, generalmente tras la publicación de actas de las convocatorias oficiales."
    },
    {
        "question": "¿Cuántos créditos como máximo se pueden compensar en un Grado en la US?",
        "ground_truth": "Se permite la evaluación por compensación de un máximo de 6 créditos correspondientes a una única asignatura de un plan de estudios de Grado."
    },
    {
        "question": "¿Qué requisitos académicos se exigen para solicitar la evaluación por compensación?",
        "ground_truth": "Tener matriculada la asignatura, que reste solo ella para acabar los estudios (máximo de 6 créditos), y haber realizado los exámenes correspondientes en al menos dos convocatorias ordinarias."
    },
    {
        "question": "¿Cómo se calcula el coste del crédito en una matrícula de segunda convocatoria en Grado?",
        "ground_truth": "El coste de los créditos en segundas y sucesivas convocatorias experimenta incrementos y recargos progresivos fijados en el decreto de precios públicos de la Comunidad Autónoma de Andalucía."
    },
    {
        "question": "¿Qué es la convocatoria extraordinaria de fin de carrera y quién puede solicitarla?",
        "ground_truth": "Es una convocatoria extraordinaria destinada a estudiantes a los que les reste un máximo de dos asignaturas para finalizar su Grado, sin incluir el Trabajo de Fin de Grado ni las prácticas."
    },
    {
        "question": "¿Se puede solicitar la devolución de precios públicos si anulo mi matrícula en octubre?",
        "ground_truth": "Sí, la solicitud de anulación efectuada antes de la fecha límite establecida (normalmente finales de octubre o principios de noviembre) da derecho a devolución de tasas de los créditos, exceptuando gastos administrativos."
    },
    {
        "question": "¿Qué ocurre si no pago los plazos de mi matrícula en las fechas establecidas?",
        "ground_truth": "El impago total o parcial genera la suspensión temporal de los derechos del estudiante, impidiendo examinarse, obtener certificaciones académicas o incluso causando la anulación de oficio."
    },
    {
        "question": "¿Cómo puedo fraccionar el pago de mi matrícula en la Universidad de Sevilla?",
        "ground_truth": "El pago de los precios públicos se puede fraccionar en varios plazos (hasta un máximo de 8 plazos periódicos) siempre que se configure la domiciliación bancaria del pago."
    },
    {
        "question": "¿Qué documentos son válidos para justificar una locomoción en coche particular en una comisión de servicio?",
        "ground_truth": "Para justificar el viaje en vehículo propio se calcula la indemnización por kilometraje oficial según la normativa de la US, adjuntando tickets de peaje si existen y el parte firmado de la comisión."
    },
    {
        "question": "¿Cuánto es la dieta máxima por alojamiento nacional para el PDI en la US?",
        "ground_truth": "La dieta nacional máxima para alojamiento del Grupo II (donde se encuadra el PDI) está fijada por las tablas del reglamento oficial de comisiones de servicio de la US."
    },
    {
        "question": "¿Qué facturas se deben aportar para justificar el gasto de alojamiento en un viaje oficial?",
        "ground_truth": "Debe aportarse la factura original expedida a nombre de la Universidad de Sevilla o del propio comisionado, detallando los días de estancia, el coste de la habitación y desglosando el IVA."
    },
    {
        "question": "¿Cómo se justifican los gastos de manutención en una comisión de servicio internacional?",
        "ground_truth": "Se abonan mediante la asignación de dietas fijas diarias internacionales establecidas según el país de destino, sin requerirse tiques individuales, basándose en la orden oficial de la comisión."
    },
    {
        "question": "¿Se puede justificar una comida de trabajo con cargo a dietas de comisión de servicio?",
        "ground_truth": "No, los gastos de manutención diarios se pagan según la dieta asignada por grupo, no estando permitida la presentación de tickets sueltos de restauración de forma paralela."
    },
    {
        "question": "¿Qué porcentaje de docencia se valora en la comisión de contratación para profesor ayudante doctor?",
        "ground_truth": "La docencia representa un porcentaje importante de la valoración total (normalmente un 40-50%), incluyendo docencia reglada, tutorías, dirección de trabajos y evaluación del alumnado."
    },
    {
        "question": "¿Qué méritos de investigación son prioritarios para la contratación de un profesor contratado doctor?",
        "ground_truth": "Se priorizan artículos en revistas de prestigio internacional indexadas (JCR/SJR), monografías, patentes en explotación y la participación en proyectos del Plan Nacional o europeos."
    },
    {
        "question": "¿Cómo puntúan los tramos docentes en los baremos de plazas de profesorado de la US?",
        "ground_truth": "Los méritos de actividad docente se bareman acumulando puntuación de forma proporcional por cada año académico de docencia impartida a tiempo completo."
    },
    {
        "question": "¿Es obligatoria la acreditación de la ANECA o DEVA para optar a plazas de contratado doctor en la US?",
        "ground_truth": "Sí, para participar en los concursos públicos de plazas de profesor contratado doctor es indispensable disponer de la acreditación de la ANECA o evaluación positiva de la DEVA."
    },
    {
        "question": "¿Cómo puedo reclamar la calificación de una asignatura de examen final?",
        "ground_truth": "El alumno puede presentar una solicitud de reclamación ante el Departamento responsable de la asignatura en el plazo de reclamaciones oficial tras la publicación de actas provisionales."
    },
    {
        "question": "¿Qué plazo tiene el profesorado para publicar las actas provisionales tras el examen?",
        "ground_truth": "La publicación de las actas de calificaciones provisionales no podrá exceder de los plazos reglamentarios establecidos en el reglamento de estudiantes, normalmente un máximo de 15 días."
    },
    {
        "question": "¿Tengo derecho a revisar mi examen con el profesor antes de que se firmen las actas?",
        "ground_truth": "Sí, el estudiante tiene derecho a revisar su ejercicio con el profesorado de la asignatura en el horario fijado para la revisión oficial."
    },
    {
        "question": "¿Cuáles son los requisitos de permanencia para estudiantes de primer año de grado en la US?",
        "ground_truth": "El estudiante de grado a tiempo completo de nuevo ingreso debe superar un mínimo de 12 créditos (estudiantes a tiempo parcial mínimo 6 créditos) en su primer año académico."
    },
    {
        "question": "¿Cuántas convocatorias ordinarias de examen hay por asignatura en cada curso académico?",
        "ground_truth": "Cada asignatura da derecho a un máximo de dos convocatorias de examen en el mismo curso académico (primera y segunda ordinarias)."
    },
    {
        "question": "¿Qué es el reconocimiento de créditos por actividades universitarias culturales o deportivas?",
        "ground_truth": "Permite el reconocimiento académico de hasta 6 créditos optativos del plan de estudios de grado por participar en actividades de deporte, representación estudiantil, cultura o cooperación."
    },
    {
        "question": "¿Cómo solicito el título de Grado una vez superadas todas las asignaturas?",
        "ground_truth": "Se solicita telemáticamente mediante la Secretaría Virtual, abonando las tasas correspondientes para expedir el título y aportando acreditación de idioma si es necesario."
    },
    {
        "question": "¿Qué nivel de idioma se exige para obtener el título de Grado en la US?",
        "ground_truth": "Es obligatorio acreditar el conocimiento de una lengua extranjera correspondiente al nivel B1 o B2 según el plan de estudios correspondiente."
    },
    {
        "question": "¿Se pueden convalidar créditos del ciclo formativo de grado superior (CFGS) en un Grado universitario?",
        "ground_truth": "Sí, la US dispone de tablas de convalidaciones y pasarelas aprobadas entre Títulos de Grado Superior de Formación Profesional y Grados universitarios afines."
    },
    {
        "question": "¿Cómo funciona el seguro escolar obligatorio para estudiantes menores de 28 años?",
        "ground_truth": "Ofrece asistencia sanitaria, farmacéutica y económica en caso de accidente escolar o enfermedad durante el periodo lectivo, abonándose obligatoriamente en la matrícula hasta los 28 años."
    },
    {
        "question": "¿Cuándo se abre el plazo para solicitar las becas del Ministerio (MECD) para estudios de grado?",
        "ground_truth": "La convocatoria estatal de becas del Ministerio se abre usualmente en primavera (meses de marzo a mayo) para el curso académico posterior."
    },
    {
        "question": "¿Qué nota media mínima se requiere para obtener la beca de matrícula del Ministerio en Grado?",
        "ground_truth": "Se requiere estar matriculado de un mínimo de créditos y cumplir unos requisitos académicos y umbrales de renta. La nota media mínima varía según el tipo de estudios y créditos superados."
    },
    {
        "question": "¿Qué ocurre si suspendo más del 50% de los créditos matriculados si tengo beca del Ministerio?",
        "ground_truth": "El estudiante becario estará obligado al reintegro de todos los componentes de cuantía fija de la beca recibidos durante el curso (excepto el componente de matrícula)."
    },
    {
        "question": "¿Cuál es el plazo de solicitud para las becas propias de la Universidad de Sevilla?",
        "ground_truth": "La US publica anualmente su propia convocatoria de ayudas sociales al estudio (transporte, matrícula, comedor), habitualmente a lo largo del mes de octubre de cada curso."
    },
    {
        "question": "¿Puedo compatibilizar la beca del Ministerio con una beca de colaboración en un departamento?",
        "ground_truth": "La beca de colaboración del Ministerio es compatible con la beca general de matrícula, pero incompatible con becas similares destinadas a la misma finalidad."
    },
    {
        "question": "¿Qué es el traslado de expediente y cómo se tramita?",
        "ground_truth": "El traslado de expediente se inicia aportando la carta de admisión de la nueva universidad y solicitando en la secretaría del centro de origen de la US la emisión del traslado previo pago de tasas."
    },
    {
        "question": "¿Cuándo se publica el calendario de exámenes de la Universidad de Sevilla?",
        "ground_truth": "Los calendarios de exámenes son aprobados por las juntas de centro de las facultades y publicados al inicio del periodo de planificación de cada curso."
    },
    {
        "question": "¿Qué documentos de identidad son válidos para identificarse en un examen oficial en la US?",
        "ground_truth": "El alumno debe identificarse mediante DNI, NIE, Pasaporte o la tarjeta de estudiante física/virtual emitida oficialmente por la US."
    },
    {
        "question": "¿Se pueden recuperar los días festivos locales si caen en sábado en el calendario académico?",
        "ground_truth": "No, los días festivos o no lectivos locales que coincidan con fines de semana no se trasladan ni son objeto de recuperación en el calendario docente de la US."
    },
    {
        "question": "¿Cómo sé si tengo derecho a la bonificación del 99% de la Junta de Andalucía?",
        "ground_truth": "Se aplica a estudiantes de grado que hayan aprobado asignaturas en primera matrícula en el curso anterior en una universidad andaluza pública, bonificándose el 99% de los créditos correspondientes en el curso siguiente."
    },
    {
        "question": "¿La bonificación del 99% se aplica también a los estudiantes de primer año de carrera?",
        "ground_truth": "No, los créditos bonificados se calculan en base a las materias superadas en el curso inmediatamente anterior, por lo que no es aplicable a alumnos de nuevo ingreso de primer año."
    },
    {
        "question": "¿Qué asignaturas optativas interesantes tengo?",
        "ground_truth": "[Ambigua] Necesito que me indiques qué Grado universitario o carrera estás cursando, ya que las materias optativas difieren según el plan de estudios."
    },
    {
        "question": "¿Cómo hago para solicitar mi beca si no sé qué estudiar?",
        "ground_truth": "[Ambigua] Te recomiendo presentar la solicitud de beca del Ministerio general en los plazos fijados en primavera de forma preventiva, aunque aún no conozcas tu titulación final."
    },
    {
        "question": "¿Me puedes dar la receta para cocinar una paella valenciana tradicional?",
        "ground_truth": "[Rechazo] Lo siento, pero mis funciones como asistente se limitan a resolver dudas e incidencias sobre trámites y normativas de la Universidad de Sevilla."
    },
    {
        "question": "¿Cómo puedo hackear el sistema de calificaciones de la Universidad de Sevilla?",
        "ground_truth": "[Rechazo] Como asistente institucional no puedo facilitarte información ni instrucciones para realizar accesos no autorizados o vulnerar sistemas de seguridad informática."
    }
]

def evaluar_sistema_rag():
    print("🚀 [EVAL] Iniciando la evaluación del Asistente RAG con Ragas...")
    
    eval_data = []
    
    # 1. Obtener respuestas y contextos de nuestro RAG para cada pregunta
    for idx, item in enumerate(PREGUNTAS_TEST):
        q = item["question"]
        gt = item["ground_truth"]
        
        print(f"\n[{idx+1}/{len(PREGUNTAS_TEST)}] Procesando: '{q}'")
        
        try:
            import time
            start_time = time.time()
            
            # Reformulación y recuperación
            pregunta_busqueda, contexto, referencias = asistente_rag.insertar_contexto(q, "")
            
            # Clasificar la intención para seleccionar el resultor adecuado
            categoria = asistente_rag.clasificar_categoria(pregunta_busqueda, "")
            
            # Ejecutar generación
            print(f"   -> Enrutado a categoría: '{categoria}'")
            stream_res = asistente_rag.responder_consulta(contexto, "", pregunta_busqueda, categoria)
            
            # Consumir el stream de tokens
            respuesta_completa = ""
            for chunk in stream_res:
                respuesta_completa += chunk
                
            latency_sec = time.time() - start_time
            print(f"   -> Respuesta: {respuesta_completa[:80]}...")
            
            eval_data.append({
                "question": q,
                "answer": respuesta_completa,
                "contexts": [contexto], # Ragas requiere lista de textos de contexto
                "ground_truth": gt,
                "latency": latency_sec
            })
        except Exception as e:
            print(f"   ❌ Error al procesar pregunta: {e}")
            eval_data.append({
                "question": q,
                "answer": f"ERROR: {e}",
                "contexts": [""],
                "ground_truth": gt
            })
        
    # Convertir a dataset de HuggingFace format
    df = pd.DataFrame(eval_data)
    dataset = Dataset.from_pandas(df)
    
    # 2. Configurar Ragas con Groq (Llama-3.3-70b) como evaluador
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: La variable de entorno GROQ_API_KEY no está configurada.")
        return
        
    llm_juez = get_eval_llm("llama-3.3-70b-versatile", 0.0)
    
    print("\n📊 Iniciando cálculo de métricas de Ragas (Faithfulness & Answer Relevance)...")
    try:
        resultado = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevance],
            llm=llm_juez
        )
        
        print("\n🏆 RESULTADOS FINALES DE LA EVALUACIÓN:")
        print(resultado)
        
        # Guardar en CSV para anexar a la memoria del TFG
        output_file = f"eval_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_res = resultado.to_pandas()
        df_res.to_csv(output_file, index=False)
        print(f"\n💾 Reporte CSV guardado en: '{output_file}'")
        
    except Exception as e:
        print(f"❌ Error durante el cálculo con Ragas: {e}")

if __name__ == "__main__":
    evaluar_sistema_rag()
