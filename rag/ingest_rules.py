import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from dotenv import load_dotenv

load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))

ruta_pdfs = os.path.join(base_dir,"..","Documentos","Documentos_US")

loader = DirectoryLoader(ruta_pdfs, glob="*.pdf", loader_cls=PyPDFLoader)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=200,
    separators=["\nArtículo", "\n\n", "\n", ". "]
)
splits = text_splitter.split_documents(docs)

embeddings = OllamaEmbeddings(model=os.getenv("MODEL"))

vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_documentos_us_db"
)

print("Base de datos de Documentos US creada correctamente.")