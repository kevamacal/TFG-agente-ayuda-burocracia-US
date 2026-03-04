from langgraph.graph import StateGraph

graph = StateGraph()

def decide_agente(input_data):
    if (contiene_duda_burocratica(input_data)):
        return "entrevistador"
    else:
        return "resultor"

graph.add_conditional_edges("decision", decide_agente)
graph.add_node("entrevistador")
graph.add_node("resultor")