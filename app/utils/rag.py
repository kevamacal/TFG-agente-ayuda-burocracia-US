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
        self.prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion())
        self.chain_reformulacion = self.prompt_reformulacion | self.llm | StrOutputParser()
        self.prompt_deteccion = ChatPromptTemplate.from_template(template_deteccion())
        self.chain_deteccion = self.prompt_deteccion | self.llm | StrOutputParser()
        self.prompt_respuesta = ChatPromptTemplate.from_template(template_respuesta())
        self.chain_respuesta = self.prompt_respuesta | self.llm | StrOutputParser()
        self.prompt_consulta = ChatPromptTemplate.from_template(template_consulta())
        self.chain_consulta = self.prompt_consulta | self.llm | StrOutputParser()
        self.prompt_rechazo = ChatPromptTemplate.from_template(template_rechazo())
        self.chain_rechazo = self.prompt_rechazo | self.llm | StrOutputParser()
        
    def insertar_contexto(self, state:StateSchema):
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
                "historial": state["historial_formateado"],
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