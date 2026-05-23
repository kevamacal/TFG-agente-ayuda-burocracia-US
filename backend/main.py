from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import models, schemas, security
from database import engine, get_db
from agente.router import router as agente_router
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from utils.config import config_light_llm 
from database import SessionLocal
import os
import shutil
import json
from services.ingestion import procesar_un_pdf, eliminar_vectores_de_pdf

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Asistente US")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

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


def get_usuario_actual(
    token: str | None = Depends(oauth2_scheme), 
    token_query: str | None = Query(None, alias="token"), 
    db: Session = Depends(get_db)
):
    """Extrae el usuario de la base de datos usando el token JWT (desde cabecera o query param)"""
    actual_token = token or token_query
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not actual_token:
        raise credentials_exception
    try:
        payload = jwt.decode(actual_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
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
    """Guarda el mensaje del usuario y devuelve un flujo SSE (Server-Sent Events) de la respuesta del agente"""
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
    
    async def sse_generator():
        try:
            # Ejecutar el agente para obtener el contexto y referencias, y la referencia del stream
            estado_final = agente_router.invoke(estado_inicial)
            referencias = estado_final.get("referencias", [])
            contexto_rag = estado_final.get("contexto", "")
            
            # Enviar metadatos iniciales
            yield f"event: metadata\ndata: {json.dumps({'referencias': referencias, 'contexto': contexto_rag})}\n\n"
            
            # Iterar y enviar tokens en tiempo real
            respuesta_texto = ""
            for chunk in estado_final.get("stream", []):
                respuesta_texto += chunk
                yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                await asyncio.sleep(0.01) # Ceder control para streaming en tiempo real
                
            # Guardar el mensaje del asistente en la base de datos
            db_gen = SessionLocal()
            try:
                referencias_str = json.dumps(referencias)
                msg_asistente = models.Mensaje(conversacion_id=conv.id, rol="assistant", contenido=respuesta_texto, referencias=referencias_str)
                db_gen.add(msg_asistente)
                db_gen.commit()
                print(f"✅ Respuesta del asistente guardada en la base de datos para conv {conv.id}")
            except Exception as db_err:
                print(f"Error guardando respuesta en base de datos: {db_err}")
            finally:
                db_gen.close()
                
            # Poda de contexto
            background_tasks.add_task(actualizar_resumen_memoria, conv.id)
            
            yield "event: close\ndata: close\n\n"
            
        except Exception as e:
            print(f"Error en sse_generator: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

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
        
    background_tasks.add_task(procesar_un_pdf, temp_path, file.filename, False)
    return {"mensaje": f"El archivo '{file.filename}' se está procesando en segundo plano."}


# Endpoints de administración de usuarios
@app.get("/admin/usuarios", response_model=list[schemas.UsuarioResponse])
def listar_usuarios(admin: models.Usuario = Depends(get_usuario_admin), db: Session = Depends(get_db)):
    """Lista todos los usuarios (solo admin)"""
    return db.query(models.Usuario).order_by(models.Usuario.id).all()

@app.post("/admin/usuarios", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario_admin(usuario: schemas.UsuarioAdminCreate, admin: models.Usuario = Depends(get_usuario_admin), db: Session = Depends(get_db)):
    """Crea un nuevo usuario con rol configurable (solo admin)"""
    db_user = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    hashed_password = security.get_password_hash(usuario.password)
    nuevo_usuario = models.Usuario(email=usuario.email, hashed_password=hashed_password, is_admin=usuario.is_admin)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.delete("/admin/usuarios/{usuario_id}")
def eliminar_usuario_admin(usuario_id: int, admin: models.Usuario = Depends(get_usuario_admin), db: Session = Depends(get_db)):
    """Elimina un usuario (solo admin)"""
    if usuario_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
        
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    db.delete(usuario)
    db.commit()
    return {"mensaje": "Usuario eliminado correctamente"}

@app.put("/admin/usuarios/{usuario_id}/admin", response_model=schemas.UsuarioResponse)
def cambiar_permisos_admin(usuario_id: int, req: schemas.UsuarioAdminUpdateRole, admin: models.Usuario = Depends(get_usuario_admin), db: Session = Depends(get_db)):
    """Otorga o elimina permisos de administrador a un usuario (solo admin)"""
    if usuario_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tus propios permisos de administrador")
        
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    usuario.is_admin = req.is_admin
    db.commit()
    db.refresh(usuario)
    return usuario

# Endpoints de documentos (obtenidos de Pinecone)
@app.get("/documentos", response_model=list[schemas.DocumentoResponse])
def listar_documentos(usuario_actual: models.Usuario = Depends(get_usuario_actual)):
    """Devuelve la lista de documentos en la base de datos vectorial Pinecone"""
    try:
        from pinecone import Pinecone
        from utils.config import settings
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index("index-tfg")
        res = index.query(
            vector=[0.0] * 1024,
            top_k=10000,
            include_metadata=True
        )
        sources = set()
        for match in res.get("matches", []):
            metadata = match.get("metadata", {})
            source = metadata.get("source")
            if source:
                sources.add(source)
        return [{"nombre": s} for s in sorted(sources)]
    except Exception as e:
        print(f"Error consultando documentos de Pinecone: {e}")
        return []

@app.delete("/admin/documentos")
def eliminar_documento_admin(nombre: str = Query(..., description="Nombre del documento a eliminar"), admin: models.Usuario = Depends(get_usuario_admin)):
    """Elimina los vectores de Pinecone y el archivo del disco (solo admin)"""
    # 1. Eliminar vectores de Pinecone
    eliminar_vectores_de_pdf(nombre)
    
    # 2. Eliminar archivo físico de la carpeta estática
    static_dir = os.path.join(os.path.dirname(__file__), "static", "documentos")
    ruta_archivo = os.path.join(static_dir, nombre)
    if os.path.exists(ruta_archivo):
        try:
            os.remove(ruta_archivo)
            print(f"Archivo eliminado de static: {ruta_archivo}")
        except Exception as e:
            print(f"Error eliminando archivo físico {ruta_archivo}: {e}")
            
    # 3. Eliminar archivo de la carpeta Documentos_US
    source_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Documentos_US")),
        "/Documentos_US"
    ]
    for sdir in source_dirs:
        alt_path = os.path.join(sdir, nombre)
        if os.path.exists(alt_path):
            try:
                os.remove(alt_path)
                print(f"Archivo eliminado de {sdir}: {alt_path}")
            except Exception as e:
                print(f"Error al eliminar archivo de {sdir}: {e}")
                
    return {"mensaje": f"Documento '{nombre}' y sus vectores eliminados con éxito."}

def seed_admin_user():
    db = SessionLocal()
    try:
        # Verificar si ya existe algún administrador
        admin_exists = db.query(models.Usuario).filter(models.Usuario.is_admin == True).first()
        if not admin_exists:
            email = "admin@us.es"
            password = "adminpassword"
            hashed_pwd = security.get_password_hash(password)
            nuevo_admin = models.Usuario(
                email=email,
                hashed_password=hashed_pwd,
                is_admin=True
            )
            db.add(nuevo_admin)
            db.commit()
            print(f"🔑 Se ha creado la cuenta de administrador inicial: {email} / {password}")
    except Exception as e:
        print(f"Error al crear el administrador inicial: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    seed_admin_user()