from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    fecha_creacion: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class MensajeBase(BaseModel):
    rol: str
    contenido: str

class MensajeResponse(MensajeBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True

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