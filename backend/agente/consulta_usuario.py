from classes.StateSchema import StateSchema
from services.rag import asistente_rag
from services.search import buscar_web_us, procesar_resultados_busqueda
import logging

logger = logging.getLogger(__name__)

def consulta_usuario(state: StateSchema):
    contexto = state.get("contexto", "")
    pregunta = state.get("pregunta_reformulada") or state.get("pregunta", "")
    historial = state.get("historial_formateado", [])
    referencias = state.get("referencias") or []
    
    # Realizar una búsqueda web complementaria de site:us.es para enriquecer el contexto del tema ambiguo
    try:
        resultados = buscar_web_us(pregunta, max_results=3)
        contexto, referencias = procesar_resultados_busqueda(
            resultados,
            contexto_previo=contexto,
            referencias_previas=referencias
        )
    except Exception as e:
        logger.exception(f"Error al realizar la búsqueda web complementaria en entrevistador: {e}")
        
    stream = asistente_rag.responder_consulta(contexto, historial, pregunta, "consulta")
    
    return {
        "stream": stream,
        "contexto": contexto,
        "referencias": referencias,
        "categoria": "entrevistador"
    }