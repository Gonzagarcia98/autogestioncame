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

    # Menú lateral
    st.sidebar.title("Menú")
    page = st.sidebar.selectbox(
        "Seleccionar página",
        ["Usuarios", "Gestión de Usuarios", "Estadísticas"]
    )
    
    # Página de Usuarios
    if page == "Usuarios":
        st.header("Lista de Usuarios Registrados")
        
        # Diagnóstico de la base de datos
        conn = sqlite3.connect('users.db')
        try:
            # Mostrar todas las tablas en la base de datos
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = c.fetchall()
            st.write("Tablas en la base de datos:", tables)
            
            # Mostrar contenido directo de la tabla users
            c.execute("SELECT username, created_at, last_login, email, telefono FROM users")
            users_data = c.fetchall()
            
            if users_data:
                # Convertir los datos a DataFrame para mejor visualización
                df = pd.DataFrame(users_data, 
                                columns=['Nombre de Entidad', 'Fecha de Registro', 
                                        'Último Acceso', 'Email', 'Teléfono'])
                
                # Formatear fechas
                df['Fecha de Registro'] = pd.to_datetime(df['Fecha de Registro']).dt.strftime('%d/%m/%Y %H:%M')
                df['Último Acceso'] = pd.to_datetime(df['Último Acceso']).dt.strftime('%d/%m/%Y %H:%M')
                
                # Filtro de búsqueda
                search_term = st.text_input("Buscar por nombre de entidad")
                if search_term:
                    df = df[df['Nombre de Entidad'].str.contains(search_term, case=False, na=False)]
                
                # Mostrar DataFrame
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Botón de exportación
                if st.button("Exportar a Excel"):
                    df.to_excel("usuarios_came.xlsx", index=False)
                    st.success("Datos exportados a 'usuarios_came.xlsx'")
            else:
                st.warning("No se encontraron usuarios en la base de datos")
                
        except Exception as e:
            st.error(f"Error al acceder a la base de datos: {str(e)}")
        finally:
            conn.close()
    
    # Página de Gestión de Usuarios
    elif page == "Gestión de Usuarios":
        st.header("Gestión de Usuarios")
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        try:
            # Obtener lista de usuarios
            c.execute("SELECT username FROM users")
            usuarios = [row[0] for row in c.fetchall()]
            
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
                            salt = secrets.token_hex(16)
                            hash_obj = hashlib.pbkdf2_hmac(
                                'sha256',
                                new_password.encode('utf-8'),
                                salt.encode('utf-8'),
                                100000
                            )
                            password_hash = hash_obj.hex()
                            
                            c.execute(
                                'UPDATE users SET password_hash = ?, salt = ? WHERE username = ?',
                                (password_hash, salt, reset_username)
                            )
                            conn.commit()
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
                        c.execute('DELETE FROM users WHERE username = ?', (delete_username,))
                        conn.commit()
                        st.success(f"Usuario {delete_username} eliminado correctamente")
                        st.rerun()
            else:
                st.info("No hay usuarios registrados en el sistema")
                
        except Exception as e:
            st.error(f"Error en la gestión de usuarios: {str(e)}")
        finally:
            conn.close()
    
    # Página de Estadísticas
    elif page == "Estadísticas":
        st.header("Estadísticas del Sistema")
        
        conn = sqlite3.connect('users.db')
        try:
            # Total de usuarios
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            
            # Usuarios nuevos (últimos 30 días)
            c.execute("""
                SELECT COUNT(*) FROM users 
                WHERE created_at >= datetime('now', '-30 days')
            """)
            new_users = c.fetchone()[0]
            
            # Usuarios activos (últimos 30 días)
            c.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_login >= datetime('now', '-30 days')
            """)
            active_users = c.fetchone()[0]
            
            # Mostrar métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de usuarios", total_users)
            with col2:
                st.metric("Usuarios nuevos (30 días)", new_users)
            with col3:
                st.metric("Usuarios activos (30 días)", active_users)
            
            # Gráfico de registros por mes
            c.execute("""
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    COUNT(*) as count
                FROM users
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month
            """)
            monthly_data = pd.DataFrame(c.fetchall(), columns=['Mes', 'Cantidad'])
            
            if not monthly_data.empty:
                fig = px.bar(
                    monthly_data,
                    x='Mes',
                    y='Cantidad',
                    title='Registros mensuales'
                )
                st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error al generar estadísticas: {str(e)}")
        finally:
            conn.close()

# Ejecutar la aplicación
admin_app()