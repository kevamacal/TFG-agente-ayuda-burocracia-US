from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from classes.StateSchema import StateSchema
from utils.rag import asistente_rag
from templates.templates import template_rechazo

def rechazo_amable(state: StateSchema):
    pregunta_busqueda = state["pregunta_reformulada"]
    historial_formateado = state["historial_formateado"]
    contexto = state["contexto"]
    
    prompt_respuesta = ChatPromptTemplate.from_template(template_rechazo())
    generation_chain = prompt_respuesta | asistente_rag.llm | StrOutputParser()
    
    stream = generation_chain.stream({
        "context": contexto,
        "historial": historial_formateado,
        "question": pregunta_busqueda 
    })
    
    return {"stream": stream}