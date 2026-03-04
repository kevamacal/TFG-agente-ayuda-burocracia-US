from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.config import config_llm, format_docs
from utils.rag_asistente_us import obtener_rag
from templates.templates import template_reformulacion, template_respuesta

def resuelve_consulta(pregunta, historial_mensajes):
    historial_formateado = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historial_mensajes[:-1]])
    
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
        
    retriever = obtener_rag()
    docs = retriever.invoke(pregunta_busqueda)
    contexto_texto = format_docs(docs)
    print("Contexto obtenido para la pregunta:", contexto_texto)
    
    stream = generation_chain.stream({
        "context": contexto_texto,
        "historial": historial_formateado,
        "question": pregunta_busqueda 
    })
    
    # 5. Formatear fuentes
    fuentes_raw = [f"{doc.metadata.get('source', 'Desconocido')} (Pág {doc.metadata.get('page', '?')})" for doc in docs]
    fuentes = list(sorted(set(fuentes_raw)))
    
    return stream, fuentes