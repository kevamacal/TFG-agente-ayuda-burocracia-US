from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

# Cargar la DB existente
embeddings = OllamaEmbeddings(model=os.getenv("MODEL"))
vectorstore = Chroma(persist_directory="./chroma_documentos_us_db", embedding_function=embeddings)

# Simular la búsqueda
query = "como anulo mi matricula"
print(f"🔎 Buscando: '{query}'")
docs = vectorstore.similarity_search(query, k=4)

print(f"\n✅ Se han encontrado {len(docs)} fragmentos relevantes:")
for i, doc in enumerate(docs):
    print(f"\n--- FRAGMENTO {i+1} (Fuente: {doc.metadata.get('source')} - Pág {doc.metadata.get('page')}) ---")
    print(doc.page_content[:300] + "...") # Imprimimos solo el principio