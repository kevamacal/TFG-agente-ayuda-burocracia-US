import datetime
from classes.StateSchema import StateSchema
from services.rag import AsistenteRAG

rag = AsistenteRAG()

def decide_ruta_inicial(state: StateSchema) -> str:
    t0 = datetime.datetime.now()
    print(f"\n--- EDGE: DECIDIENDO INTENCION --- {t0}")
    
    pregunta = state.get("pregunta", "")
    historial = state.get("historial_formateado", [])
    
    decision = rag.decide_ruta_inicial(pregunta, historial)
    
    t1 = datetime.datetime.now()
    print(f"  [TIMING] Deteccion intencion: {(t1-t0).total_seconds():.2f}s -> '{decision}'")
    
    return decision

def decide_suficiente_informacion(state: StateSchema) -> str:
    t0 = datetime.datetime.now()
    print(f"\n--- EDGE: DECIDIENDO SIGUIENTE PASO --- {t0}")
    
    pregunta_reformulada = state.get("pregunta_reformulada", "")
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    
    decision = rag.contiene_suficiente_informacion(pregunta_reformulada, historial, contexto)
    
    t1 = datetime.datetime.now()
    print(f"  [TIMING] Suficiente info: {(t1-t0).total_seconds():.2f}s -> '{decision}'")
    
    return decision
        
def decide_respuesta(state: StateSchema) -> str:
    t0 = datetime.datetime.now()
    print(f"\n--- EDGE: DECIDIENDO TIPO DE RESPUESTA --- {t0}")
    
    pregunta_reformulada = state.get("pregunta_reformulada", state.get("pregunta", ""))
    historial = state.get("historial_formateado", [])
    contexto = state.get("contexto", "")
    
    decision = rag.clasificar_categoria(pregunta_reformulada, historial)
    
    decision_limpia = decision.strip().lower()
    
    categorias_validas = ["procedimental", "calendario", "normativo", "baremo"]
    if decision_limpia not in categorias_validas:
        decision_limpia = "normativo"
    
    t1 = datetime.datetime.now()
    print(f"  [TIMING] Clasificacion: {(t1-t0).total_seconds():.2f}s -> '{decision_limpia}'")
    
    return decision_limpia