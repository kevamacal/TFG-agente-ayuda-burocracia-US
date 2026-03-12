from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

class Settings:
    def __init__(self):
        load_dotenv()
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.HUGGINGFACEHUB_API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")
        self.HUGGINGFACEHUB_MODEL = os.getenv("HUGGINGFACEHUB_MODEL")
        self.HUGGINGFACEHUB_LIGHT_MODEL = os.getenv("HUGGINGFACEHUB_LIGHT_MODEL")
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.MODEL_EMBEDDINGS = os.getenv("MODEL_EMBEDDINGS")
        self.RUTA_PDFS = self.BASE_DIR + os.getenv("RUTA_PDFS")
        self.COHERE_API_KEY = os.getenv("COHERE_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")


settings = Settings()

def config_light_llm():
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.1-8b-instant", 
        api_key=settings.GROQ_API_KEY,
        max_tokens=150 
    )
    return llm

def config_llm():
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY
    )
    return llm

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

