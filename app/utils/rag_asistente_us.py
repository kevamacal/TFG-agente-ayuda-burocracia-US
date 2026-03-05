import os, logging
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from dotenv import load_dotenv
from templates.templates import *
from classes.StateSchema import StateSchema 
from utils.config import format_docs, config_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
llm = config_llm()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = BASE_DIR + os.getenv("DB_PATH")
API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")

embeddings = HuggingFaceEndpointEmbeddings(model=os.getenv("MODEL_EMBEDDINGS"), huggingfacehub_api_token=API_KEY)
vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

def insertar_contexto(state: StateSchema):
    docs = retriever.invoke(state["pregunta"])
    logger.info(f"Documentos recuperados: {len(docs)}")
    for i, doc in enumerate(docs):
        fuente = doc.metadata.get('source', 'Desconocida')
        logger.info(f"Doc {i+1} | Fuente: {fuente} | Contenido (preview): {doc.page_content[:100]}...")
    return {"contexto": format_docs(docs)}

def contiene_duda_burocratica(pregunta, historial, contexto):
    historial_formateado = ""
    if historial:
        historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
    template = template_deteccion()
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    respuesta = chain.invoke({
        "question": pregunta,
        "historial": historial_formateado,
        "context": contexto
    })
    
    respuesta_limpia = respuesta.strip().lower()
    
    return respuesta_limpia