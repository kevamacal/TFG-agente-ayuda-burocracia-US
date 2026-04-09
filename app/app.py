import streamlit as st
import requests
import time
import os

st.set_page_config(page_title="Asistente US", page_icon="🎓")

API_URL = os.getenv("API_URL", "http://localhost:8000")

if "token" not in st.session_state:
    st.session_state.token = None
if "conversacion_id" not in st.session_state:
    st.session_state.conversacion_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def api_request(method, endpoint, data=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            return requests.get(url, headers=headers)
        elif method == "POST":
            return requests.post(url, headers=headers, json=data)
        elif method == "POST_FORM":
            return requests.post(url, headers=headers, data=data)
        elif method == "DELETE": 
            return requests.delete(url, headers=headers)
        elif method == "PUT":   
            return requests.put(url, headers=headers, json=data)
    except requests.exceptions.ConnectionError:
        st.error(f"Error de conexión: Asegúrate de que FastAPI está corriendo en {API_URL}")
        st.stop()

if not st.session_state.token:
    st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
    st.title("Asistente de Burocracia US")
    
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab1:
        email_login = st.text_input("Email", key="login_email")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar"):
            res = api_request("POST_FORM", "/login", data={"username": email_login, "password": password_login})
            if res and res.status_code == 200:
                st.session_state.token = res.json()["access_token"]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
                
    with tab2:
        email_reg = st.text_input("Email", key="reg_email")
        password_reg = st.text_input("Contraseña", type="password", key="reg_pass")
        if st.button("Registrarse"):
            res = api_request("POST", "/registro", data={"email": email_reg, "password": password_reg})
            if res and res.status_code == 201:
                st.success("Registro exitoso. Ya puedes iniciar sesión.")
            elif res and res.status_code == 400:
                st.error(res.json().get("detail", "El email ya está registrado"))
            else:
                st.error("Error al registrar el usuario")

else:
    with st.sidebar:
        st.title("Mis Conversaciones")
        if st.button("➕ Nuevo Chat", use_container_width=True):
            res = api_request("POST", "/conversaciones", data={"titulo": "Nueva conversación"})
            if res and res.status_code == 200:
                st.session_state.conversacion_id = res.json()["id"]
                st.session_state.messages = []
                st.rerun()
                
        res = api_request("GET", "/conversaciones")
        conversaciones = [] 
        if res and res.status_code == 200:
            conversaciones = res.json()
            for conv in conversaciones:
                prefix = "🟢" if st.session_state.conversacion_id == conv['id'] else "💬"
                if st.button(f"{prefix} {conv['titulo']}", key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.conversacion_id = conv['id']
                    res_msg = api_request("GET", f"/conversaciones/{conv['id']}/mensajes")
                    if res_msg and res_msg.status_code == 200:
                        st.session_state.messages = [{"role": m["rol"], "content": m["contenido"]} for m in res_msg.json()]
                    st.rerun()

        if st.session_state.conversacion_id:
            st.divider()
            st.markdown("#### ⚙️ Opciones del chat actual")
            
            titulo_actual = next((c['titulo'] for c in conversaciones if c['id'] == st.session_state.conversacion_id), "Chat")
            
            nuevo_titulo = st.text_input("Renombrar chat", value=titulo_actual, key="input_renombrar")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Guardar", use_container_width=True):
                    if nuevo_titulo != titulo_actual:
                        res_rename = api_request("PUT", f"/conversaciones/{st.session_state.conversacion_id}", data={"titulo": nuevo_titulo})
                        if res_rename and res_rename.status_code == 200:
                            st.rerun() 
            
            with col2:
                if st.button("🗑️ Eliminar", use_container_width=True, type="primary"):
                    res_del = api_request("DELETE", f"/conversaciones/{st.session_state.conversacion_id}")
                    if res_del and res_del.status_code == 200:
                        st.session_state.conversacion_id = None
                        st.session_state.messages = []
                        st.rerun()

        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.token = None
            st.session_state.conversacion_id = None
            st.session_state.messages = []
            st.rerun()  

    st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
    st.title("Asistente de Burocracia US")
    
    if not st.session_state.conversacion_id:
        st.info("👈 Selecciona o crea una conversación en el menú lateral para empezar.")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        prompt = st.chat_input("Escribe tu duda aquí (ej: ¿Cómo anulo la matrícula?)")
        
        if prompt:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Consultando la normativa vigente..."):
                    res = api_request("POST", f"/conversaciones/{st.session_state.conversacion_id}/chat", data={"pregunta": prompt})
                    
                    if res and res.status_code == 200:
                        data = res.json()
                        respuesta_completa = data["respuesta"]
                        
                        def stream_text():
                            for word in respuesta_completa.split(" "):
                                yield word + " "
                                time.sleep(0.04)
                                
                        st.write_stream(stream_text)
                        st.session_state.messages.append({"role": "assistant", "content": respuesta_completa})
                        st.rerun()
                        
                    else:
                        st.error("Error al comunicarse con el servidor FastAPI.")