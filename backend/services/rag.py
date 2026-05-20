from langchain_cohere import CohereEmbeddings, CohereRerank
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from templates.templates import *

from utils.config import format_docs, config_classifier_llm, config_light_llm, config_llm
from langchain_pinecone import PineconeVectorStore
from utils.config import settings
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
import datetime

class AsistenteRAG:
    def __init__(self):
        self.llm = config_llm()
        self.light_llm = config_light_llm()
        self.classifier_llm = config_classifier_llm()
        self.embeddings = CohereEmbeddings(model="embed-multilingual-v3.0", cohere_api_key=settings.COHERE_API_KEY)
        self.vectorstore = PineconeVectorStore(index_name="index-tfg", embedding=self.embeddings)        
        
        retriever_base = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
        cohere_reranker = CohereRerank(model="rerank-v4.0-pro" ,top_n=4)
        self.retriever = ContextualCompressionRetriever(
            base_compressor=cohere_reranker,
            base_retriever=retriever_base
        )
        
        self.chain_reformulacion = self._crear_cadena(PROMPT_REFORMULACION, self.light_llm)
        # Cadenas de clasificación: solo devuelven 1 palabra → LLM ultra-ligero (max 15 tokens)
        self.chain_deteccion = self._crear_cadena(PROMPT_DETECCION, self.classifier_llm)
        self.chain_clasificacion = self._crear_cadena(PROMPT_CLASIFICADOR, self.classifier_llm)
        self.chain_cuestiona_agente = self._crear_cadena(PROMPT_CUESTIONA_AGENTE, self.classifier_llm)
        
        self.cadenas_respuesta = {
            "procedimental": self._crear_cadena(PROMPT_RESULTOR_PROCEDIMENTAL, self.llm),
            "calendario": self._crear_cadena(PROMPT_RESULTOR_CALENDARIO, self.llm),
            "normativo": self._crear_cadena(PROMPT_RESULTOR_NORMATIVO, self.llm),
            "baremo": self._crear_cadena(PROMPT_RESULTOR_BAREMO, self.llm),
            "consulta": self._crear_cadena(PROMPT_CONSULTA_USUARIO, self.light_llm),
            "rechazo": self._crear_cadena(PROMPT_RECHAZO_AMABLE, self.light_llm)
        }

    def _crear_cadena(self, prompt, llm_elegido):
        prompt = ChatPromptTemplate.from_template(prompt)
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
        t0 = datetime.datetime.now()
        query_embedding = self.embeddings.embed_query(pregunta_reformulada)
        t1 = datetime.datetime.now()
        print(f"  [TIMING] Cohere Embedding: {(t1-t0).total_seconds():.2f}s")
        
        docs_raw = self.vectorstore.similarity_search_by_vector(query_embedding, k=12)
        t2 = datetime.datetime.now()
        print(f"  [TIMING] Pinecone Search: {(t2-t1).total_seconds():.2f}s ({len(docs_raw)} docs)")
        
        docs = self.retriever.base_compressor.compress_documents(docs_raw, pregunta_reformulada)
        t3 = datetime.datetime.now()
        print(f"  [TIMING] Cohere Rerank: {(t3-t2).total_seconds():.2f}s ({len(docs)} docs)")
        print(f"  [TIMING] Total retrieval: {(t3-t0).total_seconds():.2f}s")
        
        referencias = list(set([
            f"{doc.metadata.get('source', 'Documento desconocido')} (Página {int(doc.metadata.get('page', 0))})" 
            for doc in docs
        ]))
        
        contextos_formateados = []
        for doc in docs:
            fuente = doc.metadata.get('source', 'Desconocido')
            pagina = int(doc.metadata.get('page', 0))
            texto = doc.page_content
            contextos_formateados.append(f"FUENTE: {fuente} | PÁGINA: {pagina}\n{texto}")
            
        contexto_final = "\n\n---\n\n".join(contextos_formateados)
        
        return contexto_final, referencias
    
    def decide_ruta_inicial(self, pregunta_reformulada: str, historial_formateado: str):
        decision = self.chain_deteccion.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
        }).strip().lower()
        if "rechazo_amable" in decision: return "rechazo_amable"
        if "recuperador" in decision: return "recuperador"
        return "recuperador"
    
    def contiene_suficiente_informacion(self, pregunta_reformulada: str, historial_formateado: str, contexto: str):
        contexto_reducido = contexto[:800] if len(contexto) > 800 else contexto
        decision = self.chain_cuestiona_agente.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado,
            "context": contexto_reducido
        }).strip().lower()
        if "resultor" in decision: return "resultor"
        if "entrevistador" in decision: return "entrevistador"
        return "resultor"

    def clasificar_categoria(self, pregunta_reformulada: str, historial_formateado: str):
        decision = self.chain_clasificacion.invoke({
            "question": pregunta_reformulada, 
            "historial": historial_formateado
        }).strip().lower()
        if "procedimental" in decision: return "procedimental"
        if "calendario" in decision: return "calendario"
        if "baremo" in decision: return "baremo"
        if "normativo" in decision: return "normativo"
        return "normativo"
    
    def responder_consulta(self, contexto: str, historial_formateado: str, pregunta_reformulada: str, tipo_respuesta: str):
        inputs = {
            "context": contexto,
            "historial": historial_formateado,
            "question": pregunta_reformulada 
        }
        
        cadena_activa = self.cadenas_respuesta.get(tipo_respuesta, self.cadenas_respuesta["normativo"])
        
        return cadena_activa.stream(inputs)
    
asistente_rag = AsistenteRAG()