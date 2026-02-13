import os
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("MODEL")
DB_PATH = "./chroma_documentos_us_db"

embeddings = OllamaEmbeddings(model=MODEL_NAME)
if os.path.exists(DB_PATH):
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
else:
    raise FileNotFoundError(f"No se encuentra la DB en {DB_PATH}. ¿Ejecutaste el ingest?")

llm = ChatOllama(model="llama3.2", temperature=0)

template = """
Eres un Asistente Administrativo Experto de la Universidad de Sevilla.
Tu trabajo es resolver dudas sobre normativas, matrículas y procedimientos basándote EXCLUSIVAMENTE en el contexto proporcionado.

INSTRUCCIONES:
1. Responde de forma clara, directa y educada.
2. Si la respuesta aparece en el contexto, CITA el documento o artículo (ej: "Según la Normativa de Matrícula...").
3. Si la información no está en el contexto, di: "Lo siento, no encuentro esa información en la normativa disponible." NO inventes nada.

CONTEXTO DE LA NORMATIVA:
{context}

PREGUNTA DEL USUARIO:
{question}
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
    
    fuentes = []
    for doc in docs:
        fuentes.append(f"{doc.metadata.get('source', 'Desconocido')} (Pág. {doc.metadata.get('page', '?')})")
    
    fuentes = list(set(fuentes))
    
    return respuesta, fuentes