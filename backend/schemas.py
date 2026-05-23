from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool = False
    perfil_metadata: Optional[str] = '{}'
    fecha_creacion: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False

class MensajeBase(BaseModel):
    rol: str
    contenido: str

class MensajeResponse(MensajeBase):
    id: int
    fecha_creacion: datetime
    referencias: str | None = None
    feedback: Optional[bool] = None
    feedback_comentario: Optional[str] = None

    class Config:
        from_attributes = True

class MensajeFeedbackUpdate(BaseModel):
    feedback: bool
    feedback_comentario: Optional[str] = None


class ConversacionCreate(BaseModel):
    titulo: str

class ConversacionResponse(BaseModel):
    id: int
    titulo: str
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class PreguntaChat(BaseModel):
    pregunta: str

class UsuarioAdminCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = False

class UsuarioAdminUpdateRole(BaseModel):
    is_admin: bool

class DocumentoResponse(BaseModel):
    nombre: str