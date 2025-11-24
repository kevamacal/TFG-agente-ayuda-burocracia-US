import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

embedding_model_name = os.getenv("MODEL")
chat_model_name = "llama3.1"

embeddings = OllamaEmbeddings(model=embedding_model_name)
llm = ChatOllama(model=chat_model_name, temperature=0)

if not os.path.exists("./chroma_feedback_db") or not os.path.exists("./chroma_rules_db"):
    print("❌ Error: Faltan bases de datos.")
    print("- Asegúrate de tener './chroma_feedback_db' (tus entrevistas).")
    print("- Asegúrate de tener './chroma_rules_db' (ejecuta ingest_rules.py).")
    exit()

db_entrevistas = Chroma(persist_directory="./chroma_feedback_db", embedding_function=embeddings)
retriever_history = db_entrevistas.as_retriever(search_kwargs={"k": 2})
db_reglas = Chroma(persist_directory="./chroma_rules_db", embedding_function=embeddings)
retriever_rules = db_reglas.as_retriever(search_kwargs={"k": 4})
template = """
Eres un Editor Jefe estricto de la CNN. Tu trabajo es validar una NUEVA NOTICIA basándote en dos fuentes de información:
1. LA NORMATIVA: Las reglas de buenas prácticas que debemos seguir.
2. EL ARCHIVO: Ejemplos de nuestras entrevistas anteriores (para contexto de estilo, aunque la prioridad son las reglas).

---
CONTEXTO NORMATIVO (Reglas a cumplir):
{context_rules}

---
CONTEXTO DE ARCHIVO (Noticias similares previas):
{context_history}

---
NUEVA NOTICIA DEL USUARIO:
{input}

---
INSTRUCCIONES:
Analiza la "NUEVA NOTICIA".
Si incumple alguna norma del "CONTEXTO NORMATIVO", recházala y cita el texto exacto del error.
Usa el "CONTEXTO DE ARCHIVO" solo como referencia de estilo.
Si todo está bien, apruébala.

Respuesta:
"""

prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain_parallel = (
    RunnableParallel(
        {
            "context_rules": retriever_rules | format_docs,
            "context_history": retriever_history | format_docs,
            "input": RunnablePassthrough(),
        }
    )
    | prompt
    | llm
    | StrOutputParser()
)

print("\n🕵️  AGENTE HÍBRIDO LISTO (Reglas + Histórico).")
print("Pega tu noticia para validarla (o 'salir').")

# === FUNCIÓN PARA PEGAR VARIAS LÍNEAS ===
def input_multilinea(mensaje):
    print(f"{mensaje} (Escribe o pega tu texto. Para enviar, escribe 'FIN' en una línea nueva y pulsa Enter)")
    lineas = []
    while True:
        try:
            linea = input()
            # Si la línea es exactamente 'FIN' (o 'fin'), paramos
            if linea.strip().upper() == 'FIN':
                break
            lineas.append(linea)
        except EOFError:
            break
    return "\n".join(lineas)

# === BUCLE DE CHAT MEJORADO ===
while True:
    print("\n" + "="*40)
    # Usamos la nueva función en lugar de un simple input()
    query = input_multilinea("📝 Pega la noticia completa:")
    
    # Comprobamos si el usuario quiere salir
    if query.strip().lower() in ["salir", "exit", "chau", ""]:
        print("👋 ¡Hasta luego!")
        break
    
    print("\n🤖 Analizando texto completo...")
    try:
        response = rag_chain_parallel.invoke(query)
        print(f"\n📊 INFORME EDITORIAL:\n{response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")