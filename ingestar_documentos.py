import os
import shutil
import sys
from langchain_community.document_loaders import PyMuPDFLoader, DirectoryLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_PDFS = os.path.join(BASE_DIR, "Documentos_US")
RUTA_DB = os.path.join(BASE_DIR, "chroma_documentos_us_db")

if not os.path.exists(RUTA_PDFS):
    print(f"ERROR: No existe la carpeta {RUTA_PDFS}")
    sys.exit(1)

if os.path.exists(RUTA_DB):
    try:
        shutil.rmtree(RUTA_DB)
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
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

vectorstore = Chroma.from_documents(
    documents=splits_limpios,
    embedding=embeddings,
    persist_directory=RUTA_DB
)
print("Base de datos creada")