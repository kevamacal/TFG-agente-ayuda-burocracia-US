from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import models, schemas, security
from database import engine, get_db
from agente.router import router as agente_router
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from utils.config import config_light_llm 
from database import SessionLocal
import os
import shutil
import json
from services.ingestion import procesar_un_pdf

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Asistente US")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/")
def read_root():
    return {"mensaje": "API del Asistente US funcionando correctamente"}

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
    
    return {"access_token": access_token, "token_type": "bearer", "is_admin": usuario.is_admin}


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

@app.get("/me", response_model=schemas.UsuarioResponse)
def leer_usuario_actual(usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Devuelve la info del usuario conectado actualmente (incluyendo si es is_admin)"""
    return usuario_actual

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
    
    mensajes_recientes = historial_db[-5:] if len(historial_db) > 5 else historial_db
    
    historial_langgraph = []
    if conv.resumen_memoria and len(historial_db) > 5:
        historial_langgraph.append({"role": "system", "content": f"Resumen de conversación antigua: {conv.resumen_memoria}"})
        
    historial_langgraph.extend([{"role": m.rol, "content": m.contenido} for m in mensajes_recientes])

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
            
        referencias = estado_final.get("referencias", [])
        contexto_rag = estado_final.get("contexto", "")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el agente: {str(e)}")

    referencias_str = json.dumps(referencias)
    msg_asistente = models.Mensaje(conversacion_id=conv.id, rol="assistant", contenido=respuesta_texto, referencias=referencias_str)
    db.add(msg_asistente)
    db.commit()

    # Disparamos poda de contexto asíncrona
    background_tasks.add_task(actualizar_resumen_memoria, conv.id)

    return {"respuesta": respuesta_texto, "referencias": referencias, "contexto": contexto_rag}

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

# --- ADMINISTRACIÓN ---

def get_usuario_admin(usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    if not usuario_actual.is_admin:
        raise HTTPException(status_code=403, detail="No autorizado. Solo administradores.")
    return usuario_actual

@app.post("/admin/ingestar", status_code=202)
def ingestar_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...), admin: models.Usuario = Depends(get_usuario_admin)):
    """Sube un archivo PDF de manera temporal y lo ingesta en Pinecone usando LlamaParse"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .pdf")
        
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(procesar_un_pdf, temp_path, file.filename)
    return {"mensaje": f"El archivo '{file.filename}' se está procesando en segundo plano."}