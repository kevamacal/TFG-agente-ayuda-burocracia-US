from database import get_db, SessionLocal
import models
import crud
from utils.config import config_light_llm
import logging

logger = logging.getLogger(__name__)

def actualizar_resumen_memoria(conversacion_id: int):
    """Actualiza el resumen de memoria de forma incremental para proteger la ventana de contexto de Groq"""
    db = SessionLocal()
    try:
        conv = crud.get_conversacion_por_id(db, conversacion_id)
        if not conv: return
        
        historial = crud.get_mensajes_conversacion(db, conv.id)
        if len(historial) <= 5: return
        
        resumen_previo = conv.resumen_memoria
        llm = config_light_llm()
        
        if resumen_previo:
            # Si ya hay un resumen, solo procesamos las intervenciones intermedias que acaban de salir del contexto reciente
            # (mensajes que están antes de los últimos 5, pero limitados a un máximo de 5 mensajes nuevos para evitar sobrepasar límites)
            mensajes_viejos = historial[-10:-5] if len(historial) > 10 else historial[:-5]
            texto_nuevas = "\n".join([f"{'Usuario' if m.rol == 'user' else 'Asistente'}: {m.contenido}" for m in mensajes_viejos])
            
            prompt = (
                "Actualiza el resumen previo de la conversación incorporando de forma muy breve los puntos clave de las nuevas intervenciones.\n"
                "Conserva el resumen extremadamente condensado y al grano (trámites de interés, titulación o problemas resueltos).\n"
                "NO inventes nada y devuelve solo el nuevo resumen.\n\n"
                f"RESUMEN PREVIO:\n{resumen_previo}\n\n"
                f"NUEVAS INTERVENCIONES:\n{texto_nuevas}"
            )
        else:
            # Primera compresión de la conversación
            mensajes_viejos = historial[:-5]
            texto = "\n".join([f"{'Usuario' if m.rol == 'user' else 'Asistente'}: {m.contenido}" for m in mensajes_viejos])
            prompt = (
                "Resume MUY brevemente la siguiente conversación (el inicio de una conversación larga). "
                "Conserva solo los metadatos relevantes (si el usuario es de grado o máster, si va sobre becas, "
                "alguna fecha específica nombrada o problema principal cerrado) para que el asistente siga recordando "
                "de qué va sin tener todo el texto literal. NO inventes nada.\n\n"
                f"HISTORIAL ANTIGUO:\n{texto}"
            )
        
        res = llm.invoke(prompt)
        crud.actualizar_resumen_memoria_conversacion(db, conv, res.content.strip())
        logger.info(f"Memoria comprimida para conversacion {conversacion_id}.")
    except Exception as e:
        logger.exception(f"Error comprimiendo memoria: {e}")
    finally:
        db.close()

def generar_y_guardar_titulo(conversacion_id: int, mensaje_usuario: str):
    """Genera un título corto usando Groq y lo guarda en la base de datos."""
    db = SessionLocal() 
    
    try:
        llm = config_light_llm()
        
        prompt = (
            "Eres un generador de títulos automáticos. "
            "Resume el siguiente mensaje en un título de máximo 4 a 5 palabras. "
            "Devuelve ÚNICAMENTE el texto del título, sin comillas, sin puntos finales "
            "y sin introducciones. "
            f"Mensaje: '{mensaje_usuario}'"
        )
        
        respuesta = llm.invoke(prompt)
        nuevo_titulo = respuesta.content.strip().replace('"', '').replace("'", "")
        
        conv = crud.get_conversacion_por_id(db, conversacion_id)
        if conv:
            crud.actualizar_titulo_conversacion(db, conv, nuevo_titulo)
            logger.info(f"Título generado para conv {conversacion_id}: {nuevo_titulo}")
            
    except Exception as e:
        logger.exception(f"Error al generar el título en segundo plano: {e}")
    finally:
        db.close()

def formatear_historial(historial: list) -> str:
    """Convierte el historial de mensajes (lista de diccionarios) en un string estructurado,
    formateando correctamente los mensajes del sistema, usuario y asistente."""
    if not historial:
        return ""
    
    lineas = []
    for msg in historial:
        role = msg.get("role")
        content = msg.get("content", "")
        if not content:
            continue
        
        if role == "user":
            lineas.append(f"Usuario: {content}")
        elif role == "assistant":
            lineas.append(f"Asistente: {content}")
        elif role == "system":
            lineas.append(f"[Información del Sistema]: {content}")
        else:
            lineas.append(f"{role.capitalize() if role else 'Mensaje'}: {content}")
            
    return "\n".join(lineas)
