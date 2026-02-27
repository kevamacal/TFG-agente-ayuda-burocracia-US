import os
import shutil
import sys
from langchain_community.document_loaders import DirectoryLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_PDFS = os.getenv("RUTA_PDFS")
DB_PATH = os.getenv("DB_PATH")
MODEL_NAME = os.getenv("MODEL_EMBEDDINGS")

if not os.path.exists(RUTA_PDFS):
    print(f"ERROR: No existe la carpeta {RUTA_PDFS}")
    sys.exit(1)

if os.path.exists(DB_PATH):
    try:
        shutil.rmtree(DB_PATH)
        print("Base de datos antigua borrada.")
    except:
        pass

print("Cargando PDFs...")
loader = DirectoryLoader(
    RUTA_PDFS, 
    glob="*.pdf", 
    loader_cls=UnstructuredPDFLoader,
    loader_kwargs={
        "mode": "elements",
        "languages": ["spa"]
        } 
) 
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200, 
    chunk_overlap=250,
)
splits = splitter.split_documents(docs)
splits_limpios = filter_complex_metadata(splits)
print(f"Procesados {len(splits_limpios)} fragmentos.")

print("Generando Embeddings")
embeddings = OllamaEmbeddings(model=MODEL_NAME)

vectorstore = Chroma.from_documents(
    documents=splits_limpios,
    embedding=embeddings,
    persist_directory=DB_PATH
)
print("Base de datos creada")