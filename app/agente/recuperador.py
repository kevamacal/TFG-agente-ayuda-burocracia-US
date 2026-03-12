import datetime
from classes.StateSchema import StateSchema
from services.rag import AsistenteRAG

# Instanciamos nuestro servicio "puro" de IA
rag = AsistenteRAG()

def recuperador(state: StateSchema):
    print("\n--- NODO: RECUPERANDO CONTEXTO ---", datetime.datetime.now())
    
    pregunta = state["pregunta"]
    historial = state.get("historial_formateado", [])
    
    pregunta_busqueda, contexto, referencias = rag.procesar_y_buscar_contexto(pregunta, historial)
    
    return {
        "pregunta_reformulada": pregunta_busqueda,
        "contexto": contexto,
        "referencias": referencias,
        "historial_formateado": historial
    }