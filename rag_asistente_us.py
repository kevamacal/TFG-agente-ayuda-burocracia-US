import os
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "./chroma_documentos_us_db"
MODEL_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" 
MODEL_CHAT = "llama3.1"     

embeddings = HuggingFaceEmbeddings(model_name=MODEL_EMBEDDINGS)

if os.path.exists(DB_PATH):
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
else:
    raise FileNotFoundError(f"❌ No se encuentra la base de datos en {DB_PATH}. Ejecuta primero setup_completo.py")

llm = ChatOllama(model=MODEL_CHAT, temperature=0)

template = """
Eres un Asistente de Atención al Estudiante y Soporte de la Universidad de Sevilla.
Tu objetivo principal es "salvar" a estudiantes y profesores de la burocracia, resolviendo sus dudas de la forma más práctica, clara y sencilla posible, basándote EXCLUSIVAMENTE en el contexto proporcionado.

INSTRUCCIONES CLAVE:
1. TRÁMITES Y PROCEDIMIENTOS ("¿Cómo hago...?", "¿Cómo me matriculo?"): Si el usuario pregunta por los pasos para hacer algo, PRIORIZA buscar en el contexto guías de usuario o manuales (como el de Automatrícula MATRUX). Devuelve la respuesta como una LISTA NUMERADA paso a paso (dónde entrar, qué botones pulsar, qué seleccionar).
2. DUDAS LEGALES O NORMATIVAS: Si la pregunta es teórica (ej. requisitos, derechos, competencias), responde citando la normativa correspondiente de forma resumida y comprensible.
3. NO INVENTES NADA: Si la información exacta no está en el contexto proporcionado, responde exactamente: "Lo siento, no encuentro los pasos o la información exacta en la documentación disponible. Te sugiero contactar con la Secretaría de tu centro o revisar la web principal de la US."
4. TONO: Debe ser educado, directo y resolutivo. Evita lenguaje legal excesivamente denso a menos que sea estrictamente necesario.

CONTEXTO RECUPERADO DE LA BASE DE DATOS:
{context}

PREGUNTA DEL USUARIO:
{question}

RESPUESTA DEL ASISTENTE:
"""

prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def consultar_asistente(pregunta):
    docs = retriever.invoke(pregunta)
    respuesta = rag_chain.invoke(pregunta)
    
    fuentes_raw = [f"{doc.metadata.get('source', 'Desconocido')} (Pág {doc.metadata.get('page', '?')})" for doc in docs]
    fuentes = list(sorted(set(fuentes_raw)))
    
    return respuesta, fuentes