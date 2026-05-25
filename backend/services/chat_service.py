from typing import AsyncGenerator
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal
from services.chat_helpers import generar_y_guardar_titulo, actualizar_resumen_memoria
from services.profiling import actualizar_perfil_usuario
from agente.router import router as agente_router
import models, crud
import json
import asyncio
import os

def preparar_historial(db: Session, conv: models.Conversacion, usuario: models.Usuario) -> list:
    """Prepara el historial de mensajes de la conversación y fusiona el perfil y memoria"""
    historial_db = db.query(models.Mensaje).filter(models.Mensaje.conversacion_id == conv.id).order_by(models.Mensaje.fecha_creacion).all()
    mensajes_recientes = historial_db[-5:] if len(historial_db) > 5 else historial_db
    
    historial_langgraph = []
    
    # Inyectar perfil del usuario como mensaje de sistema inicial si existe
    perfil_str = usuario.perfil_metadata or "{}"
    try:
        perfil_metadata = json.loads(perfil_str)
        if perfil_metadata:
            perfil_formateado = "\n".join([f"- {k}: {v}" for k, v in perfil_metadata.items()])
            historial_langgraph.append({
                "role": "system", 
                "content": f"INFORMACIÓN DEL USUARIO CONECTADO (Úsala para contextualizar tus respuestas si es relevante. Asume estos datos como ciertos sobre el usuario):\n{perfil_formateado}"
            })
    except Exception as e:
        print(f"Error al decodificar perfil_metadata: {e}")

    if conv.resumen_memoria and len(historial_db) > 5:
        historial_langgraph.append({"role": "system", "content": f"Resumen de conversación antigua: {conv.resumen_memoria}"})
        
    historial_langgraph.extend([{"role": m.rol, "content": m.contenido} for m in mensajes_recientes])
    return historial_langgraph

async def sse_chat_generator(
    conv_id: int,
    usuario_id: int,
    pregunta: str,
    historial: list,
    background_tasks: BackgroundTasks
) -> AsyncGenerator[str, None]:
    """Ejecuta el stream del agente Langgraph y emite eventos SSE"""
    estado_inicial = {
        "pregunta": pregunta, 
        "historial": historial, 
        "contexto": "", 
        "stream": None,
        "referencias": []
    }
    
    try:
        # Configurar observabilidad de Langfuse si las credenciales están presentes
        config = {}
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            try:
                from services.rag import asistente_rag
                config["callbacks"] = asistente_rag.callbacks
                config["run_name"] = f"Chat RAG Asistente US - Conv {conv_id}"
            except Exception as lf_err:
                print(f"Error al configurar Langfuse callback: {lf_err}")

        # Ejecutar el agente en pasos (streaming de nodos)
        estado = estado_inicial.copy()
        for update in agente_router.stream(estado_inicial, config=config, stream_mode="updates"):
            node_name = next(iter(update.keys()))  # Seguro y correcto para dict_keys
            node_output = update[node_name]
            estado.update(node_output)
            
            if node_name == "recuperador":
                yield f"event: status\ndata: {json.dumps({'message': 'Consultando base de conocimientos...'})}\n\n"
            elif node_name == "busqueda_web":
                yield f"event: status\ndata: {json.dumps({'message': 'Buscando en el portal de la US...'})}\n\n"
            elif node_name in ["procedimental", "calendario", "normativo", "baremo", "entrevistador", "rechazo_amable"]:
                yield f"event: status\ndata: {json.dumps({'message': 'Generando respuesta...'})}\n\n"
            
            await asyncio.sleep(0.01)

        referencias = estado.get("referencias", [])
        contexto_rag = estado.get("contexto", "")
        
        # Enviar metadatos iniciales
        yield f"event: metadata\ndata: {json.dumps({'referencias': referencias, 'contexto': contexto_rag})}\n\n"
        
        # Iterar y enviar tokens en tiempo real
        respuesta_texto = ""
        stream_obj = estado.get("stream")
        generator = stream_obj.generator if hasattr(stream_obj, "generator") else stream_obj or []
        for chunk in generator:
            respuesta_texto += chunk
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.01) # Ceder control para streaming en tiempo real
            
        # Guardar el mensaje del asistente en la base de datos
        db_gen = SessionLocal()
        try:
            referencias_str = json.dumps(referencias)
            crud.crear_mensaje(db_gen, conv_id, rol="assistant", contenido=respuesta_texto, referencias=referencias_str)
            print(f"✅ Respuesta del asistente guardada en la base de datos para conv {conv_id}")
        except Exception as db_err:
            print(f"Error guardando respuesta en base de datos: {db_err}")
        finally:
            db_gen.close()
            
        # Poda de contexto
        background_tasks.add_task(actualizar_resumen_memoria, conv_id)
        background_tasks.add_task(actualizar_perfil_usuario, usuario_id, pregunta, respuesta_texto)
        
        yield "event: close\ndata: close\n\n"
        
    except Exception as e:
        print(f"Error en sse_generator: {e}")
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
