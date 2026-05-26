from classes.StateSchema import StateSchema
from services.rag import asistente_rag

def recuperador(state: StateSchema):
    pregunta = state["pregunta"]
    historial = state.get("historial_formateado", [])
    pregunta_reformulada_previa = state.get("pregunta_reformulada")
    
    pregunta_busqueda, contexto, referencias = asistente_rag.insertar_contexto(
        pregunta, 
        historial, 
        pregunta_reformulada_previa=pregunta_reformulada_previa
    )
    
    return {
        "pregunta_reformulada": pregunta_busqueda,
        "contexto": contexto,
        "referencias": referencias,
        "historial_formateado": historial
    }