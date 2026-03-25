from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import models, schemas, security
from database import engine, get_db
from agente.router import router as agente_router
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks 
from utils.config import config_light_llm 
from database import SessionLocal

# Crea las tablas si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Asistente US")

# --- DEPENDENCIAS DE AUTENTICACIÓN ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/")
def read_root():
    return {"mensaje": "API del Asistente US funcionando correctamente 🚀"}

@app.post("/registro", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    hashed_password = security.get_password_hash(usuario.password)
    
    nuevo_usuario = models.Usuario(email=usuario.email, hashed_password=hashed_password)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return nuevo_usuario

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not usuario or not security.verify_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(data={"sub": str(usuario.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}


def get_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Extrae el usuario de la base de datos usando el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    usuario = db.query(models.Usuario).filter(models.Usuario.id == int(usuario_id)).first()
    if usuario is None:
        raise credentials_exception
    return usuario

@app.get("/conversaciones", response_model=list[schemas.ConversacionResponse])
def listar_conversaciones(usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Devuelve todas las conversaciones del usuario logueado"""
    return usuario_actual.conversaciones

@app.post("/conversaciones", response_model=schemas.ConversacionResponse)
def crear_conversacion(conversacion: schemas.ConversacionCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Crea un nuevo chat vacío"""
    nueva_conv = models.Conversacion(usuario_id=usuario_actual.id, titulo=conversacion.titulo)
    db.add(nueva_conv)
    db.commit()
    db.refresh(nueva_conv)
    return nueva_conv

@app.get("/conversaciones/{conversacion_id}/mensajes", response_model=list[schemas.MensajeResponse])
def obtener_mensajes(conversacion_id: int, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Devuelve el historial de una conversación específica"""
    conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id, models.Conversacion.usuario_id == usuario_actual.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conv.mensajes


@app.post("/conversaciones/{conversacion_id}/chat")
def enviar_mensaje(
    conversacion_id: int, 
    chat_req: schemas.PreguntaChat, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    usuario_actual: models.Usuario = Depends(get_usuario_actual)
):
    """Guarda el mensaje del usuario, consulta a LangGraph y guarda la respuesta"""
    conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id, models.Conversacion.usuario_id == usuario_actual.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    if conv.titulo == "Nueva conversación":
        background_tasks.add_task(generar_y_guardar_titulo, conv.id, chat_req.pregunta)
    
    msg_usuario = models.Mensaje(conversacion_id=conv.id, rol="user", contenido=chat_req.pregunta)
    db.add(msg_usuario)
    db.commit()

    historial_db = db.query(models.Mensaje).filter(models.Mensaje.conversacion_id == conv.id).order_by(models.Mensaje.fecha_creacion).all()
    historial_langgraph = [{"role": m.rol, "content": m.contenido} for m in historial_db]

    estado_inicial = {
        "pregunta": chat_req.pregunta, 
        "historial": historial_langgraph, 
        "contexto": "", 
        "stream": None,
        "referencias": []
    }
    
    try:
        estado_final = agente_router.invoke(estado_inicial)
        
        respuesta_texto = ""
        for chunk in estado_final["stream"]:
            respuesta_texto += chunk
            
        # Añadir referencias si existen
        referencias = estado_final.get("referencias", [])
        if referencias:
            referencias_md = "\n".join([f"- {ref}" for ref in referencias])
            respuesta_texto += f"\n\n**Fuentes consultadas**\n\n{referencias_md}"
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el agente: {str(e)}")

    msg_asistente = models.Mensaje(conversacion_id=conv.id, rol="assistant", contenido=respuesta_texto)
    db.add(msg_asistente)
    db.commit()

    return {"respuesta": respuesta_texto, "referencias": referencias}

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
        
@app.delete("/conversaciones/{conversacion_id}")
def eliminar_conversacion(conversacion_id: int, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Elimina una conversación y todos sus mensajes (gracias al cascade delete)"""
    conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id, models.Conversacion.usuario_id == usuario_actual.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    db.delete(conv)
    db.commit()
    return {"mensaje": "Conversación eliminada correctamente"}

@app.put("/conversaciones/{conversacion_id}", response_model=schemas.ConversacionResponse)
def renombrar_conversacion(conversacion_id: int, conversacion: schemas.ConversacionCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Actualiza el título de una conversación"""
    conv = db.query(models.Conversacion).filter(models.Conversacion.id == conversacion_id, models.Conversacion.usuario_id == usuario_actual.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conv.titulo = conversacion.titulo
    db.commit()
    db.refresh(conv)
    return conv