import streamlit as st
from notion_client import Client
import pandas as pd
import plotly.express as px

# ==========================================
# 🔒 CONFIGURACIÓN SEGURA DE CREDENCIALES
# ==========================================
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

# Inicializar el cliente oficial de Notion
notion = Client(auth=NOTION_TOKEN)

st.set_page_config(page_title="Dashboard de Gastos Financieros", layout="wide")
st.title("📊 Control de Gastos Financieros")
st.markdown("Visualización en tiempo real de la data registrada desde el iPhone.")

# ==========================================
# 🔄 EXTRACCIÓN Y LIMPIEZA DE DATA
# ==========================================
@st.cache_data(ttl=60) # Refresca la data cada 60 segundos si se recarga la página
def cargar_datos_notion():
    try:
        # LLAMADA CORREGIDA: Sintaxis oficial estándar para consultar bases de datos
        response = notion.databases.query(database_id=DATABASE_ID)
        results = response.get("results", [])
        
        datos = []
        for row in results:
            props = row.get("properties", {})
            
            # Extraer Monto (Number)
            monto = props.get("Monto", {}).get("number", 0)
            monto = float(monto) if monto is not None else 0.0
            
            # Extraer Descripción / Texto (Rich Text)
            desc_list = props.get("Descripción", {}).get("rich_text", [])
            descripcion = desc_list[0].get("text", {}).get("content", "Sin descripción") if desc_list else "Sin descripción"
            
            # Extraer Fecha (Date)
            fecha_data = props.get("Fecha", {}).get("date", {})
            fecha = fecha_data.get("start", None) if fecha_data else None
            
            # Extraer Categoría (Select)
            categoria_data = props.get("Categoría", {}).get("select", {})
            categoria = categoria_data.get("name", "Sin Categoría") if categoria_data else "Sin Categoría"
            
            # Extraer Subcategoría (Select)
            subcat_data = props.get("Subcategoria", {}).get("select", {})
            subcategoria = subcat_data.get("name", "Sin Subcategoría") if subcat_data else "Sin Subcategoría"
            
            # Extraer Tarjeta / Medio de Pago (Select)
            tarjeta_data = props.get("Tarjeta", {}).get("select", {})
            tarjeta = tarjeta_data.get("name", "No especificado") if tarjeta_data else "No especificado"
            
            datos.append({
                "Fecha": fecha,
                "Descripción": descripcion,
                "Categoría": categoria,
                "Subcategoría": subcategoria,
                "Tarjeta": tarjeta,
                "Monto": monto
            })
            
        df = pd.DataFrame(datos)
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            df = df.sort_values(by="Fecha", ascending=False)
        return df

    except Exception as e:
        st.error(f"Error al conectar con la API de Notion: {e}")
        return pd.DataFrame()

# Cargar el DataFrame procesado
df_gastos = cargar_datos_notion()

# ==========================================
# 📈 RENDERIZADO DEL DASHBOARD
# ==========================================
if df_gastos.empty:
    st.warning("No se encontraron registros. Verifica que tu base de datos en Notion tenga filas con información y que las columnas se llamen exactamente: Monto, Descripción, Fecha, Categoría, Subcategoria y Tarjeta.")
else:
    # 1. Indicadores clave (Métricas)
    total_gastado = df_gastos["Monto"].sum()
    num_transacciones = len(df_gastos)
    
    col1, col2 = st.columns(2)
    col1.metric(label="💰 Total Gastado", value=f"S/. {total_gastado:,.2f}")
    col2.metric(label="🧾 Número de Registros", value=num_transacciones)
    
    st.markdown("---")
    
    # 2. Gráficos Distribución (Dos columnas)
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("Gastos por Macro-Categoría")
        df_cat = df_gastos.groupby("Categoría")["Monto"].sum().reset_index()
        fig_pie = px.pie(df_cat, values="Monto", names="Categoría", 
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_graf2:
        st.subheader("Distribución por Método de Pago / Tarjeta")
        df_tarjeta = df_gastos.groupby("Tarjeta")["Monto"].sum().reset_index()
        fig_bar_tarjeta = px.bar(df_tarjeta, x="Tarjeta", y="Monto", 
                                 text_auto='.2f', color="Tarjeta",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_bar_tarjeta, use_container_width=True)
        
    st.markdown("---")
    
    # 3. Vista de Subcategorías detallada
    st.subheader("🔍 Desglose profundo por Subcategoría")
    df_sub = df_gastos.groupby(["Categoría", "Subcategoría"])["Monto"].sum().reset_index()
    fig_sun = px.sunburst(df_sub, path=["Categoría", "Subcategoría"], values="Monto",
                          color="Monto", color_continuous_scale="RdBu_r")
    st.plotly_chart(fig_sun, use_container_width=True)

    st.markdown("---")

    # 4. Tabla de últimos movimientos
    st.subheader("📋 Últimos movimientos registrados")
    df_mostrar = df_gastos.copy()
    # Evitar problemas si hay fechas nulas antes de formatear
    df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%Y-%m-%d').fillna("Sin Fecha")
    st.dataframe(df_mostrar, use_container_width=True)
