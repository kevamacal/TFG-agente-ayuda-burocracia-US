import streamlit as st
import requests
import time
import os
import json
import datetime
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="Asistente US", page_icon="🎓")

API_URL = os.getenv("API_URL", "http://localhost:8000")
cookie_controller = CookieController()
TIEMPO_MAX_INACTIVIDAD_MINUTOS = 30

def logout(mensaje_razon=None):
    if mensaje_razon:
        st.warning(mensaje_razon)
        time.sleep(1.5)
        
    st.session_state.token = None
    st.session_state.conversacion_id = None
    st.session_state.messages = []
    st.session_state.is_admin = False
    
    for c in ["auth_token", "is_admin", "conversacion_id"]:
        try:
            cookie_controller.remove(c)
        except KeyError:
            pass
    
    time.sleep(0.5)
    st.rerun()

if "ultima_actividad" not in st.session_state:
    st.session_state.ultima_actividad = datetime.datetime.now()

def verificar_inactividad():
    if st.session_state.get("token"):
        ahora = datetime.datetime.now()
        tiempo_inactivo = (ahora - st.session_state.ultima_actividad).total_seconds() / 60
        
        if tiempo_inactivo > TIEMPO_MAX_INACTIVIDAD_MINUTOS:
            logout("Sesión cerrada por inactividad.")
        else:
            st.session_state.ultima_actividad = ahora

if "token" not in st.session_state:
    st.session_state.token = None
if "conversacion_id" not in st.session_state:
    st.session_state.conversacion_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

auth_token = cookie_controller.get("auth_token")
if auth_token and st.session_state.token is None:
    st.session_state.token = auth_token

conv_cookie = cookie_controller.get("conversacion_id")
if conv_cookie and st.session_state.conversacion_id is None:
    try:
        st.session_state.conversacion_id = int(conv_cookie)
    except ValueError:
        st.session_state.conversacion_id = conv_cookie

admin_cookie = cookie_controller.get("is_admin")
if admin_cookie and st.session_state.is_admin is False:
    st.session_state.is_admin = (admin_cookie == "true")

verificar_inactividad()

