from sqlalchemy.orm import Session
import models

# --- USUARIOS ---

def get_usuario_por_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def get_usuario_por_id(db: Session, usuario_id: int):
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def get_usuarios(db: Session):
    return db.query(models.Usuario).order_by(models.Usuario.id).all()

def crear_usuario(db: Session, email: str, hashed_password: str, is_admin: bool = False):
    nuevo_usuario = models.Usuario(email=email, hashed_password=hashed_password, is_admin=is_admin)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

def eliminar_usuario(db: Session, usuario: models.Usuario):
    db.delete(usuario)
    db.commit()

def actualizar_permisos_admin(db: Session, usuario: models.Usuario, is_admin: bool):
    usuario.is_admin = is_admin
    db.commit()
    db.refresh(usuario)
    return usuario

def actualizar_perfil_metadata(db: Session, usuario: models.Usuario, perfil_metadata: str):
    usuario.perfil_metadata = perfil_metadata
    db.commit()
    db.refresh(usuario)
    return usuario


# --- CONVERSACIONES ---

def get_conversaciones_usuario(db: Session, usuario_id: int):
    return db.query(models.Conversacion).filter(
        models.Conversacion.usuario_id == usuario_id
    ).order_by(models.Conversacion.id.desc()).all()

def get_conversacion(db: Session, conversacion_id: int, usuario_id: int):
    return db.query(models.Conversacion).filter(
        models.Conversacion.id == conversacion_id,
        models.Conversacion.usuario_id == usuario_id
    ).first()

def get_conversacion_por_id(db: Session, conversacion_id: int):
    return db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id).first()

def crear_conversacion(db: Session, usuario_id: int, titulo: str):
    nueva_conv = models.Conversacion(usuario_id=usuario_id, titulo=titulo)
    db.add(nueva_conv)
    db.commit()
    db.refresh(nueva_conv)
    return nueva_conv

def eliminar_conversacion(db: Session, conversacion: models.Conversacion):
    db.delete(conversacion)
    db.commit()

def actualizar_titulo_conversacion(db: Session, conversacion: models.Conversacion, titulo: str):
    conversacion.titulo = titulo
    db.commit()
    db.refresh(conversacion)
    return conversacion

def actualizar_resumen_memoria_conversacion(db: Session, conversacion: models.Conversacion, resumen: str):
    conversacion.resumen_memoria = resumen
    db.commit()
    db.refresh(conversacion)
    return conversacion


# --- MENSAJES ---

def crear_mensaje(db: Session, conversacion_id: int, rol: str, contenido: str, referencias: str = None):
    nuevo_msg = models.Mensaje(
        conversacion_id=conversacion_id,
        rol=rol,
        contenido=contenido,
        referencias=referencias
    )
    db.add(nuevo_msg)
    db.commit()
    db.refresh(nuevo_msg)
    return nuevo_msg

def get_mensaje(db: Session, mensaje_id: int, conversacion_id: int):
    return db.query(models.Mensaje).filter(
        models.Mensaje.id == mensaje_id,
        models.Mensaje.conversacion_id == conversacion_id
    ).first()

def get_mensajes_conversacion(db: Session, conversacion_id: int):
    return db.query(models.Mensaje).filter(
        models.Mensaje.conversacion_id == conversacion_id
    ).order_by(models.Mensaje.fecha_creacion.asc(), models.Mensaje.id.asc()).all()

def actualizar_feedback_mensaje(db: Session, mensaje: models.Mensaje, feedback: bool, comentario: str):
    mensaje.feedback = feedback
    mensaje.feedback_comentario = comentario
    db.commit()
    db.refresh(mensaje)
    return mensaje


# --- CONSULTAS DE ADMINISTRACIÓN ---

def get_mensajes_con_feedback_negativo(db: Session):
    return db.query(models.Mensaje).filter(
        models.Mensaje.feedback == False,
        models.Mensaje.rol == "assistant"
    ).order_by(models.Mensaje.fecha_creacion.desc()).all()

def get_pregunta_previa(db: Session, conversacion_id: int, fecha_creacion):
    return db.query(models.Mensaje).filter(
        models.Mensaje.conversacion_id == conversacion_id,
        models.Mensaje.fecha_creacion < fecha_creacion
    ).order_by(models.Mensaje.fecha_creacion.desc()).first()
