import os
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from dotenv import load_dotenv
from templates.templates import *
from classes.StateSchema import StateSchema 
from utils.config import format_docs

load_dotenv()
llm = ChatOllama(model=os.getenv("MODEL_CHAT"), temperature=0)

def insertar_contexto(state: StateSchema):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = BASE_DIR + os.getenv("DB_PATH")
    embeddings = OllamaEmbeddings(model=os.getenv("MODEL_EMBEDDINGS"))
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    return {"contexto": format_docs(retriever.invoke(state["pregunta"]))}

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
    
    return "sí" in respuesta_limpia or "si" in respuesta_limpia