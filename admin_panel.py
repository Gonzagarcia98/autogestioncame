import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import secrets
from datetime import datetime
import plotly.express as px
import os

# Código de diagnóstico temporal
def check_database():
    try:
        # Verificar si el archivo existe
        if os.path.exists('users.db'):
            print("Base de datos encontrada")
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            
            # Verificar estructura
            c.execute("PRAGMA table_info(users)")
            structure = c.fetchall()
            print("Estructura de la tabla:", structure)
            
            # Verificar registros
            c.execute("SELECT * FROM users")
            records = c.fetchall()
            print(f"Registros encontrados: {len(records)}")
            for record in records:
                print(record)
            
            conn.close()
        else:
            print("No se encuentra el archivo users.db")
    except Exception as e:
        print(f"Error al verificar la base de datos: {e}")

# Ejecutar diagnóstico
check_database()


def admin_app():
    st.set_page_config(page_title="CAME - Panel Administrativo", layout="wide")
    
    # Verificar la existencia del archivo de base de datos
    db_path = 'users.db'
    if not os.path.exists(db_path):
        st.error(f"No se encuentra el archivo de base de datos: {db_path}")
        st.info("Archivos disponibles en el directorio:")
        st.write(os.listdir())
        return

    st.title("Panel de Administración CAME")
    
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
        conn = sqlite3.connect(db_path)
        try:
            # Mostrar todas las tablas
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = c.fetchall()
            st.write("Tablas en la base de datos:", tables)
            
            # Mostrar estructura de la tabla users
            st.write("Estructura de la tabla users:")
            c.execute("PRAGMA table_info(users);")
            st.table(pd.DataFrame(c.fetchall(), 
                                columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']))
            
            # Contar registros
            c.execute("SELECT COUNT(*) FROM users")
            count = c.fetchone()[0]
            st.write(f"Número total de registros: {count}")
            
            # Mostrar todos los registros con sus columnas
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
            st.write("Columnas disponibles:", columns)
            st.write("Datos encontrados:", data)
            
            if data:
                df = pd.DataFrame(data, columns=columns)
                
                # Formatear fechas
                for col in ['created_at', 'last_login']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y %H:%M')
                
                # Renombrar columnas para mejor visualización
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
                
                st.write("Datos en formato tabla:")
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Exportar a Excel
                if st.button("Exportar a Excel"):
                    df.to_excel("usuarios_came.xlsx", index=False)
                    st.success("Datos exportados a 'usuarios_came.xlsx'")
            else:
                st.warning("No se encontraron registros en la tabla")

        except Exception as e:
            st.error(f"Error detallado al acceder a la base de datos: {str(e)}")
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