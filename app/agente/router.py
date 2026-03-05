from langgraph.graph import END, StateGraph
from agente.resuelve_consultas import resuelve_consulta
from agente.consulta_usuario import consulta_usuario
from utils.rag_asistente_us import insertar_contexto, contiene_duda_burocratica
from classes.StateSchema import StateSchema

    

graph = StateGraph(state_schema=StateSchema)

def decide_agente(state: StateSchema):
    pregunta = state["pregunta"]
    historial = state["historial"]
    contexto = state["contexto"]
    if (contiene_duda_burocratica(pregunta, historial, contexto)):
        return "entrevistador"
    else:
        return "resultor"

graph.add_node("recuperador", insertar_contexto)
graph.set_entry_point("recuperador")
graph.add_conditional_edges("recuperador", decide_agente)
graph.add_node("entrevistador",consulta_usuario)
graph.add_node("resultor", resuelve_consulta)
graph.add_edge("entrevistador", END)
graph.add_edge("resultor", END)
app = graph.compile()