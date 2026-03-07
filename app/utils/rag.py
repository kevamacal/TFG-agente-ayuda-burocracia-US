from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from templates.templates import *
from classes.StateSchema import StateSchema 
from utils.config import format_docs, config_llm
from templates.templates import template_reformulacion
from langchain_pinecone import PineconeVectorStore
from utils.config import settings

class AsistenteRAG:
    def __init__(self):
        self.llm = config_llm()
        self.embeddings = HuggingFaceEndpointEmbeddings(model=settings.MODEL_EMBEDDINGS, huggingfacehub_api_token=settings.HUGGINGFACEHUB_API_KEY)
        self.vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=self.embeddings)
        self.retriever = self.vectorstore.as_retriever(search_type="mmr",search_kwargs={"k": 6})
        
    def insertar_contexto(self, state:StateSchema):
        pregunta = state["pregunta"]
        historial = state["historial"]

        if historial:
            historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
            prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion())
            rephrase_chain = prompt_reformulacion | self.llm | StrOutputParser()
            pregunta_busqueda = rephrase_chain.invoke({
                "historial": historial_formateado,
                "question": pregunta
            })
        else:
            pregunta_busqueda = pregunta
        
        docs = self.buscar_contexto(pregunta_busqueda)
        
        return {
            "historial_formateado": historial_formateado,
            "pregunta": pregunta,
            "contexto": docs,
            "pregunta_reformulada": pregunta_busqueda
        }
        
    def buscar_contexto(self, pregunta_reformulada):
        docs = self.retriever.invoke(pregunta_reformulada)
        return format_docs(docs)
    
    def contiene_duda_burocratica(self, pregunta, historial, contexto, pregunta_reformulada):
        historial_formateado = ""
        if historial:
            historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
        
        template = template_deteccion()
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        
        respuesta = chain.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
            "context": contexto
        })
        return respuesta.strip().lower()
    
asistente_rag = AsistenteRAG()