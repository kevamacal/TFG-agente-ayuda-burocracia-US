from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from templates.templates import (
    template_reformulacion,
    template_deteccion,
    template_respuesta,
    template_consulta,
    template_rechazo,
    template_procedimental,
    template_calendario,
    template_normativo,
    template_baremo,
    template_cuestiona_agente
)

from utils.config import format_docs, config_light_llm, config_llm
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
        
        retriever_base = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 12})
        cohere_reranker = CohereRerank(model="rerank-v4.0-pro" ,top_n=5)
        self.retriever = ContextualCompressionRetriever(
            base_compressor=cohere_reranker,
            base_retriever=retriever_base
        )
        
        self.chain_reformulacion = self._crear_cadena(template_reformulacion, self.light_llm)
        self.chain_deteccion = self._crear_cadena(template_deteccion, self.light_llm)
        self.chain_clasificacion = self._crear_cadena(template_respuesta, self.light_llm)
        self.chain_cuestiona_agente = self._crear_cadena(template_cuestiona_agente, self.light_llm)
        
        self.cadenas_respuesta = {
            "procedimental": self._crear_cadena(template_procedimental, self.llm),
            "calendario": self._crear_cadena(template_calendario, self.llm),
            "normativo": self._crear_cadena(template_normativo, self.llm),
            "baremo": self._crear_cadena(template_baremo, self.llm),
            "consulta": self._crear_cadena(template_consulta, self.light_llm),
            "rechazo": self._crear_cadena(template_rechazo, self.light_llm)
        }

    def _crear_cadena(self, funcion_template, llm_elegido):
        prompt = ChatPromptTemplate.from_template(funcion_template())
        return prompt | llm_elegido | StrOutputParser()

    def insertar_contexto(self, pregunta: str, historial_formateado: str):
        print("\n\nInsertando contexto...", datetime.datetime.now())        
        if historial_formateado:
            pregunta_busqueda = self.chain_reformulacion.invoke({
                "historial": historial_formateado,
                "question": pregunta
            })
        else:
            pregunta_busqueda = pregunta
        
        print("Buscando contexto...", datetime.datetime.now())
        contexto, referencias = self._buscar_contexto(pregunta_busqueda)
        print("Contexto insertado exitosamente", datetime.datetime.now())
        return pregunta_busqueda, contexto, referencias
        
    def _buscar_contexto(self, pregunta_reformulada: str):    
        docs = self.retriever.invoke(pregunta_reformulada)
        referencias = list(set([doc.metadata.get("source","Documento desconocido") for doc in docs]))
        return format_docs(docs), referencias
    
    def contiene_duda_burocratica(self, pregunta_reformulada: str, historial_formateado: str):
        return self.chain_deteccion.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
        }).strip().lower()
    
    def contiene_suficiente_informacion(self, pregunta_reformulada: str, historial_formateado: str, contexto: str):
        return self.chain_cuestiona_agente.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
            "context": contexto
        }).strip().lower()

    def clasificar_categoria(self, pregunta_reformulada: str, historial_formateado: str):
        return self.chain_clasificacion.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado
        }).strip().lower()
    
    def responder_consulta(self, contexto: str, historial_formateado: str, pregunta_reformulada: str, tipo_respuesta: str):
        inputs = {
            "context": contexto,
            "historial": historial_formateado,
            "question": pregunta_reformulada 
        }
        
        cadena_activa = self.cadenas_respuesta.get(tipo_respuesta, self.cadenas_respuesta["normativo"])
        
        return cadena_activa.stream(inputs)
    
asistenteRAG = AsistenteRAG()