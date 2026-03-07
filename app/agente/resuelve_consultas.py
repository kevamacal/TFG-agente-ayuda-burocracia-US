from utils.rag import asistente_rag
from classes.StateSchema import StateSchema

def resuelve_consulta(state: StateSchema):
    stream = asistente_rag.responder_consulta(state, "respuesta")["stream"]
    return {"stream": stream}