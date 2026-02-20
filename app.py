import streamlit as st
from rag_asistente_us import consultar_asistente

st.set_page_config(page_title="Asistente US", page_icon="🎓")

st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
st.title("🎓 Asistente de Burocracia US")
st.markdown("""
Bienvenido. Soy tu asistente virtual especializado en normativas de la Universidad de Sevilla.
Pregúntame sobre **matrículas, exámenes, convalidaciones o plazos**.
""")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Escribe tu duda aquí (ej: ¿Cómo anulo la matrícula?)")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Consultando la normativa vigente..."):
        respuesta_texto, fuentes = consultar_asistente(prompt)

    with st.chat_message("assistant"):
        st.markdown(respuesta_texto)
        
        with st.expander("📚 Fuentes consultadas (Transparencia)"):
            for fuente in fuentes:
                st.caption(f"📄 {fuente}")
    
    st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})