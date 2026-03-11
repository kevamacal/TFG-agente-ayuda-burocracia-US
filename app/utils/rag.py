from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from templates.templates import *
from classes.StateSchema import StateSchema 
from utils.config import format_docs, config_llm, config_light_llm
from templates.templates import template_reformulacion
from langchain_pinecone import PineconeVectorStore
from utils.config import settings
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
import datetime

class AsistenteRAG:
    def __init__(self):
        self.llm = config_llm()
        self.light_llm = config_light_llm()
        self.embeddings = HuggingFaceEndpointEmbeddings(model=settings.MODEL_EMBEDDINGS, huggingfacehub_api_token=settings.HUGGINGFACEHUB_API_KEY)
        self.vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=self.embeddings)        
        self.prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion())
        self.chain_reformulacion = self.prompt_reformulacion | self.light_llm | StrOutputParser()
        self.prompt_deteccion = ChatPromptTemplate.from_template(template_deteccion())
        self.chain_deteccion = self.prompt_deteccion | self.light_llm | StrOutputParser()
        self.prompt_respuesta = ChatPromptTemplate.from_template(template_respuesta())
        self.chain_respuesta = self.prompt_respuesta | self.llm | StrOutputParser()
        self.prompt_consulta = ChatPromptTemplate.from_template(template_consulta())
        self.chain_consulta = self.prompt_consulta | self.llm | StrOutputParser()
        self.prompt_rechazo = ChatPromptTemplate.from_template(template_rechazo())
        self.chain_rechazo = self.prompt_rechazo | self.llm | StrOutputParser()
        retriever_base = self.vectorstore.as_retriever(search_type="mmr",search_kwargs={"k": 20})
        cohere_reranker = CohereRerank(model="rerank-v4.0-pro" ,top_n=5)
        self.retriever = ContextualCompressionRetriever(
            base_compressor=cohere_reranker,
            base_retriever=retriever_base
        )
        
    def insertar_contexto(self, state:StateSchema):
        print("\n\nInsertando contexto...", datetime.datetime.now())
        pregunta = state["pregunta"]
        historial = state["historial"]
        historial_formateado = self._formatear_historial(historial)
        
        if historial:
            pregunta_busqueda = self.chain_reformulacion.invoke({
                "historial": historial_formateado,
                "question": pregunta
            })
        else:
            pregunta_busqueda = pregunta
        
        print("Buscando contexto...", datetime.datetime.now())
        contexto, referencias = self.buscar_contexto(pregunta_busqueda)
        print("Contexto insertado exitosamente", datetime.datetime.now())
        return {
            "historial_formateado": historial_formateado,
            "pregunta": pregunta,
            "contexto": contexto,
            "pregunta_reformulada": pregunta_busqueda,
            "referencias": referencias
        }
        
    def buscar_contexto(self, pregunta_reformulada):
        docs = self.retriever.invoke(pregunta_reformulada)
        referencias = list(set([doc.metadata.get("source","Documento desconocido") for doc in docs]))
        return format_docs(docs), referencias
    
    def contiene_duda_burocratica(self, pregunta, historial, contexto, pregunta_reformulada):
        historial_formateado = ""
        if historial:
            historial_formateado = self._formatear_historial(historial)
        
        respuesta = self.chain_deteccion.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
            "context": contexto
        })
        return respuesta.strip().lower()
    
    def responder_consulta(self, state: StateSchema, tipo_respuesta):
        inputs = {
                "context": state["contexto"],
                "historial": state["historial"],
                "question": state["pregunta_reformulada"] 
            }
        cadena_activa = None
        if tipo_respuesta == "consulta":    
            cadena_activa = self.chain_consulta
        elif tipo_respuesta == "respuesta":
            cadena_activa = self.chain_respuesta
        elif tipo_respuesta == "rechazo":
            cadena_activa = self.chain_rechazo
        
        return {"stream": cadena_activa.stream(inputs)}
    
    def _formatear_historial(self, historial):
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
    
asistente_rag = AsistenteRAG()