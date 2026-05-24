import datetime
from classes.StateSchema import StateSchema
from services.rag import asistente_rag
from services.search import buscar_web_us

def consulta_usuario(state: StateSchema):
    print("\n--- NODO: ENTREVISTADOR (RESOLUCIÓN DE AMBIGÜEDADES CON BÚSQUEDA WEB) ---", datetime.datetime.now())
    
    contexto = state.get("contexto", "")
    pregunta = state.get("pregunta_reformulada") or state.get("pregunta", "")
    historial = state.get("historial_formateado", [])
    referencias = state.get("referencias") or []
    
    # Realizar una búsqueda web complementaria de site:us.es para enriquecer el contexto del tema ambiguo
    try:
        print("🔍 [ENTREVISTADOR] Enriqueciendo contexto ambiguo mediante búsqueda web complementaria...")
        resultados = buscar_web_us(pregunta, max_results=3)
        contextos_web = []
        referencias_web = []
        
        for r in resultados:
            titulo = r["title"]
            body = r["body"]
            href = r["href"]
            contextos_web.append(f"FUENTE WEB (site:us.es): {titulo} ({href})\n{body}")
            referencias_web.append(f"{titulo} (Web US: {href})")
            
        if contextos_web:
            contexto_web_final = "\n\n---\n\n".join(contextos_web)
            if contexto:
                contexto = contexto + "\n\n---\n\n" + contexto_web_final
            else:
                contexto = contexto_web_final
            referencias = list(set(referencias + referencias_web))
            print(f"✅ [ENTREVISTADOR] Búsqueda web exitosa. Añadidas {len(referencias_web)} fuentes.")
    except Exception as e:
        print(f"⚠️ [ENTREVISTADOR] Error al realizar la búsqueda web complementaria: {e}")
        
    stream = asistente_rag.responder_consulta(contexto, historial, pregunta, "consulta")
    
    return {
        "stream": stream,
        "contexto": contexto,
        "referencias": referencias
    }