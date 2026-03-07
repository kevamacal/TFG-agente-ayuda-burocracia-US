import os, sys
from langchain_text_splitters import MarkdownTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from config import extraer_texto_pdf
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_PDFS = BASE_DIR + os.getenv("RUTA_PDFS")
MODEL_NAME = os.getenv("MODEL_EMBEDDINGS")
API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("index-tfg")

if not os.path.exists(RUTA_PDFS):
    print(f"ERROR: No existe la carpeta {RUTA_PDFS}")
    sys.exit(1)

print("Cargando PDFs...")
docs = extraer_texto_pdf(RUTA_PDFS)

splitter = MarkdownTextSplitter(
    chunk_size=1200, 
    chunk_overlap=250,
)
splits = splitter.split_documents(docs)
splits_limpios = filter_complex_metadata(splits)
print(f"Procesados {len(splits_limpios)} fragmentos.")

print("Generando Embeddings")
embeddings = HuggingFaceEndpointEmbeddings(model=MODEL_NAME, huggingfacehub_api_token=API_KEY)

vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=embeddings)

batch_size = 100
for i in range(0, len(splits_limpios), batch_size):
    lote = splits_limpios[i : i + batch_size]
    vectorstore.add_documents(lote)
    print(f"Subidos {min(i + batch_size, len(splits_limpios))} de {len(splits_limpios)} fragmentos...")

print("Base de datos creada exitosamente")