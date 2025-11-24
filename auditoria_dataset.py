# auditar_dataset.py
import os
import psycopg2
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

load_dotenv()

# CONFIGURACIÓN
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# 1. Cargar Recursos
embeddings = OllamaEmbeddings(model=os.getenv("MODEL"))
llm = ChatOllama(model="llama3.1", temperature=0)

# Cargar las Reglas para evaluar
if not os.path.exists("./chroma_rules_db"):
    print("❌ Primero ejecuta ingest_rules.py")
    exit()
rules_vectorstore = Chroma(persist_directory="./chroma_rules_db", embedding_function=embeddings)
rules_retriever = rules_vectorstore.as_retriever(search_kwargs={"k": 4})

# Crear nueva DB para los "Casos de Estudio" (Feedback)
feedback_vectorstore = Chroma(persist_directory="./chroma_feedback_db", embedding_function=embeddings)

def obtener_entrevistas():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id, titulo, transcripcion FROM entrevistas LIMIT 50;") # Limitamos para probar
    datos = cur.fetchall()
    conn.close()
    return datos

def evaluar_entrevista(texto):
    # Recuperamos reglas relevantes para este texto
    docs_reglas = rules_retriever.invoke(texto)
    contexto_reglas = "\n".join([d.page_content for d in docs_reglas])

    prompt = ChatPromptTemplate.from_template("""
    Actúa como un Auditor de Calidad. Evalúa la siguiente entrevista basándote en estas reglas:
    {rules}
    
    ENTREVISTA:
    {text}
    
    Salida requerida solo en este formato:
    ESTADO: [APROBADA o RECHAZADA]
    MOTIVO: [Breve explicación de por qué, citando la regla específica]
    """)
    
    chain = prompt | llm
    return chain.invoke({"rules": contexto_reglas, "text": texto})

# === EJECUCIÓN ===
entrevistas = obtener_entrevistas()
print(f"🚀 Auditando {len(entrevistas)} entrevistas existentes...")

for id_ent, titulo, transcripcion in entrevistas:
    print(f"   Evaluando ID {id_ent}: {titulo[:30]}...")
    
    # El LLM genera la "Etiqueta"
    analisis = evaluar_entrevista(transcripcion).content
    
    # Creamos un documento que contiene el EJEMPLO + LA CRÍTICA
    contenido_didactico = f"""
    EJEMPLO DE ARCHIVO (ID: {id_ent})
    TITULO: {titulo}
    RESULTADO AUDITORÍA: {analisis}
    ---
    FRAGMENTO DEL TEXTO ORIGINAL:
    {transcripcion[:800]}...
    """
    
    doc = Document(page_content=contenido_didactico, metadata={"origen": "auditoria_interna"})
    feedback_vectorstore.add_documents([doc])

print("✅ Auditoría terminada. Los resultados están en './chroma_feedback_db'")