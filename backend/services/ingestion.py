import os
import sys
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Asegurarnos de que backend esté en el path (por si se ejecuta importando)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from langchain_text_splitters import MarkdownTextSplitter
from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores.utils import filter_complex_metadata
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from utils.config import settings
from langchain_core.documents import Document

# IMPORTACIÓN DE LA LIBRERÍA CLÁSICA
from llama_parse import LlamaParse

def extraer_texto_un_pdf(pdf_path: str, original_filename: str): 
    docs = []
    
    # 1. Inicializamos el parser
    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"), 
        result_type="markdown",
        system_prompt="""
        Estás procesando documentos burocráticos, académicos y normativos oficiales (universitarios). 
        Tu objetivo es extraer el contenido preservando meticulosamente la relación lógica entre los elementos.
        Sigue estas reglas estrictamente:
        1. TABLAS: Son críticas. Extrae todas las celdas, filas y columnas sin omitir texto. Si una celda tiene mucho texto o está combinada, plásmalo de forma que no se pierda nada de información en la conversión a Markdown.
        2. NOTAS Y ANEXOS: Si hay "Notas a pie de página", "Aclaraciones" o texto pequeño justo debajo de una tabla o sección, DEBES mantener ese texto inmediatamente después de la tabla/sección a la que hace referencia.
        3. JERARQUÍA: Respeta los encabezados (H1, H2, H3) y las listas enumeradas o con viñetas para que el contexto normativo quede claro.
        4. NO RESUMAS: Extrae el texto íntegramente, palabra por palabra.
        """
    )
    
    logger.info(f"Enviando a LlamaParse: {original_filename} (procesando en la nube...)")
    
    try:
        # Extraemos el resultado usando la API JSON para aislar meta tags "page"
        json_results = parser.get_json_result(pdf_path)
        
        for result in json_results:
            for page_data in result.get("pages", []):
                texto_pagina = page_data.get("md", "")
                num_pagina = page_data.get("page", 1)
                
                if not texto_pagina or not texto_pagina.strip():
                    continue
                
                doc = Document(
                    page_content=texto_pagina, 
                    metadata={
                        "source": original_filename,
                        "page": num_pagina 
                    }
                )
                docs.append(doc)
                
    except Exception as e:
        logger.exception(f"Error crítico procesando {original_filename}: {e}")
        raise e
                
    return docs

def procesar_un_pdf(filepath: str, original_filename: str, keep_file: bool = False):
    """
    Servicio de backend asíncrono para ingestar un único documento.
    """
    try:
        logger.info(f"=== Iniciando proceso para {original_filename} ===")
        
        # 1. Conexión a Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index("index-tfg")
        
        # 2. Extracción vía LlamaParse
        docs_completos = extraer_texto_un_pdf(filepath, original_filename)
        
        if not docs_completos:
            logger.warning(f"El documento {original_filename} estaba vacío o no se pudo extraer texto.")
            return
 

        # 3. Fragmentación (Text Splitter)
        logger.info(f"Fragmentando el Markdown de {original_filename}...")
        splitter = MarkdownTextSplitter(
            chunk_size=1500, 
            chunk_overlap=250
        )
        
        splits = splitter.split_documents(docs_completos)
        splits_limpios = filter_complex_metadata(splits)
        logger.info(f"Procesados {len(splits_limpios)} fragmentos listos para incrustar.")
        
        # 4. Generación de Embeddings y Subida a Pinecone
        logger.info("Generando Embeddings y subiendo a Pinecone...")
        embeddings = CohereEmbeddings(
            model="embed-multilingual-v3.0",
            cohere_api_key=settings.COHERE_API_KEY
        )
        vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=embeddings)
        
        batch_size = 100
        for i in range(0, len(splits_limpios), batch_size):
            lote = splits_limpios[i : i + batch_size]
            vectorstore.add_documents(lote)
            logger.info(f"Subidos {min(i + batch_size, len(splits_limpios))} de {len(splits_limpios)} fragmentos...")
            
        logger.info(f"✅ ¡Documento {original_filename} ingestado exitosamente!")

    except Exception as e:
        logger.exception(f"Error total durante el procesado: {e}")
    finally:
        # 5. Asegurarnos de limpiar basura residual en local pase lo que pase si no queremos conservarlo
        if not keep_file:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🧹 Archivo temporal local descartado: {filepath}")
            except Exception as cleanup_err:
                logger.warning(f"No se pudo eliminar el fichero {filepath}. Error: {cleanup_err}")

def eliminar_vectores_de_pdf(filename: str):
    """
    Elimina los vectores asociados a un archivo de Pinecone.
    """
    try:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index("index-tfg")
        # El filter de Pinecone depende del metadato. source es donde guardamos el nombre del archivo
        index.delete(filter={"source": {"$eq": filename}})
        logger.info(f"✅ Vectores de '{filename}' eliminados de Pinecone.")
        return True
    except Exception as e:
        logger.exception(f"Error eliminando vectores de {filename} de Pinecone: {e}")
        return False
