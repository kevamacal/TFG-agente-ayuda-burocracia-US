import datetime
from classes.StateSchema import StateSchema
from services.rag import AsistenteRAG

rag = AsistenteRAG()

def decide_intencion(state: StateSchema) -> str:
    print("\n--- EDGE: DECIDIENDO INTENCIÓN ---", datetime.datetime.now())
    
    pregunta = state.get("pregunta", "")
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    
    decision = rag.contiene_duda_burocratica(pregunta, historial, contexto)
    
    return decision

def decide_suficiente_informacion(state: StateSchema) -> str:
    print("\n--- EDGE: DECIDIENDO SIGUIENTE PASO ---", datetime.datetime.now())
    
    pregunta_reformulada = state.get("pregunta_reformulada", "")
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    
    decision = rag.contiene_suficiente_informacion(pregunta_reformulada, historial, contexto)
    
    print(f"Decisión tomada: ir a nodo '{decision}'", datetime.datetime.now())
    
    return decision
        
def decide_respuesta(state: StateSchema) -> str:
    print("\n--- EDGE: DECIDIENDO TIPO DE RESPUESTA ---", datetime.datetime.now())
    
    pregunta_reformulada = state.get("pregunta_reformulada", state.get("pregunta", ""))
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    
    decision = rag.clasificar_categoria(pregunta_reformulada, historial,contexto)
    
    decision_limpia = decision.strip().lower()
    
    categorias_validas = ["procedimental", "calendario", "normativo", "baremo"]
    if decision_limpia not in categorias_validas:
        decision_limpia = "normativo"
    
    print(f"Pregunta clasificada como: '{decision_limpia}'", datetime.datetime.now())
    
    return decision_limpia