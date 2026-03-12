from classes.StateSchema import StateSchema
from services.rag import asistente_rag

def rechazo_amable(state: StateSchema):
    contexto = state.get("contexto", "")
    pregunta = state.get("pregunta_reformulada", "")
    historial = state.get("historial_formateado", [])
    
    stream = asistente_rag.responder_consulta(contexto, historial, pregunta,"rechazo")
    return {"stream": stream}