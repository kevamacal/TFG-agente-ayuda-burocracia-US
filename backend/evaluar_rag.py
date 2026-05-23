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

# Batería de preguntas de prueba (normativa de la US y trámites)
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
        
        # Reformulación y recuperación
        pregunta_busqueda, contexto, referencias = asistente_rag.insertar_contexto(q, "")
        
        # Clasificar la intención para seleccionar el resultor adecuado
        categoria = asistente_rag.clasificar_categoria(pregunta_busqueda, "")
        
        # Ejecutar generación
        print(f"   -> Ejecutando nodo resultor tipo: '{categoria}'")
        stream_res = asistente_rag.responder_consulta(contexto, "", pregunta_busqueda, categoria)
        
        # Consumir el stream de tokens y unir
        respuesta_completa = ""
        for chunk in stream_res:
            respuesta_completa += chunk
            
        print(f"   -> Respuesta: {respuesta_completa[:80]}...")
        
        eval_data.append({
            "question": q,
            "answer": respuesta_completa,
            "contexts": [contexto], # Ragas requiere lista de textos de contexto
            "ground_truth": gt
        })
        
    # Convertir a dataset de HuggingFace format
    df = pd.DataFrame(eval_data)
    dataset = Dataset.from_pandas(df)
    
    # 2. Configurar Ragas con Groq (Llama-3.3-70b) como evaluador
    # Groq requiere su API key en la variable GROQ_API_KEY
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
