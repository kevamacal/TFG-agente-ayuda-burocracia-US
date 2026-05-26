from typing import Annotated
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from dependencies import DbSession, CurrentUser
from services.chat_helpers import generar_y_guardar_titulo
from services import chat_service
import schemas, crud

router = APIRouter(
    prefix="/conversaciones",
    tags=["Conversaciones"]
)

detail_404_error = "Conversación no encontrada"

@router.get("", response_model=list[schemas.ConversacionResponse])
def listar_conversaciones(usuario_actual: CurrentUser, db: DbSession):
    """Devuelve todas las conversaciones del usuario logueado"""
    return crud.get_conversaciones_usuario(db, usuario_actual.id)

@router.post("", response_model=schemas.ConversacionResponse)
def crear_conversacion(
    conversacion: schemas.ConversacionCreate,
    db: DbSession,
    usuario_actual: CurrentUser
):
    """Crea un nuevo chat vacío"""
    return crud.crear_conversacion(db, usuario_actual.id, conversacion.titulo)

@router.get("/{conversacion_id}/mensajes", response_model=list[schemas.MensajeResponse])
def obtener_mensajes(
    conversacion_id: int,
    db: DbSession,
    usuario_actual: CurrentUser,
):
    """Devuelve el historial de una conversación específica"""
    conversacion = crud.get_conversacion(db, conversacion_id, usuario_actual.id)

    if not conversacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_404_error)
    
    return crud.get_mensajes_conversacion(db, conversacion_id)

@router.post("/{conversacion_id}/chat")
def enviar_mensaje(
    conversacion_id: int,
    chat_req: schemas.PreguntaChat,
    background_tasks: BackgroundTasks,
    db: DbSession,
    usuario_actual: CurrentUser
):
    """Guarda el mensaje del usuario y devuelve un flujo SSE (Server-Sent Events) de la respuesta del agente"""
    conv = crud.get_conversacion(db, conversacion_id, usuario_actual.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_404_error)
    
    if conv.titulo == "Nueva conversación":
        background_tasks.add_task(generar_y_guardar_titulo, conv.id, chat_req.pregunta)
    
    # Registrar el mensaje del usuario en la base de datos
    crud.crear_mensaje(db, conv.id, rol="user", contenido=chat_req.pregunta)

    # Preparar el historial mediante el servicio de chat
    historial = chat_service.preparar_historial(db, conv, usuario_actual)

    # Obtener el stream del generador SSE
    generator = chat_service.sse_chat_generator(
        conv_id=conv.id,
        usuario_id=usuario_actual.id,
        pregunta=chat_req.pregunta,
        historial=historial,
        background_tasks=background_tasks
    )

    return StreamingResponse(generator, media_type="text/event-stream")

@router.delete("/{conversacion_id}")
def eliminar_conversacion(
    conversacion_id: int, 
    db: DbSession, 
    usuario_actual: CurrentUser
):
    """Elimina una conversación y todos sus mensajes (gracias al cascade delete)"""
    conv = crud.get_conversacion(db, conversacion_id, usuario_actual.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_404_error)
    
    crud.eliminar_conversacion(db, conv)
    return {"mensaje": "Conversación eliminada correctamente"}

@router.put("/{conversacion_id}", response_model=schemas.ConversacionResponse)
def renombrar_conversacion(
    conversacion_id: int, 
    conversacion: schemas.ConversacionCreate, 
    db: DbSession, 
    usuario_actual: CurrentUser
):
    """Actualiza el título de una conversación"""
    conv = crud.get_conversacion(db, conversacion_id, usuario_actual.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_404_error)
    
    return crud.actualizar_titulo_conversacion(db, conv, conversacion.titulo)

@router.post("/{conversacion_id}/mensajes/{mensaje_id}/feedback", response_model=schemas.MensajeResponse)
def registrar_feedback_mensaje(
    conversacion_id: int,
    mensaje_id: int,
    req: schemas.MensajeFeedbackUpdate,
    db: DbSession,
    usuario_actual: CurrentUser
):
    """Permite registrar o actualizar el feedback (positivo/negativo) y comentario de un mensaje"""
    conv = crud.get_conversacion(db, conversacion_id, usuario_actual.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail_404_error)
        
    msg = crud.get_mensaje(db, mensaje_id, conversacion_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensaje no encontrado")
        
    return crud.actualizar_feedback_mensaje(db, msg, req.feedback, req.feedback_comentario)