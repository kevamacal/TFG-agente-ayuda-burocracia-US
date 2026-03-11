from dotenv import load_dotenv
import os
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

class Settings:
    def __init__(self):
        load_dotenv()
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.HUGGINGFACEHUB_API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")
        self.HUGGINGFACEHUB_MODEL = os.getenv("HUGGINGFACEHUB_MODEL")
        self.HUGGINGFACEHUB_LIGHT_MODEL = os.getenv("HUGGINGFACEHUB_LIGHT_MODEL")
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.MODEL_EMBEDDINGS = os.getenv("MODEL_EMBEDDINGS")
        self.RUTA_PDFS = self.BASE_DIR + os.getenv("RUTA_PDFS")
        self.COHERE_API_KEY = os.getenv("COHERE_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")


settings = Settings()

def config_light_llm():
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.1-8b-instant", 
        api_key=settings.GROQ_API_KEY,
        max_tokens=150 
    )
    return llm

def config_llm():
    llm = ChatGroq(
        temperature=0.1, 
        model_name="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY
    )
    return llm

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def extraer_texto_pdf(directorio): 
    docs = []
    opciones = PdfPipelineOptions()
    opciones.do_ocr = True   
    opciones.ocr_batch_size = 1
    opciones.layout_batch_size = 1
    opciones.table_batch_size = 1
    opciones.images_scale = 0.7
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=opciones
            )
        },
    )
    for pdf in os.listdir(directorio):
        if pdf.endswith(".pdf"):
            print(f"Procesando documento: {pdf} (esto puede tardar...)")
            docling_document = converter.convert(os.path.join(directorio, pdf)).document
            markdown = docling_document.export_to_markdown()
            doc = Document(page_content=markdown, metadata={"source": pdf})
            docs.append(doc)
    return docs