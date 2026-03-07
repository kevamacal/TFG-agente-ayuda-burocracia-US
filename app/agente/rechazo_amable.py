from classes.StateSchema import StateSchema
from utils.rag import asistente_rag

def rechazo_amable(state: StateSchema):
    stream = asistente_rag.responder_consulta(state, "rechazo")["stream"]
    return {"stream": stream}