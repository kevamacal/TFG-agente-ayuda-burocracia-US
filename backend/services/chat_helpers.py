from database import get_db, SessionLocal
import models
from utils.config import config_light_llm

def actualizar_resumen_memoria(conversacion_id: int):
    """Actualiza el resumen de memoria para proteger la ventana de contexto de Groq"""
    db = next(get_db())
    try:
        conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id).first()
        if not conv: return
        
        historial = db.query(models.Mensaje).filter(models.Mensaje.conversacion_id == conv.id).order_by(models.Mensaje.fecha_creacion).all()
        if len(historial) <= 5: return
        
        mensajes_viejos = historial[:-4] # Excluimos los 4 últimos para que no se duplique la info en contexto
        texto = "\n".join([f"{'Usuario' if m.rol == 'user' else 'Asistente'}: {m.contenido}" for m in mensajes_viejos])
        
        llm = config_light_llm()
        prompt = (
            "Resume MUY brevemente la siguiente conversación (el inicio de una conversación larga). "
            "Conserva solo los metadatos relevantes (si el usuario es de grado o máster, si va sobre becas, "
            "alguna fecha específica nombrada o problema principal cerrado) para que el asistente siga recordando "
            "de qué va sin tener todo el texto literal. NO inventes nada.\n"
            f"HISTORIAL ANTIGUO:\n{texto}"
        )
        
        res = llm.invoke(prompt)
        conv.resumen_memoria = res.content.strip()
        db.commit()
        print(f"🧠 Memoria comprimida para conversacion {conversacion_id}.")
    except Exception as e:
        print(f"Error comprimiendo memoria: {e}")
    finally:
        db.close()

def generar_y_guardar_titulo(conversacion_id: int, mensaje_usuario: str):
    """Genera un título corto usando Groq y lo guarda en la base de datos."""
    db = next(get_db()) 
    
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
        
        conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id).first()
        if conv:
            conv.titulo = nuevo_titulo
            db.commit()
            print(f"✅ Título generado para conv {conversacion_id}: {nuevo_titulo}")
            
    except Exception as e:
        print(f"Error al generar el título en segundo plano: {e}")
    finally:
        db.close()
