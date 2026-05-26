from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from jose import jwt, JWTError
import security, models, crud


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

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
        
    usuario = crud.get_usuario_por_id(db, int(usuario_id))
    if usuario is None:
        raise credentials_exception
    return usuario

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[models.Usuario, Depends(get_usuario_actual)]

def get_usuario_admin(usuario_actual: CurrentUser):
    if not usuario_actual.is_admin:
        raise HTTPException(status_code=403, detail="No autorizado. Solo administradores.")
    return usuario_actual

CurrentAdmin = Annotated[models.Usuario, Depends(get_usuario_admin)]