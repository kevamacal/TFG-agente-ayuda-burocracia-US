from classes.StateSchema import StateSchema
from utils.rag import asistente_rag

def consulta_usuario(state: StateSchema):
    stream = asistente_rag.responder_consulta(state, "consulta")["stream"]
    return {"stream": stream}