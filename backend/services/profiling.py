import json
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from utils.config import config_light_llm

def actualizar_perfil_usuario(usuario_id: int, pregunta: str, respuesta: str):
    """Analiza la última interacción en segundo plano y actualiza el perfil del usuario (JSON)"""
    db = SessionLocal()
    try:
        # Obtener el usuario
        usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not usuario:
            return
        
        # Leer perfil actual
        perfil_actual_str = usuario.perfil_metadata or "{}"
        try:
            perfil_actual = json.loads(perfil_actual_str)
        except Exception:
            perfil_actual = {}

        # Configurar prompt para extraer metadatos
        llm = config_light_llm()
        prompt = (
            "Eres un agente inteligente extractor de perfiles. Analiza la siguiente interacción entre un usuario "
            "y un asistente RAG académico. Determina si se puede deducir algún dato del perfil del usuario (ej: titulación, "
            "facultad, rol de usuario -alumno/profesor/personal de administración/externo-, becas de interés, curso académico, etc.) "
            "que nos sirva para personalizar y contextualizar las respuestas en el futuro.\n\n"
            "INSTRUCCIONES:\n"
            "1. Compara con el perfil actual del usuario y añade o actualiza campos relevantes.\n"
            "2. Responde ÚNICAMENTE con el objeto JSON completo resultante fusionado, formateado de manera válida.\n"
            "3. NO incluyes markdown (como ```json), no des explicaciones, ni agregues texto adicional. Solo el JSON plano.\n"
            "4. Si no hay nada nuevo que extraer o no aporta valor al perfil, devuelve exactamente el JSON actual sin cambios.\n\n"
            f"Perfil actual: {json.dumps(perfil_actual, ensure_ascii=False)}\n"
            f"Pregunta del Usuario: '{pregunta}'\n"
            f"Respuesta del Asistente: '{respuesta}'\n"
            "JSON FUSIONADO:"
        )

        # Invocar LLM
        resultado = llm.invoke(prompt).content.strip()
        
        # Limpiar posibles bloques de markdown en la respuesta del LLM
        if resultado.startswith("```"):
            lines = resultado.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            resultado = "\n".join(lines).strip()
            
        # Intentar validar que sea un JSON correcto
        try:
            nuevo_perfil = json.loads(resultado)
            if isinstance(nuevo_perfil, dict):
                # Fusionar con el perfil actual para evitar perder claves no analizadas en este turno
                perfil_actual.update(nuevo_perfil)
                usuario.perfil_metadata = json.dumps(perfil_actual, ensure_ascii=False)
                db.commit()
                print(f"👤 Perfil actualizado para usuario {usuario_id}: {usuario.perfil_metadata}")
        except Exception as parse_err:
            print(f"Error al parsear el JSON de perfil generado: {parse_err}. Respuesta LLM: {resultado}")
            
    except Exception as e:
        print(f"Error en actualizar_perfil_usuario: {e}")
    finally:
        db.close()
