from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.config import config_llm, settings
from utils.rag import asistente_rag
from templates.templates import template_reformulacion, template_consulta
from classes.StateSchema import StateSchema

def consulta_usuario(state: StateSchema):
    pregunta_busqueda = state["pregunta_reformulada"]
    contexto = state["contexto"]
    historial_formateado = state["historial_formateado"]
    
    prompt_pregunta   = ChatPromptTemplate.from_template(template_consulta())
    generation_chain = prompt_pregunta | asistente_rag.llm | StrOutputParser()
    
    stream = generation_chain.stream({
        "context": contexto,
        "historial": historial_formateado,
        "question": pregunta_busqueda 
    })
    
    return {"stream": stream}