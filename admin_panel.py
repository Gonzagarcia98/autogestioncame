import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime
import plotly.express as px

def admin_app():
    st.set_page_config(page_title="CAME - Panel Administrativo", layout="wide")
    
    st.title("Panel de Administración CAME")
    
    # Función para conectar a la base de datos
    def get_db_connection():
        return sqlite3.connect('users.db')
    
    # Función para obtener todos los usuarios con su información
    def get_all_users_info():
        conn = get_db_connection()
        try:
            query = '''
            SELECT 
                username as "Nombre de Entidad",
                strftime('%d/%m/%Y %H:%M', created_at) as "Fecha de Registro",
                strftime('%d/%m/%Y %H:%M', last_login) as "Último Acceso",
                fecha_fundacion as "Fecha de Fundación",
                email as "Email",
                telefono as "Teléfono"
            FROM users
            ORDER BY created_at DESC
            '''
            df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            st.error(f"Error al obtener usuarios: {str(e)}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    # Función para obtener estadísticas
    def get_statistics():
        conn = get_db_connection()
        try:
            # Total de usuarios
            total_users = pd.read_sql_query('SELECT COUNT(*) as total FROM users', conn).iloc[0]['total']
            
            # Usuarios nuevos (últimos 30 días)
            new_users = pd.read_sql_query('''
                SELECT COUNT(*) as total 
                FROM users 
                WHERE created_at >= date('now', '-30 days')
            ''', conn).iloc[0]['total']
            
            # Usuarios activos (últimos 30 días)
            active_users = pd.read_sql_query('''
                SELECT COUNT(*) as total 
                FROM users 
                WHERE last_login >= date('now', '-30 days')
            ''', conn).iloc[0]['total']
            
            # Registros por mes
            monthly_data = pd.read_sql_query('''
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    COUNT(*) as count
                FROM users
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month
            ''', conn)
            
            return total_users, new_users, active_users, monthly_data
        except Exception as e:
            st.error(f"Error al obtener estadísticas: {str(e)}")
            return 0, 0, 0, pd.DataFrame()
        finally:
            conn.close()
    
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

    # Menú lateral
    st.sidebar.title("Menú")
    page = st.sidebar.selectbox(
        "Seleccionar página",
        ["Usuarios", "Gestión de Usuarios", "Estadísticas"]
    )
    
    # Página de Usuarios
    if page == "Usuarios":
        st.header("Lista de Usuarios Registrados")
        
        # Obtener datos
        df_users = get_all_users_info()
        
        if not df_users.empty:
            # Filtros
            search_term = st.text_input("Buscar por nombre de entidad")
            
            # Filtrar datos
            if search_term:
                filtered_df = df_users[df_users['Nombre de Entidad'].str.contains(search_term, case=False, na=False)]
            else:
                filtered_df = df_users
            
            # Mostrar datos
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Exportar datos
            if st.button("Exportar a Excel"):
                filtered_df.to_excel("usuarios_came.xlsx", index=False)
                st.success("Datos exportados a 'usuarios_came.xlsx'")
        else:
            st.info("No hay usuarios registrados en el sistema")
    
    # Página de Gestión de Usuarios
    elif page == "Gestión de Usuarios":
        st.header("Gestión de Usuarios")
        
        # Obtener lista de usuarios
        df_users = get_all_users_info()
        usuarios = df_users['Nombre de Entidad'].tolist() if not df_users.empty else []
        
        if usuarios:
            tab1, tab2 = st.tabs(["Resetear Contraseña", "Eliminar Usuario"])
            
            with tab1:
                st.subheader("Resetear Contraseña")
                reset_username = st.selectbox(
                    "Seleccionar usuario",
                    options=usuarios
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
                    options=usuarios,
                    key="delete_user"
                )
                
                st.warning("⚠️ Esta acción no se puede deshacer")
                confirm_delete = st.checkbox("Confirmo que quiero eliminar este usuario")
                
                if st.button("Eliminar Usuario") and confirm_delete:
                    if delete_user(delete_username):
                        st.success(f"Usuario {delete_username} eliminado correctamente")
                        st.rerun()
        else:
            st.info("No hay usuarios registrados en el sistema")
    
    # Página de Estadísticas
    elif page == "Estadísticas":
        st.header("Estadísticas del Sistema")
        
        # Obtener estadísticas
        total_users, new_users, active_users, monthly_data = get_statistics()
        
        # Mostrar métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de usuarios registrados", total_users)
        
        with col2:
            st.metric("Usuarios nuevos (últimos 30 días)", new_users)
        
        with col3:
            st.metric("Usuarios activos (últimos 30 días)", active_users)
        
        # Gráfico de registros por mes
        if not monthly_data.empty:
            st.subheader("Registros por mes")
            fig = px.bar(
                monthly_data,
                x='month',
                y='count',
                title='Registros mensuales',
                labels={'month': 'Mes', 'count': 'Cantidad de registros'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar estadísticas mensuales")

# Ejecutar la aplicación
admin_app()