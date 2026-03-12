from langgraph.graph import END, StateGraph, START
from classes.StateSchema import StateSchema
from agente.edges import decide_suficiente_informacion, decide_respuesta, decide_intencion
from agente.consulta_usuario import consulta_usuario
from agente.rechazo_amable import rechazo_amable
from agente.resultor_procedimental import resultor_procedimental
from agente.resultor_calendario import resultor_calendario
from agente.resultor_normativo import resultor_normativo
from agente.resultor_baremo import resultor_baremo
from agente.recuperador import recuperador
from agente.estado_inicial import estado_inicial

graph = StateGraph(state_schema=StateSchema)

graph.add_node("estado_inicial", estado_inicial)
graph.add_node("evalua_intencion", lambda state: state)
graph.add_node("recuperador", recuperador)
graph.add_node("entrevistador", consulta_usuario)
graph.add_node("rechazo_amable", rechazo_amable)
graph.add_node("clasificador", lambda state: state) 
graph.add_node("procedimental", resultor_procedimental)
graph.add_node("calendario", resultor_calendario)
graph.add_node("normativo", resultor_normativo)
graph.add_node("baremo", resultor_baremo)

graph.add_conditional_edges(
    "evalua_intencion",
    decide_intencion,
    {
        "recuperador":"recuperador",
        "rechazo_amable":"rechazo_amable"
    }
)

graph.add_conditional_edges(
    "recuperador", 
    decide_suficiente_informacion,
    {
        "entrevistador": "entrevistador",
        "resultor": "clasificador",
    }
)

graph.add_conditional_edges(
    "clasificador",
    decide_respuesta,
    {
        "procedimental": "procedimental",
        "calendario": "calendario",
        "normativo": "normativo",
        "baremo": "baremo"
    }
)

graph.add_edge(START, "estado_inicial")
graph.add_edge("estado_inicial", "evalua_intencion")
graph.add_edge("entrevistador", END)
graph.add_edge("rechazo_amable", END)
graph.add_edge("procedimental", END)
graph.add_edge("calendario", END)
graph.add_edge("normativo", END)
graph.add_edge("baremo", END)

router = graph.compile()
print(router.get_graph().draw_mermaid(), "\n\n")