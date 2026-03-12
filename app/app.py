import streamlit as st
from agente.router import router
import datetime
import time 

st.set_page_config(page_title="Asistente US", page_icon="🎓")

st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
st.title("Asistente de Burocracia US")
st.markdown("""
Bienvenido. Soy tu asistente virtual especializado en normativas de la Universidad de Sevilla.
Pregúntame sobre **matrículas, exámenes, convalidaciones o plazos**.
""")

def generador_lento(stream_original):
    """
    Ralentiza ligeramente el stream para que Groq no lo imprima 
    de golpe y se vea el efecto 'máquina de escribir'.
    """
    for chunk in stream_original:
        yield chunk
        time.sleep(0.05) 

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Escribe tu duda aquí (ej: ¿Cómo anulo la matrícula?)")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        error_ocurrido = False
        
        with st.status("Consultando la normativa vigente...", expanded=False) as status:
            estado_inicial = {
                "pregunta": prompt, 
                "historial": st.session_state.messages, 
                "contexto": "", 
                "stream": None,
                "referencias":[]
            }
            
            try:
                estado_final = router.invoke(estado_inicial)
                print("Finalizada consulta", datetime.datetime.now(), "\n\n")
                
                stream = estado_final["stream"]
                referencias = estado_final.get("referencias", [])
                status.update(label="Normativa consultada", state="complete", expanded=False)
                
            except Exception as e:
                error_msg = str(e).lower()
                error_ocurrido = True
                if "429" in error_msg or "rate limit" in error_msg:
                    status.update(label="Servidores saturados", state="error", expanded=False)
                    st.error("⚠️ El sistema ha recibido demasiadas peticiones seguidas (Límite de API gratuito). Por favor, **espera 1 minuto** y vuelve a preguntar.")
                else:
                    status.update(label="Error en la consulta", state="error", expanded=False)
                    st.error(f"⚠️ Ocurrió un error inesperado al consultar la normativa: {e}")

        if not error_ocurrido:
            try:
                stream_visual = generador_lento(stream)
                respuesta_texto = st.write_stream(stream_visual)
                
                if referencias:
                    st.markdown("**Fuentes consultadas**")
                    referencias_md = "\n".join([f"- {ref}" for ref in referencias])
                    st.markdown(referencias_md)
                    
                    respuesta_texto += f"\n\n**Fuentes consultadas**\n\n{referencias_md}"
                    
                st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
                
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "rate limit" in error_msg:
                    st.error("⚠️ El sistema se saturó a mitad de la respuesta. Espera 1 minuto y reinténtalo.")
                else:
                    st.error(f"⚠️ Error al escribir la respuesta: {e}")