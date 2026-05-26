from services.rag import asistente_rag
import logging

logger = logging.getLogger(__name__)

def estado_inicial(state):
    pregunta = state["pregunta"]
    historial = state.get("historial", [])
    
    historial_formateado = "" 
    if historial:
        historial_formateado = "\n".join([
            f"{'Usuario' if msg['role'] == 'user' else 'Asistente'}: {msg['content']}" 
            for msg in historial
        ])
    
    try:
        # Invocar la llamada estructurada consolidada
        analisis = asistente_rag.chain_analisis_inicial.invoke({
            "historial": historial_formateado,
            "question": pregunta
        })
        
        intencion = analisis.intencion
        pregunta_reformulada = analisis.pregunta_reformulada
        categoria = analisis.categoria
    except Exception as e:
        logger.warning(f"Error en análisis estructurado inicial: {e}. Usando valores de fallback.")
        intencion = "recuperador"
        pregunta_reformulada = pregunta
        categoria = "normativo"
        
    return {
        "historial_formateado": historial_formateado,
        "intencion": intencion,
        "pregunta_reformulada": pregunta_reformulada,
        "categoria": categoria
    }