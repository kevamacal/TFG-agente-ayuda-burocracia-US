import datetime
from classes.StateSchema import StateSchema
from services.rag import asistente_rag

def recuperador(state: StateSchema):
    print("\n--- NODO: RECUPERANDO CONTEXTO ---", datetime.datetime.now())
    
    pregunta = state["pregunta"]
    historial = state.get("historial_formateado", [])
    
    pregunta_busqueda, contexto, referencias = asistente_rag.insertar_contexto(pregunta, historial)
    
    return {
        "pregunta_reformulada": pregunta_busqueda,
        "contexto": contexto,
        "referencias": referencias,
        "historial_formateado": historial
    }