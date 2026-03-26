import json
import time
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import _faithfulness, _answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from backend.templates.templates import *
from backend.utils.config import settings
from backend.services.rag import AsistenteRAG

def get_eval_llm(modelo: str, temperatura: float):
    """
    Crea una instancia de ChatGroq para la evaluación
    usando la API Key ya configurada en tu proyecto.
    """
    return ChatGroq(
        temperature=temperatura, 
        model_name=modelo, 
        api_key=settings.GROQ_API_KEY,
        max_tokens=1024
    )

def ejecutar_evaluacion_agentica():
    print("Cargando dataset_eval.json...")
    with open("dataset_eval.json", "r", encoding="utf-8") as f:
        casos_uso = json.load(f)

    modelos = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
    temperaturas = [0.0, 0.5]
    
    asistente = AsistenteRAG()
    resultados_agente = []
    
    ragas_data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}

    print("\n--- FASE 1: Recuperación de Contextos ---")
    contextos_cacheados = {}
    for caso in casos_uso:
        pregunta = caso["question"]
        print(f"Buscando contexto para: {pregunta}")
        try:
            contexto, _ = asistente._buscar_contexto(pregunta)
            contextos_cacheados[pregunta] = contexto
            time.sleep(1)
        except Exception as e:
            contextos_cacheados[pregunta] = ""
            print(f"Error recuperando contexto para '{pregunta}': {e}")

    print("\n--- FASE 2: Evaluando Decisiones del Agente y Generación ---")
    
    mapa_prompts = {
        "procedimental": PROMPT_RESULTOR_PROCEDIMENTAL,
        "calendario": PROMPT_RESULTOR_CALENDARIO,
        "normativo": PROMPT_RESULTOR_NORMATIVO,
        "baremo": PROMPT_RESULTOR_BAREMO,
        "consulta": PROMPT_CONSULTA_USUARIO,
        "rechazo": PROMPT_RECHAZO_AMABLE
    }

    for modelo in modelos:
        for temp in temperaturas:
            print(f"\nProbando Configuración -> Modelo: {modelo} | Temp: {temp}")
            llm_eval = get_eval_llm(modelo, temp)
            
            asistente.light_llm = llm_eval
            asistente.llm = llm_eval
            
            asistente.chain_deteccion = asistente._crear_cadena(PROMPT_DETECCION, llm_eval)
            asistente.chain_cuestiona_agente = asistente._crear_cadena(PROMPT_CUESTIONA_AGENTE, llm_eval)
            asistente.chain_clasificacion = asistente._crear_cadena(PROMPT_CLASIFICADOR, llm_eval)
            
            for clave in asistente.cadenas_respuesta:
                asistente.cadenas_respuesta[clave] = asistente._crear_cadena(mapa_prompts[clave], llm_eval)

            for caso in casos_uso:
                pregunta = caso["question"]
                contexto = contextos_cacheados[pregunta]
                historial = "" 
                
                print(f"   -> Evaluando: '{pregunta}'")
                
                try:
                    ruta_inicial = asistente.decide_ruta_inicial(pregunta, historial)
                    
                    if ruta_inicial == "rechazo_amable":
                        ruta_final = "rechazo"
                    else: 
                        suficiente_info = asistente.contiene_suficiente_informacion(pregunta, historial, contexto)
                        
                        if suficiente_info == "entrevistador":
                            ruta_final = "consulta"
                        else: 
                            ruta_final_temp = asistente.clasificar_categoria(pregunta, historial, contexto)
                            if ruta_final_temp not in ["procedimental", "calendario", "normativo", "baremo"]:
                                ruta_final = "normativo" 
                            else:
                                ruta_final = ruta_final_temp
                    
                    cadena_activa = asistente.cadenas_respuesta.get(ruta_final, asistente.cadenas_respuesta["normativo"])
                    
                    respuesta = cadena_activa.invoke({
                        "context": contexto, 
                        "historial": historial, 
                        "question": pregunta
                    })
                    
                    ruta_esperada = caso.get("expected_route", "normativo")
                    acierto_ruta = 1 if ruta_final == ruta_esperada else 0
                    
                    resultados_agente.append({
                        "Modelo": modelo,
                        "Temp": temp,
                        "Pregunta": pregunta,
                        "Ruta_Esperada": ruta_esperada,
                        "Ruta_Tomada": ruta_final,
                        "Acierto_Router": acierto_ruta
                    })
                    
                    ragas_data["question"].append(pregunta)
                    ragas_data["answer"].append(respuesta)
                    ragas_data["contexts"].append([contexto] if contexto else [""])
                    ragas_data["ground_truth"].append(caso.get("ground_truth", ""))
                    
                except Exception as e:
                    print(f"      [!] Error evaluando esta pregunta: {e}")
                
                time.sleep(4) 

    print("\n--- FASE 3: Ejecutando RAGAS con Groq ---")
    dataset_ragas = Dataset.from_dict(ragas_data)
    
    llm_juez = get_eval_llm("llama-3.3-70b-versatile", 0.0) 
    
    evaluator_llm = LangchainLLMWrapper(llm_juez)
    evaluator_embeddings = LangchainEmbeddingsWrapper(asistente.embeddings)
    
    resultado_ragas = evaluate(
        dataset_ragas,
        metrics=[_faithfulness, _answer_relevancy],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings
    )
    
    df_ragas = resultado_ragas.to_pandas()
    
    df_final = pd.DataFrame(resultados_agente)
    df_final["Faithfulness"] = df_ragas["faithfulness"]
    df_final["Answer_Relevancy"] = df_ragas["answer_relevancy"]
    
    nombre_archivo = "evaluacion_agentica_ragas.csv"
    df_final.to_csv(nombre_archivo, index=False, encoding="utf-8")
    print(f"\n¡Evaluación completada con éxito! Resultados guardados en {nombre_archivo}")

if __name__ == "__main__":
    ejecutar_evaluacion_agentica()