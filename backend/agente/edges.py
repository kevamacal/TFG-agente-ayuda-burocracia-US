from classes.StateSchema import StateSchema
from services.rag import asistente_rag

def decide_ruta_inicial(state: StateSchema) -> str:
    return state.get("intencion", "recuperador")

def decide_suficiente_informacion(state: StateSchema) -> str:
    pregunta_reformulada = state.get("pregunta_reformulada", "")
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    return asistente_rag.contiene_suficiente_informacion(pregunta_reformulada, historial, contexto)
        
def decide_respuesta(state: StateSchema) -> str:
    decision = state.get("categoria", "normativo")
    decision_limpia = decision.strip().lower()
    
    categorias_validas = ["procedimental", "calendario", "normativo", "baremo"]
    if decision_limpia not in categorias_validas:
        decision_limpia = "normativo"
        
    return decision_limpia