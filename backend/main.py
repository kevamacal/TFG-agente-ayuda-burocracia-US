import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import models, security
from database import engine, SessionLocal
from routers import auth, admin, conversaciones, documentos

# Configurar logger
logger = logging.getLogger(__name__)

# Crear tablas
models.Base.metadata.create_all(bind=engine)

# Migración manual de nuevas columnas a tablas existentes si ya están creadas
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil_metadata TEXT DEFAULT '{}';"))
        conn.execute(text("ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS resumen_memoria TEXT;"))
        conn.execute(text("ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS feedback BOOLEAN;"))
        conn.execute(text("ALTER TABLE mensajes ADD COLUMN IF NOT EXISTS feedback_comentario TEXT;"))
    logger.info("[main.py] Migración de base de datos completada exitosamente.")
except Exception as e:
    logger.exception(f"[main.py] Error al ejecutar migraciones de base de datos: {e}")

app = FastAPI(title="API Asistente US")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth.router)
app.include_router(conversaciones.router)
app.include_router(admin.router)
app.include_router(documentos.router)

@app.get("/")
def read_root():
    return {"mensaje": "API del Asistente US funcionando correctamente"}

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
            logger.info(f"Se ha creado la cuenta de administrador inicial: {email} / {password}")
    except Exception as e:
        logger.exception(f"Error al crear el administrador inicial: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    seed_admin_user()