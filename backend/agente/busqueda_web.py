from classes.StateSchema import StateSchema
from services.search import buscar_web_us, procesar_resultados_busqueda

def busqueda_web(state: StateSchema):
    pregunta_reformulada = state.get("pregunta_reformulada") or state.get("pregunta", "")
    
    # Realizar búsqueda web
    resultados = buscar_web_us(pregunta_reformulada, max_results=4)
    
    contexto_actual = state.get("contexto", "")
    referencias_actuales = state.get("referencias") or []
    
    contexto_combinado, referencias_combinadas = procesar_resultados_busqueda(
        resultados,
        contexto_previo=contexto_actual,
        referencias_previas=referencias_actuales
    )
    
    return {
        "contexto": contexto_combinado,
        "referencias": referencias_combinadas
    }
