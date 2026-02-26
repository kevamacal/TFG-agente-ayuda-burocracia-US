import os
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
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

template_reformulacion = """
Dada la siguiente conversación y la pregunta final del usuario, reformula la pregunta final 
para que sea independiente y contenga todo el contexto (sujetos, trámites, etc.).
NO respondas a la pregunta, SOLO devuelve la pregunta reformulada. Si ya es clara por sí sola, devuélvela tal cual.

Historial de conversación:
{historial}

Pregunta del usuario: {question}

Pregunta reformulada:
"""
prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion)
rephrase_chain = prompt_reformulacion | llm | StrOutputParser()

template_respuesta = """
Eres un Asistente de Atención al Estudiante y Soporte de la Universidad de Sevilla.
Tu objetivo principal es "salvar" a estudiantes y profesores de la burocracia, resolviendo sus dudas de la forma más práctica, clara y sencilla posible, basándote EXCLUSIVAMENTE en el contexto proporcionado.

INSTRUCCIONES CLAVE:
1. TRÁMITES Y PROCEDIMIENTOS: PRIORIZA buscar en el contexto guías de usuario o manuales. Devuelve la respuesta como una LISTA NUMERADA paso a paso.
2. DUDAS LEGALES O NORMATIVAS: Responde citando la normativa correspondiente de forma resumida.
3. NO INVENTES NADA: Si la información exacta no está, responde: "Lo siento, no encuentro la información exacta..."
4. TONO: Educado, directo y resolutivo.

CONTEXTO RECUPERADO DE LA BASE DE DATOS:
{context}

PREGUNTA DEL USUARIO:
{question}

RESPUESTA DEL ASISTENTE:
"""
prompt_respuesta = ChatPromptTemplate.from_template(template_respuesta)
generation_chain = prompt_respuesta | llm | StrOutputParser()

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def consultar_asistente(pregunta, historial_mensajes):
    historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial_mensajes[:-1]])
    
    if historial_formateado.strip():
        pregunta_busqueda = rephrase_chain.invoke({
            "historial": historial_formateado,
            "question": pregunta
        })
        # Imprimimos en consola para que veas la magia en acción
        print(f"Pregunta original: {pregunta}")
        print(f"Pregunta reformulada para la BD: {pregunta_busqueda}")
    else:
        pregunta_busqueda = pregunta

    docs = retriever.invoke(pregunta_busqueda)
    contexto_texto = format_docs(docs)
    
    stream = generation_chain.stream({
        "context": contexto_texto,
        "question": pregunta_busqueda 
    })
    
    # 5. Formatear fuentes
    fuentes_raw = [f"{doc.metadata.get('source', 'Desconocido')} (Pág {doc.metadata.get('page', '?')})" for doc in docs]
    fuentes = list(sorted(set(fuentes_raw)))
    
    return stream, fuentes