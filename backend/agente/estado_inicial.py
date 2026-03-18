def estado_inicial(state):
    historial = state.get("historial", [])
    
    historial_formateado = "" 
    
    if historial:
        historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial])
    
    return {
        "historial_formateado": historial_formateado,
    }