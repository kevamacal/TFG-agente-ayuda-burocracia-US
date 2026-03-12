from langgraph.graph import END, StateGraph
from app.services.rag import asistente_rag
from classes.StateSchema import StateSchema
from agente.edges import decide_agente, decide_respuesta

# Importamos los nodos (fíjate que ya NO importo resuelve_consulta)
from agente.consulta_usuario import consulta_usuario
from agente.rechazo_amable import rechazo_amable
from agente.resultor_procedimental import resultor_procedimental
from agente.resultor_calendario import resultor_calendario
from agente.resultor_normativo import resultor_normativo
from agente.resultor_baremo import resultor_baremo

graph = StateGraph(state_schema=StateSchema)

# Nodos iniciales y finales
graph.add_node("recuperador", asistente_rag.insertar_contexto)
graph.add_node("entrevistador", consulta_usuario)
graph.add_node("rechazo_amable", rechazo_amable)

graph.add_node("clasificador", lambda state: state) 

graph.add_node("procedimental", resultor_procedimental)
graph.add_node("calendario", resultor_calendario)
graph.add_node("normativo", resultor_normativo)
graph.add_node("baremo", resultor_baremo)

graph.set_entry_point("recuperador")

graph.add_conditional_edges(
    "recuperador", 
    decide_agente,
    {
        "entrevistador": "entrevistador",
        "resultor": "clasificador",
        "rechazo_amable": "rechazo_amable"
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

# Todos los que generan respuesta final van al END
graph.add_edge("entrevistador", END)
graph.add_edge("rechazo_amable", END)
graph.add_edge("procedimental", END)
graph.add_edge("calendario", END)
graph.add_edge("normativo", END)
graph.add_edge("baremo", END)

app = graph.compile()