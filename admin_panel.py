import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime
import plotly.express as px
import os

# Función de diagnóstico de bases de datos
def check_all_databases():
    st.subheader("Diagnóstico de Bases de Datos")
    databases = ['users.db', 'came_database']
    
    for db_name in databases:
        st.write(f"\n--- Verificando {db_name} ---")
        try:
            if os.path.exists(db_name):
                conn = sqlite3.connect(db_name)
                c = conn.cursor()
                
                # Listar todas las tablas
                c.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = c.fetchall()
                st.write(f"Tablas encontradas en {db_name}:", tables)
                
                # Para cada tabla, mostrar su contenido
                for table in tables:
                    table_name = table[0]
                    st.write(f"\nContenido de la tabla {table_name}:")
                    
                    # Obtener estructura de la tabla
                    c.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in c.fetchall()]
                    
                    # Obtener datos
                    c.execute(f"SELECT * FROM {table_name}")
                    records = c.fetchall()
                    
                    if records:
                        df = pd.DataFrame(records, columns=columns)
                        st.dataframe(df)
                    else:
                        st.write("Tabla vacía")
                
                conn.close()
            else:
                st.write(f"No se encuentra el archivo {db_name}")
        except Exception as e:
            st.write(f"Error al verificar {db_name}: {str(e)}")

def admin_app():
    st.set_page_config(page_title="CAME - Panel Administrativo", layout="wide")
    
    st.title("Panel de Administración CAME")
    
    # Ejecutar diagnóstico de bases de datos
    check_all_databases()
    
    # Determinar qué base de datos usar
    db_path = 'came_database' if os.path.exists('came_database') else 'users.db'
    
    # Menú lateral
    st.sidebar.title("Menú")
    page = st.sidebar.selectbox(
        "Seleccionar página",
        ["Usuarios", "Gestión de Usuarios", "Estadísticas"]
    )
    
    # Página de Usuarios
    if page == "Usuarios":
        st.header("Lista de Usuarios Registrados")
        
        conn = sqlite3.connect(db_path)
        try:
            c = conn.cursor()
            
            # Mostrar estructura de la tabla users
            st.write("Estructura de la tabla users:")
            c.execute("PRAGMA table_info(users);")
            st.table(pd.DataFrame(c.fetchall(), 
                                columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']))
            
            # Contar registros
            c.execute("SELECT COUNT(*) FROM users")
            count = c.fetchone()[0]
            st.write(f"Número total de registros: {count}")
            
            # Mostrar todos los registros
            c.execute("""
                SELECT 
                    username,
                    created_at,
                    last_login,
                    email,
                    telefono,
                    fecha_fundacion
                FROM users
                ORDER BY created_at DESC
            """)
            columns = [description[0] for description in c.description]
            data = c.fetchall()
            
            if data:
                df = pd.DataFrame(data, columns=columns)
                
                # Formatear fechas
                for col in ['created_at', 'last_login']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y %H:%M')
                
                # Renombrar columnas
                column_names = {
                    'username': 'Nombre de Entidad',
                    'created_at': 'Fecha de Registro',
                    'last_login': 'Último Acceso',
                    'email': 'Email',
                    'telefono': 'Teléfono',
                    'fecha_fundacion': 'Fecha de Fundación'
                }
                df = df.rename(columns=column_names)
                
                # Filtro de búsqueda
                search_term = st.text_input("Buscar por nombre de entidad")
                if search_term:
                    df = df[df['Nombre de Entidad'].str.contains(search_term, case=False, na=False)]
                
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Exportar a Excel
                if st.button("Exportar a Excel"):
                    df.to_excel("usuarios_came.xlsx", index=False)
                    st.success("Datos exportados a 'usuarios_came.xlsx'")
            else:
                st.warning("No se encontraron registros en la tabla")

        except Exception as e:
            st.error(f"Error al acceder a la base de datos: {str(e)}")
        finally:
            conn.close()
    
    # Página de Gestión de Usuarios
    elif page == "Gestión de Usuarios":
        st.header("Gestión de Usuarios")
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        try:
            # Obtener lista de usuarios
            c.execute("SELECT username FROM users ORDER BY created_at DESC")
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
        
        conn = sqlite3.connect(db_path)
        try:
            c = conn.cursor()
            
            # Total de usuarios
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