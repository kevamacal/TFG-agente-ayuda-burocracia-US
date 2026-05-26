from langchain_cohere import CohereEmbeddings, CohereRerank
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from templates.templates import *
from pydantic import BaseModel, Field
import os
from utils.config import format_docs, config_classifier_llm, config_light_llm, config_llm
from langchain_pinecone import PineconeVectorStore
from utils.config import settings
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
import logging

logger = logging.getLogger(__name__)

class StreamWrapper:
    def __init__(self, generator):
        self.generator = generator

    def __repr__(self):
        return f"<StreamWrapper generator={self.generator}>"


class AnalisisInicial(BaseModel):
    intencion: str = Field(description="Categoría de intención: 'recuperador' para consultas académicas o 'rechazo_amable' para no relacionadas.")
    pregunta_reformulada: str = Field(description="Pregunta reformulada independiente que combina el historial de chat.")
    categoria: str = Field(description="Tipo de respuesta académica: 'procedimental', 'calendario', 'normativo', 'baremo' o 'ninguna' (si la intención es 'rechazo_amable').")

class AsistenteRAG:
    def __init__(self):
        # Inicializar callbacks globales de Langfuse si las credenciales están presentes
        self.callbacks = []
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            try:
                # Puente de compatibilidad para Langfuse v2.x con Langchain moderno
                import sys, types
                if 'langchain.callbacks' not in sys.modules:
                    langchain_callbacks_base = types.ModuleType('langchain.callbacks.base')
                    import langchain_core.callbacks.base
                    langchain_callbacks_base.BaseCallbackHandler = langchain_core.callbacks.base.BaseCallbackHandler
                    sys.modules['langchain.callbacks'] = types.ModuleType('langchain.callbacks')
                    sys.modules['langchain.callbacks.base'] = langchain_callbacks_base
                if 'langchain.schema.agent' not in sys.modules:
                    langchain_schema_agent = types.ModuleType('langchain.schema.agent')
                    import langchain_core.agents
                    langchain_schema_agent.AgentAction = langchain_core.agents.AgentAction
                    langchain_schema_agent.AgentFinish = langchain_core.agents.AgentFinish
                    sys.modules['langchain.schema'] = types.ModuleType('langchain.schema')
                    sys.modules['langchain.schema.agent'] = langchain_schema_agent
                if 'langchain.schema.document' not in sys.modules:
                    langchain_schema_document = types.ModuleType('langchain.schema.document')
                    import langchain_core.documents
                    langchain_schema_document.Document = langchain_core.documents.Document
                    sys.modules['langchain.schema.document'] = langchain_schema_document

                from langfuse.callback import CallbackHandler
                langfuse_handler = CallbackHandler(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
                )
                self.callbacks = [langfuse_handler]
                logger.info("Langfuse CallbackHandler inicializado globalmente en AsistenteRAG")
            except Exception as lf_err:
                logger.exception(f"Error al inicializar Langfuse globalmente en AsistenteRAG: {lf_err}")

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
        prompt_analisis = ChatPromptTemplate.from_template(PROMPT_ANALISIS_INICIAL)
        self.chain_analisis_inicial = prompt_analisis | self.light_llm.with_structured_output(AnalisisInicial)
        # Cadenas de clasificación: solo devuelven 1 palabra → LLM ultra-ligero (max 15 tokens)
        self.chain_cuestiona_agente = self._crear_cadena(PROMPT_CUESTIONA_AGENTE, self.classifier_llm)
        self.chain_evaluador = self._crear_cadena(PROMPT_EVALUADOR_RELEVANCIA, self.classifier_llm)
        
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

    def insertar_contexto(self, pregunta: str, historial_formateado: str, pregunta_reformulada_previa: str = None):
        if pregunta_reformulada_previa:
            pregunta_busqueda = pregunta_reformulada_previa
        elif historial_formateado:
            pregunta_busqueda = self.chain_reformulacion.invoke({
                "historial": historial_formateado,
                "question": pregunta
            }, config={"callbacks": self.callbacks})
        else:
            pregunta_busqueda = pregunta
        
        contexto, referencias = self._buscar_contexto(pregunta_busqueda)
        return pregunta_busqueda, contexto, referencias
        
    def _buscar_contexto(self, pregunta_reformulada: str):    
        query_embedding = self.embeddings.embed_query(pregunta_reformulada)
        
        # 1. Recuperar un conjunto mayor de candidatos densos (k=18)
        docs_raw = self.vectorstore.similarity_search_by_vector(query_embedding, k=18)
        
        # 2. Búsqueda Léxica (Sparse/Keyword) sobre los candidatos
        stopwords = {
            "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", 
            "en", "y", "o", "u", "para", "por", "con", "como", "que", "es", "son",
            "mi", "tu", "su", "mis", "tus", "sus", "sobre", "esta", "este", "estos", "estas"
        }
        palabras_clave = [
            w.lower().strip("?,.¡!¿()\"'") 
            for w in pregunta_reformulada.split() 
            if w.lower().strip("?,.¡!¿()\"'") not in stopwords and len(w) > 2
        ]
        
        scores_lexicos = []
        for doc in docs_raw:
            content_lower = doc.page_content.lower()
            score = 0
            for word in palabras_clave:
                score += content_lower.count(word)
            scores_lexicos.append((doc, score))
            
        docs_ordenados_lexico = [d[0] for d in sorted(scores_lexicos, key=lambda x: x[1], reverse=True)]
        
        # 3. Fusión por Reciprocal Rank Fusion (RRF)
        rrf_scores = []
        for idx, doc in enumerate(docs_raw):
            dense_rank = idx + 1
            lexico_rank = docs_ordenados_lexico.index(doc) + 1
            rrf_score = (1.0 / (60.0 + dense_rank)) + (1.0 / (60.0 + lexico_rank))
            rrf_scores.append((doc, rrf_score))
            
        docs_combinados = [item[0] for item in sorted(rrf_scores, key=lambda x: x[1], reverse=True)]
        docs_hibridos = docs_combinados[:12]
        
        # 4. Cohere Rerank sobre los candidatos híbridos
        docs = self.retriever.base_compressor.compress_documents(docs_hibridos, pregunta_reformulada)
        
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
    
    def contiene_suficiente_informacion(self, pregunta_reformulada: str, historial_formateado: str, contexto: str):
        if not contexto or not contexto.strip():
            logger.info("[EVALUATOR] Contexto vacío -> busqueda_web")
            return "busqueda_web"
            
        contexto_reducido = contexto[:1500] if len(contexto) > 1500 else contexto
        res = self.chain_evaluador.invoke({
            "question": pregunta_reformulada, 
            "context": contexto_reducido
        }, config={"callbacks": self.callbacks}).strip().lower()
        
        logger.info(f"[EVALUATOR] Relevancia evaluada: '{res}'")
        if "insuficiente" in res:
            return "busqueda_web"
        elif "suficiente" in res:
            return "resultor"
        elif "ambiguo" in res:
            decision_doble_pregunta = self.chain_cuestiona_agente.invoke({
                "historial": historial_formateado,
                "context": contexto_reducido,
                "question": pregunta_reformulada
            }, config={"callbacks":self.callbacks}).strip().lower()

            return "entrevistador" if "entrevistador" in decision_doble_pregunta else "resultor"
        else:
            return "busqueda_web"
    
    def responder_consulta(self, contexto: str, historial_formateado: str, pregunta_reformulada: str, tipo_respuesta: str):
        inputs = {
            "context": contexto,
            "historial": historial_formateado,
            "question": pregunta_reformulada 
        }
        
        cadena_activa = self.cadenas_respuesta.get(tipo_respuesta, self.cadenas_respuesta["normativo"])
        
        raw_stream = cadena_activa.stream(inputs, config={"callbacks": self.callbacks})
        return StreamWrapper(raw_stream)
    
asistente_rag = AsistenteRAG()