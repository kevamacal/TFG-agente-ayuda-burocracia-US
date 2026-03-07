from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.rag import asistente_rag
from templates.templates import template_respuesta
from classes.StateSchema import StateSchema

def resuelve_consulta(state: StateSchema):
    pregunta_busqueda = state["pregunta_reformulada"]
    contexto = state["contexto"]
    historial_formateado = state["historial_formateado"]
    
    prompt_respuesta = ChatPromptTemplate.from_template(template_respuesta())
    generation_chain = prompt_respuesta | asistente_rag.llm | StrOutputParser()
    
    stream = generation_chain.stream({
        "context": contexto,
        "historial": historial_formateado,
        "question": pregunta_busqueda 
    })
    
    return {"stream": stream}