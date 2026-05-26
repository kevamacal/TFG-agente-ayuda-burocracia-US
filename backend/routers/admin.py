from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Query
from dependencies import DbSession, CurrentAdmin
from services.ingestion import procesar_un_pdf, eliminar_vectores_de_pdf
import schemas, security, crud
import os
import shutil

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Administración"]
)

@router.get("/feedback/negativo")
def listar_feedback_negativo(
    admin: CurrentAdmin,
    db: DbSession
):
    """Devuelve los mensajes valorados con feedback negativo junto con la pregunta previa (contexto de usuario)"""
    mensajes_negativos = crud.get_mensajes_con_feedback_negativo(db)
    
    resultado = []
    for msg in mensajes_negativos:
        pregunta_previa = crud.get_pregunta_previa(db, msg.conversacion_id, msg.fecha_creacion)
        pregunta_texto = pregunta_previa.contenido if pregunta_previa else "Desconocida"
        
        resultado.append({
            "mensaje_id": msg.id,
            "conversacion_id": msg.conversacion_id,
            "pregunta_usuario": pregunta_texto,
            "respuesta_asistente": msg.contenido,
            "referencias": msg.referencias,
            "feedback_comentario": msg.feedback_comentario,
            "fecha_creacion": msg.fecha_creacion
        })
        
    return resultado

@router.post("/ingestar", status_code=202)
def ingestar_pdf(
    background_tasks: BackgroundTasks, 
    admin: CurrentAdmin,
    file: UploadFile = File(...)
):
    """Sube un archivo PDF de manera temporal y lo ingesta en Pinecone usando LlamaParse"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos .pdf")
        
    # Obtener el directorio backend base (padre de routers/)
    base_dir = os.path.dirname(os.path.dirname(__file__))
    temp_dir = os.path.join(base_dir, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(procesar_un_pdf, temp_path, file.filename, False)
    return {"mensaje": f"El archivo '{file.filename}' se está procesando en segundo plano."}

@router.get("/usuarios", response_model=list[schemas.UsuarioResponse])
def listar_usuarios(
    admin: CurrentAdmin, 
    db: DbSession
):
    """Lista todos los usuarios (solo admin)"""
    return crud.get_usuarios(db)

@router.post("/usuarios", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario_admin(
    usuario: schemas.UsuarioAdminCreate, 
    admin: CurrentAdmin, 
    db: DbSession
):
    """Crea un nuevo usuario con rol configurable (solo admin)"""
    db_user = crud.get_usuario_por_email(db, usuario.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está registrado")
    
    hashed_password = security.get_password_hash(usuario.password)
    nuevo_usuario = crud.crear_usuario(db, usuario.email, hashed_password, is_admin=usuario.is_admin)
    return nuevo_usuario

@router.delete("/usuarios/{usuario_id}")
def eliminar_usuario_admin(
    usuario_id: int, 
    admin: CurrentAdmin, 
    db: DbSession
):
    """Elimina un usuario (solo admin)"""
    if usuario_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes eliminarte a ti mismo")
        
    usuario = crud.get_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
    crud.eliminar_usuario(db, usuario)
    return {"mensaje": "Usuario eliminado correctamente"}

@router.put("/usuarios/{usuario_id}/admin", response_model=schemas.UsuarioResponse)
def cambiar_permisos_admin(
    usuario_id: int, 
    req: schemas.UsuarioAdminUpdateRole, 
    admin: CurrentAdmin, 
    db: DbSession
):
    """Otorga o elimina permisos de administrador a un usuario (solo admin)"""
    if usuario_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes cambiar tus propios permisos de administrador")
        
    usuario = crud.get_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        
    return crud.actualizar_permisos_admin(db, usuario, req.is_admin)

@router.delete("/documentos")
def eliminar_documento_admin(
    admin: CurrentAdmin,
    nombre: str = Query(..., description="Nombre del documento a eliminar")
):
    """Elimina los vectores de Pinecone y el archivo del disco (solo admin)"""
    # 1. Eliminar vectores de Pinecone
    eliminar_vectores_de_pdf(nombre)
    
    # 2. Eliminar archivo físico de la carpeta estática
    base_dir = os.path.dirname(os.path.dirname(__file__))
    static_dir = os.path.join(base_dir, "static", "documentos")
    ruta_archivo = os.path.join(static_dir, nombre)
    if os.path.exists(ruta_archivo):
        try:
            os.remove(ruta_archivo)
            logger.info(f"Archivo eliminado de static: {ruta_archivo}")
        except Exception as e:
            logger.error(f"Error eliminando archivo físico {ruta_archivo}: {e}")
    return {"mensaje": f"Documento '{nombre}' y sus vectores eliminados con éxito."}
