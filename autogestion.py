import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
import datetime
from pathlib import Path
import os

# Crear directorio de uploads si no existe
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Configuración de la página
st.set_page_config(
    page_title="Autogestión CAME",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de estilos
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de la base de datos
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            fecha_fundacion DATE,
            email TEXT,
            telefono TEXT,
            facebook TEXT,
            twitter TEXT,
            instagram TEXT,
            linkedin TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Funciones de autenticación
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return hash_obj.hex(), salt

def verify_password(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password_hash, salt FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        stored_hash, salt = result
        password_hash, _ = hash_password(password, salt)
        return password_hash == stored_hash
    return False

def register_user(username, password):
    password_hash, salt = hash_password(password)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)',
            (username, password_hash, salt)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_last_login(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(
        'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?',
        (username,)
    )
    conn.commit()
    conn.close()

# Funciones de manejo de datos
def load_data():
    try:
        file_path = 'datos_entidades.csv'
        
        if not os.path.exists(file_path):
            st.error(f"No se encontró el archivo {file_path}")
            return pd.DataFrame()

        # Intentar leer el archivo con diferentes configuraciones
        try:
            # Primero intentamos leer el archivo para ver su estructura
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                st.write("Encabezados encontrados:", first_line)
            
            # Intentar cargar con diferentes separadores
            separators = [',', ';', '\t']
            df = None
            
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, 
                                   encoding='utf-8', 
                                   sep=sep,
                                   error_bad_lines=False,  # Ignora líneas problemáticas
                                   warn_bad_lines=True)    # Avisa sobre líneas problemáticas
                    break
                except Exception as e:
                    continue
            
            if df is None:
                st.error("No se pudo leer el archivo con ningún separador conocido")
                return pd.DataFrame()

            # Mostrar información sobre las columnas encontradas
            st.write("Columnas encontradas en el archivo:", df.columns.tolist())
            
            # Mapeo de columnas
            columns_map = {
                'Entidad': 'nombre_entidad',
                'Sigla': 'sigla',
                'Fecha de Ingreso': 'fecha_ingreso',
                'Pertenece al CD 2024': 'consejo_directivo',
                'IGJ': 'igj',
                'AFIP': 'afip',
                'Estatuto': 'estatuto',
                'Nómina Actualizada': 'nomina',
                'Fecha de vencimiento - NÓMINA': 'vencimiento_nomina',
                'Presidente': 'presidente',
                'Fecha de vencimiento - PRESIDENTE': 'vencimiento_presidente',
                'CUIT': 'cuit',
                'Estado del CUIT': 'estado_cuit',
                'Provincia': 'provincia',
                'Localidad': 'localidad',
                'Dirección': 'direccion'
            }

            # Verificar qué columnas existen realmente en el archivo
            existing_columns = {}
            for old_col, new_col in columns_map.items():
                if old_col in df.columns:
                    existing_columns[old_col] = new_col
                elif old_col.strip() in df.columns:
                    existing_columns[old_col.strip()] = new_col

            # Mostrar mapeo de columnas para debug
            st.write("Mapeo de columnas:", existing_columns)

            # Renombrar las columnas que existen
            df = df.rename(columns=existing_columns)

            # Limpiar y formatear datos
            if 'consejo_directivo' in df.columns:
                df['consejo_directivo'] = df['consejo_directivo'].map({'SI': 'Si', 'NO': 'No'})
            if 'igj' in df.columns:
                df['igj'] = df['igj'].map({'SI': 'Si', 'NO': 'No'})
            if 'afip' in df.columns:
                df['afip'] = df['afip'].map({'SI': 'Si', 'NO': 'No'})
            if 'estatuto' in df.columns:
                df['estatuto'] = df['estatuto'].map({'SI': 'Si', 'NO': 'No'})
            
            # Convertir fechas
            date_columns = ['fecha_ingreso', 'vencimiento_nomina', 'vencimiento_presidente']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

            return df

        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error al cargar el archivo CSV: {str(e)}")
        return pd.DataFrame()

def get_entity_data(df, username):
    try:
        return df[df['nombre_entidad'] == username].iloc[0]
    except:
        return None

def save_file(uploaded_file, entity_name, file_type):
    if uploaded_file is not None:
        save_dir = Path(f"uploads/{entity_name}")
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Agregar timestamp al nombre del archivo
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.name.split('.')[-1]
        file_name = f"{file_type}_{timestamp}.{file_extension}"
        
        file_path = save_dir / file_name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Registrar la subida en un log
        log_path = save_dir / "uploads_log.txt"
        with open(log_path, "a") as log:
            log.write(f"{datetime.datetime.now()}: Subido {file_type} - {file_name}\n")
            
        return True
    return False

def get_user_info(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT fecha_fundacion, email, telefono, facebook, twitter, instagram, linkedin
        FROM users WHERE username = ?
    ''', (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'fecha_fundacion': result[0],
            'email': result[1],
            'telefono': result[2],
            'facebook': result[3],
            'twitter': result[4],
            'instagram': result[5],
            'linkedin': result[6]
        }
    return None

def update_user_info(username, info):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE users 
            SET fecha_fundacion = ?,
                email = ?,
                telefono = ?,
                facebook = ?,
                twitter = ?,
                instagram = ?,
                linkedin = ?
            WHERE username = ?
        ''', (
            info['fecha_fundacion'],
            info['email'],
            info['telefono'],
            info['facebook'],
            info['twitter'],
            info['instagram'],
            info['linkedin'],
            username
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user info: {str(e)}")
        return False
    finally:
        conn.close()

# Inicializar la base de datos
init_db()

# Inicializar estado de la sesión
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Sistema de Login/Registro
if not st.session_state.authenticated:
    st.title("Autogestión CAME")
    
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Primer Acceso"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Nombre de la entidad")
            password = st.text_input("Contraseña", type="password")
            submit_button = st.form_submit_button("Ingresar")
            
            if submit_button:
                df = load_data()
                if username in df['nombre_entidad'].values:
                    if verify_password(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        update_last_login(username)
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta")
                else:
                    st.error("Entidad no encontrada")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Nombre de la entidad")
            new_password = st.text_input("Contraseña", type="password")
            confirm_password = st.text_input("Confirmar contraseña", type="password")
            register_button = st.form_submit_button("Registrarse")
            
            if register_button:
                df = load_data()
                if new_username in df['nombre_entidad'].values:
                    if new_password == confirm_password:
                        if register_user(new_username, new_password):
                            st.success("Registro exitoso. Ya puedes iniciar sesión.")
                        else:
                            st.error("La entidad ya está registrada")
                    else:
                        st.error("Las contraseñas no coinciden")
                else:
                    st.error("Entidad no encontrada en nuestros registros")

# Pantalla principal
else:
    # Cargar datos
    df = load_data()
    entity_data = get_entity_data(df, st.session_state.username)
    user_info = get_user_info(st.session_state.username)
    
    if entity_data is None:
        st.error("Error al cargar los datos de la entidad")
        st.stop()
    
    # Sidebar con navegación
    st.sidebar.title("Menú")
    page = st.sidebar.radio("Ir a:", ["Perfil", "Consejos Directivos"])
    
    # Botón de cierre de sesión
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()
    
    if page == "Perfil":
        st.title("Perfil de la Entidad")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Información General")
            st.write(f"Nombre de la entidad: {entity_data['nombre_entidad']}")
            if pd.notna(entity_data['sigla']):
                st.write(f"Sigla: {entity_data['sigla']}")
            st.write(f"Fecha de ingreso: {entity_data['fecha_ingreso'].strftime('%d/%m/%Y')}")
            st.write(f"Dirección: {entity_data['direccion']}")
            st.write(f"Localidad: {entity_data['localidad']}")
            st.write(f"Provincia: {entity_data['provincia']}")
            st.write(f"Pertenece al Consejo Directivo: {entity_data['consejo_directivo']}")
            st.write(f"CUIT: {entity_data['cuit']}")
            st.write(f"Estado CUIT: {entity_data['estado_cuit']}")
            st.write(f"Presidente: {entity_data['presidente']}")
            
            if pd.notna(entity_data['vencimiento_presidente']):
                st.write(f"Vencimiento mandato presidente: {entity_data['vencimiento_presidente'].strftime('%d/%m/%Y')}")
            
            st.subheader("Estado de Documentación")
            
            # Nómina
            st.write("### Nómina")
            nomina_status = entity_data['nomina']
            st.write(f"Estado: {nomina_status}")
            if pd.notna(entity_data['vencimiento_nomina']):
                st.write(f"Fecha de vencimiento: {entity_data['vencimiento_nomina'].strftime('%d/%m/%Y')}")
            if nomina_status != "Vigente":
                nomina_file = st.file_uploader("Actualizar nómina", key="nomina")
                if nomina_file:
                    if save_file(nomina_file, entity_data['nombre_entidad'], "nomina"):
                        st.success("Nómina actualizada correctamente")
            
            # Estatuto
            st.write("### Estatuto")
            estatuto_status = "Enviado" if entity_data['estatuto'] == "Si" else "Pendiente"
            st.write(f"Estado: {estatuto_status}")
            if estatuto_status == "Pendiente":
                estatuto_file = st.file_uploader("Enviar estatuto", key="estatuto")
                if estatuto_file:
                    if save_file(estatuto_file, entity_data['nombre_entidad'], "estatuto"):
                        st.success("Estatuto enviado correctamente")
            
            # IGJ
            st.write("### IGJ")
            igj_status = "Enviado" if entity_data['igj'] == "Si" else "Pendiente"
            st.write(f"Estado: {igj_status}")
            if igj_status == "Pendiente":
                igj_file = st.file_uploader("Enviar IGJ", key="igj")
                if igj_file:
                    if save_file(igj_file, entity_data['nombre_entidad'], "igj"):
                        st.success("IGJ enviado correctamente")
            
           # AFIP
            st.write("### AFIP")
            afip_status = "Enviado" if entity_data['afip'] == "Si" else "Pendiente"
            st.write(f"Estado: {afip_status}")
            if afip_status == "Pendiente":
                afip_file = st.file_uploader("Enviar constancia AFIP", key="afip")
                if afip_file:
                    if save_file(afip_file, entity_data['nombre_entidad'], "afip"):
                        st.success("Constancia AFIP enviada correctamente")
        
        with col2:
            st.subheader("Editar Información")
            with st.form("update_info"):
                # Cargar datos existentes si están disponibles
                current_info = user_info or {}
                
                # Fecha de fundación
                fundacion = st.date_input(
                    "Fecha de fundación",
                    value=datetime.datetime.strptime(current_info.get('fecha_fundacion', '2000-01-01'), '%Y-%m-%d').date() 
                    if current_info.get('fecha_fundacion') 
                    else datetime.datetime.now().date()
                )
                
                # Información de contacto
                st.subheader("Información de Contacto")
                email = st.text_input("Email", value=current_info.get('email', ''))
                telefono = st.text_input("Teléfono", value=current_info.get('telefono', ''))
                
                # Redes sociales
                st.subheader("Redes Sociales")
                facebook = st.text_input("Facebook", value=current_info.get('facebook', ''))
                twitter = st.text_input("Twitter", value=current_info.get('twitter', ''))
                instagram = st.text_input("Instagram", value=current_info.get('instagram', ''))
                linkedin = st.text_input("LinkedIn", value=current_info.get('linkedin', ''))
                
                if st.form_submit_button("Actualizar información"):
                    new_info = {
                        'fecha_fundacion': fundacion.strftime('%Y-%m-%d'),
                        'email': email,
                        'telefono': telefono,
                        'facebook': facebook,
                        'twitter': twitter,
                        'instagram': instagram,
                        'linkedin': linkedin
                    }
                    if update_user_info(st.session_state.username, new_info):
                        st.success("Información actualizada correctamente")
                    else:
                        st.error("Error al actualizar la información")
    
    elif page == "Consejos Directivos":
        st.title("Próximos Consejos Directivos")
        
        # Crear tabs para diferentes tipos de información
        tab1, tab2 = st.tabs(["Próximas Reuniones", "Histórico"])
        
        with tab1:
            # Ejemplo de información de próximos consejos
            hay_info = False  # TODO: Implementar lógica real para verificar si hay información
            
            if hay_info:
                st.write("### Próxima reunión")
                st.write("Fecha: [Fecha]")
                st.write("Lugar: [Lugar]")
                st.write("Hora: [Hora]")
                
                # Botón de inscripción si está disponible
                if st.button("Inscribirse a la reunión"):
                    st.write("Redirigiendo al formulario de inscripción...")
            else:
                st.info("No hay información disponible sobre próximos consejos directivos")
        
        with tab2:
            st.write("### Reuniones anteriores")
            st.info("El histórico de reuniones estará disponible próximamente")