def inject_css():
    bg_color = "#000000"
    bg_sec = "#171A21"
    text_color = "#FFFFFF"
    expander_bg = "#1A1C24"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}

        h1, h2, h3, h4, h5, h6, p, span, div, label, li {{
            color: {text_color} !important;
        }}

        .stApp {{
            background-color: {bg_color};
        }}

        [data-testid="stSidebar"] {{
            background-color: {bg_sec} !important;
            border-right: 1px solid rgba(128, 128, 128, 0.1);
        }}

        [data-testid="stChatMessage"] {{
            animation: fadeInUp 0.4s ease-out forwards;
            background-color: transparent !important;
            padding: 1rem 0;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        [data-testid="stChatMessage"][data-baseweb="card"] {{ }}
        
        [data-testid="stChatMessage"]:has([data-testid="stMarkdownContainer"] p) {{}}
        
        .stChatMessage:nth-child(even) {{
        }}
        
        div.stButton > button {{
            border-radius: 6px;
            border: 1px solid rgba(128,128,128,0.2);
            transition: all 0.2s;
            font-weight: 500;
        }}
        div.stButton > button:hover {{
            background-color: #9D1C34;
            color: white !important;
            border-color: #9D1C34;
            transform: translateY(-1px);
        }}

        [data-testid="stChatInput"] {{
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,0.2);
            background-color: {bg_sec};
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        
        [data-testid="stExpander"] {{
            background-color: {expander_bg};
            border-radius: 8px;
            border: 1px solid rgba(128,128,128,0.1);
            margin-top: 10px;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def api_request(method, endpoint, data=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        response = None
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "POST_FORM":
            response = requests.post(url, headers=headers, data=data)
        elif method == "DELETE": 
            response = requests.delete(url, headers=headers)
        elif method == "PUT":   
            response = requests.put(url, headers=headers, json=data)
            
        if response is not None and response.status_code == 401:
            logout("Tu sesión ha caducado. Por favor, vuelve a iniciar sesión.")
            
        return response

    except requests.exceptions.ConnectionError:
        st.error(f"Error de conexión: Asegúrate de que FastAPI está corriendo en {API_URL}")
        st.stop()

if not st.session_state.token:
    inject_css()
    st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
    st.title("Asistente Académico")
    
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab1:
        email_login = st.text_input("Email", key="login_email")
        password_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar"):
            res = api_request("POST_FORM", "/login", data={"username": email_login, "password": password_login})
            if res and res.status_code == 200:
                token = res.json()["access_token"]
                is_admin = res.json().get("is_admin", False)
                st.session_state.token = token
                st.session_state.is_admin = is_admin
                cookie_controller.set("auth_token", token)
                cookie_controller.set("is_admin", "true" if is_admin else "false")
                time.sleep(0.5)
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
    inject_css()
    with st.sidebar:
        st.title("Conversaciones")
        if st.button("Nuevo Chat", use_container_width=True, type="primary"):
            res = api_request("POST", "/conversaciones", data={"titulo": "Nueva conversación"})
            if res and res.status_code == 200:
                st.session_state.conversacion_id = res.json()["id"]
                cookie_controller.set("conversacion_id", str(res.json()["id"]))
                st.session_state.messages = []
                st.rerun()
                
        res = api_request("GET", "/conversaciones")
        conversaciones = [] 
        if res and res.status_code == 200:
            conversaciones = res.json()
            for conv in conversaciones:
                prefix = "•" if st.session_state.conversacion_id == conv['id'] else ""
                if st.button(f"{prefix} {conv['titulo']}", key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.conversacion_id = conv['id']
                    cookie_controller.set("conversacion_id", str(conv['id']))
                    res_msg = api_request("GET", f"/conversaciones/{conv['id']}/mensajes")
                    if res_msg and res_msg.status_code == 200:
                        mensajes_parseados = []
                        for m in res_msg.json():
                            refs = []
                            if m.get("referencias"):
                                try:
                                    refs = json.loads(m["referencias"])
                                except:
                                    pass
                            mensajes_parseados.append({"role": m["rol"], "content": m["contenido"], "referencias": refs})
                        st.session_state.messages = mensajes_parseados
                    st.rerun()

        if st.session_state.conversacion_id:
            st.divider()
            st.markdown("#### Configuración de chat")
            
            titulo_actual = next((c['titulo'] for c in conversaciones if c['id'] == st.session_state.conversacion_id), "Chat")
            
            nuevo_titulo = st.text_input("Renombrar chat", value=titulo_actual, key="input_renombrar")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Aplicar cambios", use_container_width=True):
                    if nuevo_titulo != titulo_actual:
                        res_rename = api_request("PUT", f"/conversaciones/{st.session_state.conversacion_id}", data={"titulo": nuevo_titulo})
                        if res_rename and res_rename.status_code == 200:
                            st.rerun() 
            
            with col2:
                if st.button("Eliminar", use_container_width=True, type="primary"):
                    res_del = api_request("DELETE", f"/conversaciones/{st.session_state.conversacion_id}")
                    if res_del and res_del.status_code == 200:
                        st.session_state.conversacion_id = None
                        try:
                            cookie_controller.remove("conversacion_id")
                        except KeyError:
                            pass
                        st.session_state.messages = []
                        time.sleep(0.5)
                        st.rerun()

        if st.session_state.get("is_admin", False):
            st.divider()
            with st.expander("Gestión de conocimiento", expanded=False):
                st.info("Añade un documento PDF nuevo al repositorio del agente.")
                pdf_file = st.file_uploader("Documento PDF", type=["pdf"])
                if st.button("Procesar documento") and pdf_file:
                    with st.spinner("Integrando..."):
                        files = {"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")}
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        try:
                            resp = requests.post(f"{API_URL}/admin/ingestar", headers=headers, files=files)
                            if resp.status_code == 202:
                                st.toast(f"Documento encolado para procesado.", icon="✅")
                            else:
                                st.error("Error al añadir documento.")
                        except Exception as e:
                            st.error(f"Error de red: {e}")

        st.divider()
            
        if st.button("Cerrar Sesión", use_container_width=True):
            logout()

    st.image("https://www.uco.es/investigacion/proyectos/SEBASENet/images/thumb/Logo_US.png/655px-Logo_US.png", width=100)
    st.title("Asistente Académico")
    
    if not st.session_state.conversacion_id:
        st.info("Selecciona o crea una conversación en el menú lateral para empezar.")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                refs = message.get("referencias", [])
                if refs:
                    with st.expander("Fuentes y referencias consultadas"):
                        for r in refs:
                            st.markdown(f"- {r}")
        
        prompt = st.chat_input("Escribe tu duda aquí (ej: ¿Cómo anulo la matrícula?)")
        
        if prompt:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Consultando normativas..."):
                    res = api_request("POST", f"/conversaciones/{st.session_state.conversacion_id}/chat", data={"pregunta": prompt})
                    
                    if res and res.status_code == 200:
                        data = res.json()
                        respuesta_completa = data["respuesta"]
                        refs_nuevas = data.get("referencias", [])
                        
                        def stream_text():
                            for word in respuesta_completa.split(" "):
                                yield word + " "
                                time.sleep(0.015)
                                
                        st.write_stream(stream_text)
                        
                        if refs_nuevas:
                            with st.expander("Fuentes y referencias consultadas"):
                                for r in refs_nuevas:
                                    st.markdown(f"- {r}")
                                    
                        st.session_state.messages.append({"role": "assistant", "content": respuesta_completa, "referencias": refs_nuevas})
                        st.rerun()
                        
                    else:
                        st.error("Error al comunicarse con el servidor.")