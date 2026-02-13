import os
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
DB_PATH = "./chroma_documentos_us_db"
MODEL_EMBEDDINGS = "sentence-transformers/all-MiniLM-L6-v2" # Rápido y eficiente en CPU
MODEL_CHAT = "llama3.2" # Tu modelo local de Ollama

# 1. Cargar Embeddings (HuggingFace)
# Usamos el mismo modelo que en el setup.py para que coincidan los vectores
embeddings = HuggingFaceEmbeddings(model_name=MODEL_EMBEDDINGS)

# 2. Conectar a la Base de Datos
if os.path.exists(DB_PATH):
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    # k=6: Recuperamos 6 fragmentos para dar suficiente contexto al LLM
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
else:
    raise FileNotFoundError(f"❌ No se encuentra la base de datos en {DB_PATH}. Ejecuta primero setup_completo.py")

# 3. Configurar el LLM (Llama 3.2)
# Temperature=0 para que sea riguroso y no creativo con las leyes
llm = ChatOllama(model=MODEL_CHAT, temperature=0)

# 4. DEFINICIÓN DEL PROMPT (Tu plantilla personalizada)
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

# Función auxiliar para formatear los documentos recuperados en texto plano
def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

# 5. Cadena RAG (Retrieval-Augmented Generation)
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 6. Función pública para llamar desde la APP (Streamlit)
def consultar_asistente(pregunta):
    """
    Recibe una pregunta, busca en la DB, genera respuesta con LLM
    y devuelve el texto + las fuentes consultadas.
    """
    # 1. Recuperar documentos (para mostrar fuentes)
    docs = retriever.invoke(pregunta)
    
    # 2. Generar respuesta
    respuesta = rag_chain.invoke(pregunta)
    
    # 3. Procesar fuentes para mostrarlas limpias en la web
    # Formato: "NombreArchivo (Pág X)"
    fuentes_raw = [f"{doc.metadata.get('source', 'Desconocido')} (Pág {doc.metadata.get('page', '?')})" for doc in docs]
    # Eliminar duplicados manteniendo el orden
    fuentes = list(sorted(set(fuentes_raw)))
    
    return respuesta, fuentes