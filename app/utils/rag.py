import os, logging
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from templates.templates import *
from classes.StateSchema import StateSchema 
from utils.config import format_docs, config_llm
from templates.templates import template_reformulacion
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
llm = config_llm()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)

embeddings = HuggingFaceEndpointEmbeddings(model=os.getenv("MODEL_EMBEDDINGS"), huggingfacehub_api_token=API_KEY)
vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=embeddings)
retriever = vectorstore.as_retriever(search_type="mmr",search_kwargs={"k": 6})

def insertar_contexto(state: StateSchema):
    pregunta = state["pregunta"]
    historial = state["historial"]
    
    if historial:
        historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
        prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion())
        rephrase_chain = prompt_reformulacion | llm | StrOutputParser()
        pregunta_busqueda = rephrase_chain.invoke({
            "historial": historial_formateado,
            "question": pregunta
        })
    else:
        pregunta_busqueda = pregunta

    docs = retriever.invoke(pregunta_busqueda)
    logger.info(f"Documentos recuperados: {len(docs)}")
    
    return {
        "contexto": format_docs(docs),
        "pregunta_reformulada": pregunta_busqueda
    }

def contiene_duda_burocratica(pregunta, historial, contexto, pregunta_reformulada):
    historial_formateado = ""
    if historial:
        historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
    
    template = template_deteccion()
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    respuesta = chain.invoke({
        "question": pregunta_reformulada, 
        "historial": historial_formateado,
        "context": contexto
    })
    return respuesta.strip().lower()