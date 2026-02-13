import os
import shutil
import sys
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
# CAMBIO CLAVE: Usamos HuggingFace en lugar de Ollama para embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings 
from dotenv import load_dotenv

load_dotenv()

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_PDFS = os.path.join(BASE_DIR, "Documentos", "Documentos_US")
RUTA_DB = os.path.join(BASE_DIR, "chroma_documentos_us_db")

# Comprobaciones básicas
if not os.path.exists(RUTA_PDFS):
    print(f"❌ ERROR: No existe la carpeta {RUTA_PDFS}")
    sys.exit(1)

# Limpieza
if os.path.exists(RUTA_DB):
    try:
        shutil.rmtree(RUTA_DB)
        print("🧹 Base de datos antigua borrada.")
    except:
        pass

# Ingesta
print("🚀 Cargando PDFs...")
loader = DirectoryLoader(RUTA_PDFS, glob="*.pdf", loader_cls=PyPDFLoader)
docs = loader.load()

# Chunking (Troceado)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=600, 
    chunk_overlap=150,
    separators=["\nArtículo", "\n\n", "\n", ". "]
)
splits = splitter.split_documents(docs)
print(f"   -> Procesados {len(splits)} fragmentos.")

# Embeddings Rápidos
print("🧠 Generando Embeddings (HuggingFace CPU)...")
# Este modelo es ligero, rápido y funciona genial en CPU
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory=RUTA_DB
)
print("✅ ¡ÉXITO! Base de datos creada rapidísimo.")