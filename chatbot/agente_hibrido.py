import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

embedding_model_name = os.getenv("MODEL")
chat_model_name = "llama3.2"

embeddings = OllamaEmbeddings(model=embedding_model_name)
llm = ChatOllama(model=chat_model_name, temperature=0)

if not os.path.exists("./chroma_feedback_db") or not os.path.exists("./chroma_rules_db"):
    print("Error: Faltan bases de datos.")
    print("- Asegúrate de tener './chroma_feedback_db' (tus entrevistas).")
    print("- Asegúrate de tener './chroma_rules_db' (ejecuta ingest_rules.py).")
    exit()

db_entrevistas = Chroma(persist_directory="./chroma_feedback_db", embedding_function=embeddings)
retriever_history = db_entrevistas.as_retriever(search_kwargs={"k": 2})
db_reglas = Chroma(persist_directory="./chroma_rules_db", embedding_function=embeddings)
retriever_rules = db_reglas.as_retriever(search_kwargs={"k": 4})
template = """
Eres un Editor Jefe de Programas Informativos (Radio/Podcast). Tu trabajo es validar un GUIÓN O TRANSCRIPCIÓN basándote en:
1. LA NORMATIVA: Reglas de buenas prácticas (interacción, viveza, evitar "efecto email").
2. EL ARCHIVO: Segmentos emitidos anteriormente.

---
CONTEXTO NORMATIVO:
{context_rules}

---
CONTEXTO DE ARCHIVO (Segmentos similares):
{context_history}

---
TRANSCRIPCIÓN A EVALUAR:
{input}

---
INSTRUCCIONES:
Analiza el flujo del diálogo.
¿Suena natural y "vivo" como pide el Criterio 1?
¿Hay repreguntas reales o parece un cuestionario leído?
Si incumple las normas, RECHAZA y explica por qué.
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

print("AGENTE HÍBRIDO LISTO (Reglas + Histórico).")
print("Pega tu noticia para validarla (o 'salir').")
def input_multilinea(mensaje):
    print(f"{mensaje} (Escribe o pega tu texto. Para enviar, escribe 'FIN' en una línea nueva y pulsa Enter)")
    lineas = []
    while True:
        try:
            linea = input()
            if linea.strip().upper() == 'FIN':
                break
            lineas.append(linea)
        except EOFError:
            break
    return "\n".join(lineas)

while True:
    print("\n" + "="*40)
    query = input_multilinea("📝 Pega la noticia completa:")
    
    if query.strip().lower() in ["salir", "exit", ""]:
        print("👋 ¡Hasta luego!")
        break
    
    print("Analizando texto completo...")
    try:
        response = rag_chain_parallel.invoke(query)
        print(f"INFORME EDITORIAL:\n{response}") 
    except Exception as e:
        print(f"Error: {e}")