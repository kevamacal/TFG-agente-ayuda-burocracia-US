import os
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from dotenv import load_dotenv
from templates.templates import * 

load_dotenv()

def obtener_rag():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = BASE_DIR + os.getenv("DB_PATH")
    embeddings = OllamaEmbeddings(model=os.getenv("MODEL_EMBEDDINGS"))
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    return retriever

def contiene_duda_burocratica(pregunta, contexto, historial):
    template = template_deteccion(pregunta, contexto, historial)
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke() == "Sí"