import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import hashlib
from PIL import Image
import io

# Configuración inicial de la página
st.set_page_config(page_title="Autogestión CAME", layout="wide")

# Inicialización del estado de la sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None

# Inicialización de la base de datos
def init_db():
    conn = sqlite3.connect('came_database.db')
    c = conn.cursor()
    
    # Tabla de usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE,
                  password TEXT,
                  entity_name TEXT)''')
    
    # Tabla de datos de entidades
    c.execute('''CREATE TABLE IF NOT EXISTS entity_data
                 (entity_id INTEGER PRIMARY KEY,
                  foundation_date DATE,
                  email TEXT,
                  address TEXT,
                  phone TEXT,
                  social_media TEXT,
                  directiva_vencimiento DATE,
                  directiva_estado TEXT,
                  estatuto BLOB,
                  igj BLOB,
                  afip BLOB)''')
    
    # Tabla de consejos directivos
    c.execute('''CREATE TABLE IF NOT EXISTS consejos
                 (id INTEGER PRIMARY KEY,
                  fecha DATE,
                  lugar TEXT,
                  hora TEXT,
                  link_inscripcion TEXT)''')
    
    # Insertar usuario de prueba si no existe
    c.execute('SELECT * FROM users WHERE username=?', ('admin',))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password, entity_name) VALUES (?, ?, ?)',
                 ('admin', hash_password('admin'), 'Entidad de Prueba'))
    
    conn.commit()
    conn.close()

# Función para hash de contraseña
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Función de autenticación
def authenticate(username, password):
    conn = sqlite3.connect('came_database.db')
    c = conn.cursor()
    hashed_pw = hash_password(password)
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, hashed_pw))
    result = c.fetchone()
    conn.close()
    return result is not None

# Función para guardar archivos
def save_file(file, entity_id, file_type):
    if file is not None:
        conn = sqlite3.connect('came_database.db')
        c = conn.cursor()
        
        file_bytes = file.read()
        c.execute(f'UPDATE entity_data SET {file_type}=? WHERE entity_id=?', 
                 (sqlite3.Binary(file_bytes), entity_id))
        
        conn.commit()
        conn.close()

# Función para cerrar sesión
def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = None

# Inicialización de la base de datos
init_db()

# Título principal
st.title("Autogestión CAME")

# Sistema de login
if not st.session_state['logged_in']:
    with st.form("login_form"):
        st.subheader("Inicio de Sesión")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar")
        
        if submit:
            if authenticate(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success("Login exitoso!")
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
        
        st.info("Usuario de prueba: admin / Contraseña: admin")

# Contenido principal después del login
else:
    # Crear tabs para diferentes secciones
    tab1, tab2, tab3 = st.tabs(["Datos de la Entidad", "Documentación", "Consejos Directivos"])
    
    with tab1:
        st.header("Datos de la Entidad")
        
        # Formulario para datos básicos
        with st.form("entity_data_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                foundation_date = st.date_input("Fecha de Fundación")
                email = st.text_input("Email")
                address = st.text_input("Dirección")
            
            with col2:
                phone = st.text_input("Teléfono")
                social_media = st.text_input("Redes Sociales")
            
            if st.form_submit_button("Actualizar Datos"):
                # Aquí iría la lógica para actualizar en la base de datos
                st.success("Datos actualizados correctamente")
    
    with tab2:
        st.header("Documentación")
        
        # Sección de Comisión Directiva
        st.subheader("Comisión Directiva")
        directiva_status = "Vigente"  # Esto vendría de la base de datos
        st.info(f"Estado: {directiva_status}")
        
        # Sección de documentos
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Estatuto")
            estatuto_file = st.file_uploader("Subir Estatuto", type=['pdf'], key='estatuto')
            if estatuto_file:
                save_file(estatuto_file, 1, 'estatuto')
                st.success("Estatuto subido correctamente")
        
        with col2:
            st.subheader("IGJ")
            igj_file = st.file_uploader("Subir IGJ", type=['pdf'], key='igj')
            if igj_file:
                save_file(igj_file, 1, 'igj')
                st.success("IGJ subido correctamente")
        
        with col3:
            st.subheader("AFIP")
            afip_file = st.file_uploader("Subir AFIP", type=['pdf'], key='afip')
            if afip_file:
                save_file(afip_file, 1, 'afip')
                st.success("AFIP subido correctamente")
    
    with tab3:
        st.header("Próximos Consejos Directivos")
        
        # Ejemplo de consejo directivo
        with st.container():
            st.subheader("Próximo Consejo")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("Fecha: 15 de Noviembre 2024")
                st.write("Lugar: Sede Central")
            
            with col2:
                st.write("Hora: 14:00")
                st.button("Formulario de Inscripción", 
                         help="Haga click para ir al formulario de inscripción")
        
        # Si no hay consejos programados
        if False:  # Condición para cuando no hay consejos
            st.info("No hay información disponible sobre próximos consejos directivos")
    
    # Botón de logout en la barra lateral
    if st.sidebar.button("Cerrar Sesión"):
        logout()
        st.experimental_rerun()