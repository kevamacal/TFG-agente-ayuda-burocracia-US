from typing import Annotated
from dependencies import DbSession, CurrentUser
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
import schemas, security, crud

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

@router.post("/registro", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: DbSession):
    db_user = crud.get_usuario_por_email(db, usuario.email)

    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya registrado")

    hashed_password = security.get_password_hash(usuario.password)
    nuevo_usuario = crud.crear_usuario(db, usuario.email, hashed_password)
    return nuevo_usuario

@router.post("/login", response_model=schemas.Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    usuario = crud.get_usuario_por_email(db, form_data.username)

    if not usuario or not security.verify_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = security.create_access_token(data={"sub": str(usuario.id)})

    return {"access_token": access_token, "token_type": "bearer", "is_admin": usuario.is_admin}

@router.get("/me", response_model=schemas.UsuarioResponse)
def leer_usuario_actual(usuario_actual: CurrentUser):
    return usuario_actual