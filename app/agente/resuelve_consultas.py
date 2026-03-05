from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.config import config_llm, format_docs
from utils.rag_asistente_us import insertar_contexto
from templates.templates import template_reformulacion, template_respuesta
from classes.StateSchema import StateSchema

def resuelve_consulta(state: StateSchema):
    pregunta = state["pregunta"]
    historial = state["historial"]
    contexto = state["contexto"]
    historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial[:-1]])
    
    llm = config_llm()
    prompt_reformulacion = ChatPromptTemplate.from_template(template_reformulacion())
    rephrase_chain = prompt_reformulacion | llm | StrOutputParser()
    
    prompt_respuesta = ChatPromptTemplate.from_template(template_respuesta())
    generation_chain = prompt_respuesta | llm | StrOutputParser()
    
    if historial_formateado.strip():
        pregunta_busqueda = rephrase_chain.invoke({
            "historial": historial_formateado,
            "question": pregunta
        })
    else:
        pregunta_busqueda = pregunta
    
    
    stream = generation_chain.stream({
        "context": contexto,
        "historial": historial_formateado,
        "question": pregunta_busqueda 
    })
    
    return {"stream": stream}