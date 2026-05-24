import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# ==========================================
# 🔒 CONFIGURACIÓN Y CREDENCIALES
# ==========================================
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

st.set_page_config(page_title="Gestión Financiera Pro", layout="wide")

# Estilo personalizado para las métricas
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🔄 EXTRACCIÓN DE DATOS
# ==========================================
def cargar_datos():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers)
        if response.status_code != 200:
            return pd.DataFrame()
            
        data = response.json()
        results = data.get("results", [])
        
        datos = []
        for row in results:
            props = row.get("properties", {})
            
            # Extraer campos (ajustados a tus nombres reales)
            monto = props.get("Monto", {}).get("number", 0) or 0
            tipo = props.get("Tipo", {}).get("select", {}).get("name", "Gasto")
            fecha_str = props.get("Fecha", {}).get("date", {}).get("start", None)
            categoria = props.get("Categoria", {}).get("select", {}).get("name", "Otros")
            subcat = props.get("Subcategoria", {}).get("select", {}).get("name", "General")
            descripcion = props.get("Descripcion", {}).get("rich_text", [])
            desc = descripcion[0].get("text", {}).get("content", "") if descripcion else ""

            datos.append({
                "Fecha": fecha_str,
                "Tipo": tipo,
                "Categoria": categoria,
                "Subcategoria": subcat,
                "Monto": float(monto),
                "Descripcion": desc
            })
            
        df = pd.DataFrame(datos)
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            # Crear columnas de tiempo para filtros
            df['Mes'] = df['Fecha'].dt.strftime('%Y-%m')
            df['Nombre_Mes'] = df['Fecha'].dt.strftime('%B %Y')
        return df
    except:
        return pd.DataFrame()

df_raw = cargar_datos()

# ==========================================
# 📋 FILTROS (SIDEBAR)
# ==========================================
st.sidebar.header("🎯 Filtros de Visualización")

if not df_raw.empty:
    # Filtro de Mes
    meses_disp = sorted(df_raw['Mes'].unique(), reverse=True)
    mes_sel = st.sidebar.multiselect("Seleccionar Mes", meses_disp, default=meses_disp[:1])
    
    # Filtro de Tipo
    tipos_disp = df_raw['Tipo'].unique()
    tipo_sel = st.sidebar.multiselect("Tipo de Movimiento", tipos_disp, default=tipos_disp)

    # Aplicar Filtros
    df_filtrado = df_raw[df_raw['Mes'].isin(mes_sel) & df_raw['Tipo'].isin(tipo_sel)]
    
    # Filtros dinámicos de Categoría y Subcategoría basados en lo anterior
    cat_disp = df_filtrado['Categoria'].unique()
    cat_sel = st.sidebar.multiselect("Categoría", cat_disp, default=cat_disp)
    
    df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(cat_sel)]
else:
    df_filtrado = pd.DataFrame()

# ==========================================
# 📊 LÓGICA DE CÁLCULO (SALDO NETO)
# ==========================================
st.title("🏦 Dashboard de Finanzas Personales")

if df_raw.empty:
    st.error("No se pudo cargar la información. Revisa la conexión con Notion.")
else:
    # Cálculos globales para métricas (basados en el filtro de mes seleccionado)
    # Importante: Ajustamos los nombres de 'Tipo' según lo que tengas en Notion
    ingresos = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']['Monto'].sum()
    inversiones = df_filtrado[df_filtrado['Tipo'] == 'Inversión']['Monto'].sum()
    saldo_neto = ingresos - gastos - inversiones

    # 1. KPIs Principales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Saldo Neto (Mes)", f"S/. {saldo_neto:,.2f}", delta_color="normal")
    m2.metric("📈 Ingresos", f"S/. {ingresos:,.2f}")
    m3.metric("📉 Gastos", f"S/. {gastos:,.2f}")
    m4.metric("🧱 Inversiones", f"S/. {inversiones:,.2f}")

    st.markdown("---")

    # 2. SECCIÓN DE ANÁLISIS POR PESTAÑAS
    tab_general, tab_inversiones = st.tabs(["📊 Análisis General", "🚀 Rendimiento Inversiones"])

    with tab_general:
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Distribución por Categoría")
            fig_cat = px.sunburst(df_filtrado, path=['Categoria', 'Subcategoria'], values='Monto',
                                 color='Monto', color_continuous_scale='Blues')
            st.plotly_chart(fig_cat, use_container_width=True)
            
        with col_b:
            st.subheader("Evolución Diaria de Gastos")
            df_daily = df_filtrado[df_filtrado['Tipo'] == 'Gasto'].groupby('Fecha')['Monto'].sum().reset_index()
            fig_line = px.line(df_daily, x='Fecha', y='Monto', markers=True, line_shape="spline")
            st.plotly_chart(fig_line, use_container_width=True)

    with tab_inversiones:
        st.subheader("Análisis Detallado de Inversiones")
        
        # Filtrar solo inversiones
        df_inv = df_raw[df_raw['Tipo'] == 'Inversión']
        
        if df_inv.empty:
            st.info("No hay registros marcados como 'Inversión' para mostrar.")
        else:
            col_inv1, col_inv2 = st.columns([1, 2])
            
            with col_inv1:
                st.write("**Total acumulado por activo:**")
                df_inv_tot = df_inv.groupby('Subcategoria')['Monto'].sum().reset_index()
                st.dataframe(df_inv_tot, hide_index=True)
            
            with col_inv2:
                # Inversiones por Mes y Subcategoría (Acciones vs Emprendimientos)
                df_inv_month = df_inv.groupby(['Mes', 'Subcategoria'])['Monto'].sum().reset_index()
                fig_inv = px.bar(df_inv_month, x='Mes', y='Monto', color='Subcategoria',
                                barmode='group', title="Inversiones Mensuales por Tipo",
                                text_auto='.2s', color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_inv, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Detalle de Movimientos Filtrados")
    st.dataframe(df_filtrado[['Fecha', 'Tipo', 'Categoria', 'Subcategoria', 'Monto', 'Descripcion']], 
                 use_container_width=True, hide_index=True)
