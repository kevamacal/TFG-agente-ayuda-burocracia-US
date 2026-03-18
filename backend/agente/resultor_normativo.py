from classes.StateSchema import StateSchema
from services.rag import asistente_rag

def resultor_normativo(state: StateSchema):
    contexto = state.get("contexto", "")
    pregunta = state.get("pregunta_reformulada", "")
    historial = state.get("historial_formateado", [])
    
    stream = asistente_rag.responder_consulta(contexto, historial, pregunta,"normativo")
    return {"stream": stream}