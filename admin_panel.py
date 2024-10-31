import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime

def admin_app():
    st.set_page_config(page_title="CAME - Panel Administrativo", layout="wide")
    
    st.title("Panel de Administración CAME")
    
    # Función para conectar a la base de datos
    def get_db_connection():
        return sqlite3.connect('users.db')
    
    # Función para obtener todos los usuarios con su información
    def get_all_users_info():
        conn = get_db_connection()
        query = '''
        SELECT 
            username,
            created_at,
            last_login,
            fecha_fundacion,
            email,
            telefono,
            facebook,
            twitter,
            instagram,
            linkedin
        FROM users
        ORDER BY created_at DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    # Función para resetear contraseña
    def reset_password(username, new_password):
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            new_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        password_hash = hash_obj.hex()
        
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute(
                'UPDATE users SET password_hash = ?, salt = ? WHERE username = ?',
                (password_hash, salt, username)
            )
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error al resetear contraseña: {str(e)}")
            return False
        finally:
            conn.close()
    
    # Función para eliminar usuario
    def delete_user(username):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error al eliminar usuario: {str(e)}")
            return False
        finally:
            conn.close()

    # Cargar datos de usuarios
    df_users = get_all_users_info()
    
    # Menú lateral
    st.sidebar.title("Menú")
    page = st.sidebar.selectbox(
        "Seleccionar página",
        ["Usuarios", "Gestión de Usuarios", "Estadísticas"]
    )
    
    # Página de Usuarios
    if page == "Usuarios":
        st.header("Lista de Usuarios Registrados")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("Buscar por nombre de entidad")
        
        # Filtrar datos
        if search_term:
            filtered_df = df_users[df_users['username'].str.contains(search_term, case=False, na=False)]
        else:
            filtered_df = df_users
        
        # Mostrar datos
        if not filtered_df.empty:
            # Formatear fechas
            filtered_df['created_at'] = pd.to_datetime(filtered_df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
            filtered_df['last_login'] = pd.to_datetime(filtered_df['last_login']).dt.strftime('%d/%m/%Y %H:%M')
            
            st.dataframe(filtered_df, use_container_width=True)
            
            # Exportar datos
            if st.button("Exportar a Excel"):
                filtered_df.to_excel("usuarios_came.xlsx", index=False)
                st.success("Datos exportados a 'usuarios_came.xlsx'")
        else:
            st.info("No se encontraron usuarios")
    
    # Página de Gestión de Usuarios
    elif page == "Gestión de Usuarios":
        st.header("Gestión de Usuarios")
        
        tab1, tab2 = st.tabs(["Resetear Contraseña", "Eliminar Usuario"])
        
        with tab1:
            st.subheader("Resetear Contraseña")
            reset_username = st.selectbox(
                "Seleccionar usuario",
                options=df_users['username'].tolist()
            )
            new_password = st.text_input("Nueva contraseña", type="password")
            confirm_password = st.text_input("Confirmar contraseña", type="password")
            
            if st.button("Resetear Contraseña"):
                if new_password == confirm_password:
                    if reset_password(reset_username, new_password):
                        st.success(f"Contraseña reseteada para {reset_username}")
                else:
                    st.error("Las contraseñas no coinciden")
        
        with tab2:
            st.subheader("Eliminar Usuario")
            delete_username = st.selectbox(
                "Seleccionar usuario para eliminar",
                options=df_users['username'].tolist(),
                key="delete_user"
            )
            
            st.warning("⚠️ Esta acción no se puede deshacer")
            confirm_delete = st.checkbox("Confirmo que quiero eliminar este usuario")
            
            if st.button("Eliminar Usuario") and confirm_delete:
                if delete_user(delete_username):
                    st.success(f"Usuario {delete_username} eliminado correctamente")
                    st.rerun()
    
    # Página de Estadísticas
    elif page == "Estadísticas":
        st.header("Estadísticas del Sistema")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de usuarios registrados", len(df_users))
        
        with col2:
            # Usuarios nuevos (últimos 30 días)
            df_users['created_at'] = pd.to_datetime(df_users['created_at'])
            recent_users = df_users[df_users['created_at'] > pd.Timestamp.now() - pd.Timedelta(days=30)]
            st.metric("Usuarios nuevos (últimos 30 días)", len(recent_users))
        
        with col3:
            # Usuarios activos (último login en 30 días)
            df_users['last_login'] = pd.to_datetime(df_users['last_login'])
            active_users = df_users[df_users['last_login'] > pd.Timestamp.now() - pd.Timedelta(days=30)]
            st.metric("Usuarios activos (últimos 30 días)", len(active_users))
        
        # Gráfico de registros por mes
        st.subheader("Registros por mes")
        monthly_registrations = df_users.groupby(df_users['created_at'].dt.strftime('%Y-%m'))['username'].count()
        st.bar_chart(monthly_registrations)

if _name_ == "_main_":
    admin_app()