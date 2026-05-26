from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    perfil_metadata = Column(Text, nullable=True, default='{}')
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    conversaciones = relationship("Conversacion", back_populates="usuario", order_by="desc(Conversacion.id)", cascade="all, delete-orphan")

class Conversacion(Base):
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String, default="Nueva conversación")
    resumen_memoria = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="conversaciones")
    mensajes = relationship("Mensaje", back_populates="conversacion", order_by="Mensaje.id", cascade="all, delete-orphan")

class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True, index=True)
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=False)
    rol = Column(String, nullable=False) 
    contenido = Column(Text, nullable=False)
    referencias = Column(Text, nullable=True, default='[]')
    feedback = Column(Boolean, nullable=True)
    feedback_comentario = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    conversacion = relationship("Conversacion", back_populates="mensajes")