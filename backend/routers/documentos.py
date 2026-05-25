from typing import Annotated
from fastapi import APIRouter
from dependencies import CurrentUser
import schemas

router = APIRouter(
    prefix="/documentos",
    tags=["Documentos"]
)

@router.get("", response_model=list[schemas.DocumentoResponse])
def listar_documentos(usuario_actual: CurrentUser):
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
