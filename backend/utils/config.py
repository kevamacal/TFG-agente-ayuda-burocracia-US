from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

class Settings:
    def __init__(self):
        load_dotenv()
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.MODEL_EMBEDDINGS = os.getenv("MODEL_EMBEDDINGS")
        self.RUTA_PDFS = self.BASE_DIR + os.getenv("RUTA_PDFS")
        self.COHERE_API_KEY = os.getenv("COHERE_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")


settings = Settings()

def config_classifier_llm():
    """LLM ultra-ligero para cadenas de clasificación que solo devuelven 1 palabra."""
    llm = ChatGroq(
        temperature=0.0, 
        model_name="llama-3.1-8b-instant", 
        api_key=settings.GROQ_API_KEY,
        max_tokens=15,
        max_retries=3
    )
    return llm

def config_light_llm():
    """LLM ligero para reformulación, consulta al usuario y rechazo amable."""
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.1-8b-instant", 
        api_key=settings.GROQ_API_KEY,
        max_tokens=1000,
        max_retries=3
    )
    return llm

def config_llm():
    """LLM principal para los nodos resolutores (baremo, normativo, etc.)."""
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        max_tokens=1500,
        max_retries=10
    )
    return llm

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def get_eval_llm(model_name: str, temperature: float):
    """Genera una instancia de LLM dinámica para pruebas."""
    return ChatGroq(
        temperature=temperature, 
        model_name=model_name, 
        api_key=settings.GROQ_API_KEY,
        max_retries=10
    )