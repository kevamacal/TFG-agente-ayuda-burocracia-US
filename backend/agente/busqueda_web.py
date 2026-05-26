from classes.StateSchema import StateSchema
from services.search import buscar_web_us

def busqueda_web(state: StateSchema):
    
    pregunta_reformulada = state.get("pregunta_reformulada") or state.get("pregunta", "")
    
    # Realizar búsqueda web
    resultados = buscar_web_us(pregunta_reformulada, max_results=4)
    
    contextos_web = []
    referencias_web = []
    
    for r in resultados:
        titulo = r["title"]
        body = r["body"]
        href = r["href"]
        contextos_web.append(f"FUENTE WEB (site:us.es): {titulo} ({href})\n{body}")
        referencias_web.append(f"{titulo} (Web US: {href})")
        
    contexto_web_final = "\n\n---\n\n".join(contextos_web)
    
    # Unir con el contexto actual de Pinecone si hubiese algo
    contexto_actual = state.get("contexto", "")
    if contexto_actual and contexto_web_final:
        contexto_combinado = contexto_actual + "\n\n---\n\n" + contexto_web_final
    else:
        contexto_combinado = contexto_web_final or contexto_actual
        
    # Combinar referencias
    referencias_actuales = state.get("referencias") or []
    referencias_combinadas = list(set(referencias_actuales + referencias_web))
    
    return {
        "contexto": contexto_combinado,
        "referencias": referencias_combinadas
    }
