import os, sys
from langchain_text_splitters import MarkdownTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from config import settings
from langchain_core.documents import Document
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

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

pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index("index-tfg")

if not os.path.exists(settings.RUTA_PDFS):
    print(f"ERROR: No existe la carpeta {settings.RUTA_PDFS}")
    sys.exit(1)

print("Cargando PDFs...")
docs = extraer_texto_pdf(settings.RUTA_PDFS)

splitter = MarkdownTextSplitter(
    chunk_size=1200, 
    chunk_overlap=250,
)
splits = splitter.split_documents(docs)
splits_limpios = filter_complex_metadata(splits)
print(f"Procesados {len(splits_limpios)} fragmentos.")

print("Generando Embeddings")
embeddings = HuggingFaceEndpointEmbeddings(model=settings.MODEL_EMBEDDINGS, huggingfacehub_api_token=settings.HUGGINGFACEHUB_API_KEY)

vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=embeddings)

batch_size = 100
for i in range(0, len(splits_limpios), batch_size):
    lote = splits_limpios[i : i + batch_size]
    vectorstore.add_documents(lote)
    print(f"Subidos {min(i + batch_size, len(splits_limpios))} de {len(splits_limpios)} fragmentos...")

print("Base de datos creada exitosamente")