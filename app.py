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

# Estilo para mejorar legibilidad de las métricas
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
            df['Mes'] = df['Fecha'].dt.strftime('%Y-%m')
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
    mes_sel = st.sidebar.multiselect("Seleccionar Mes", meses_disp, default=meses_disp[:2] if len(meses_disp) > 1 else meses_disp)
    
    # Filtro de Tipo
    tipos_disp = df_raw['Tipo'].unique()
    tipo_sel = st.sidebar.multiselect("Tipo de Movimiento", tipos_disp, default=tipos_disp)

    # Aplicar Filtros Base
    df_filtrado = df_raw[df_raw['Mes'].isin(mes_sel) & df_raw['Tipo'].isin(tipo_sel)]
    
    # Filtros dinámicos de Categoría
    cat_disp = sorted(df_filtrado['Categoria'].unique())
    cat_sel = st.sidebar.multiselect("Categoría", cat_disp, default=cat_disp)
    
    df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(cat_sel)]
else:
    df_filtrado = pd.DataFrame()

# ==========================================
# 📊 LÓGICA DE CÁLCULO (SALDO NETO)
# ==========================================
st.title("🏦 Dashboard de Finanzas Personales")

if df_raw.empty:
    st.error("No se pudo cargar la información. Revisa la conexión con Notion o verifica tus columnas.")
else:
    # KPIs basados en la selección de la barra lateral
    ingresos = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']['Monto'].sum()
    inversiones = df_filtrado[df_filtrado['Tipo'] == 'Inversión']['Monto'].sum()
    saldo_neto = ingresos - gastos - inversiones

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Saldo Neto (Filtrado)", f"S/. {saldo_neto:,.2f}")
    m2.metric("📈 Ingresos", f"S/. {ingresos:,.2f}")
    m3.metric("📉 Gastos total", f"S/. {gastos:,.2f}")
    m4.metric("🧱 Inversiones", f"S/. {inversiones:,.2f}")

    st.markdown("---")

    # ==========================================
    # 📈 PESTAÑAS DE ANÁLISIS
    # ==========================================
    tab_general, tab_inversiones = st.tabs(["📊 Análisis Operativo", "🚀 Rendimiento Inversiones"])

    with tab_general:
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("📅 Distribución Mensual por Categoría")
            if not df_filtrado.empty:
                # Agrupamos por Mes, Categoría y Subcategoría
                df_mes_cat = df_filtrado.groupby(['Mes', 'Categoria', 'Subcategoria'])['Monto'].sum().reset_index()
                
                # Gráfico de barras apiladas por Mes y Categoría, con Subcategoría en el desglose (hover)
                fig_bar_mes = px.bar(
                    df_mes_cat, 
                    x="Mes", 
                    y="Monto", 
                    color="Categoria",
                    title="Montos por Mes y Categoría",
                    hover_data=["Subcategoria"],
                    barmode="stack",
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_bar_mes.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Categorías")
                st.plotly_chart(fig_bar_mes, use_container_width=True)
            else:
                st.info("No hay datos para los filtros seleccionados.")
            
        with col_b:
            st.subheader("🔍 Desglose de Gastos (Top Categorías y Subcategorías)")
            # Filtrar estrictamente Gastos para este gráfico analítico
            df_solo_gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
            
            if not df_solo_gastos.empty:
                # Agrupamos por Categoria y Subcategoria para ordenarlo jerárquicamente
                df_pareto_gastos = df_solo_gastos.groupby(['Categoria', 'Subcategoria'])['Monto'].sum().reset_index()
                df_pareto_gastos = df_pareto_gastos.sort_values(by="Monto", ascending=True) # Ascendente para que la barra más larga quede arriba en horizontal
                
                # Gráfico de barras horizontales mostrando Categoría + Subcategoría en el eje Y
                df_pareto_gastos['Cat_Sub'] = df_pareto_gastos['Categoria'] + " / " + df_pareto_gastos['Subcategoria']
                
                fig_gastos = px.bar(
                    df_pareto_gastos,
                    x="Monto",
                    y="Cat_Sub",
                    orientation="h",
                    color="Categoria",
                    text_auto='.2f',
                    title="Ranking de Gastos del Mayor al Menor",
                    color_discrete_sequence=px.colors.qualitative.Dark24
                )
                fig_gastos.update_layout(yaxis_title="", xaxis_title="Monto total gastado (S/.)", showlegend=False)
                st.plotly_chart(fig_gastos, use_container_width=True)
            else:
                st.info("No hay registros clasificados como 'Gasto' en los filtros seleccionados.")

    with tab_inversiones:
        st.subheader("Análisis Detallado de Inversiones")
        
        # Filtro exclusivo de Inversión extraído de la data cruda para no alterarse por filtros de Categorías de gasto
        df_inv = df_raw[df_raw['Tipo'] == 'Inversión']
        
        if df_inv.empty:
            st.info("No hay registros marcados como 'Inversión' en tu Notion para mostrar.")
        else:
            col_inv1, col_inv2 = st.columns([1, 2])
            
            with col_inv1:
                st.write("**Total acumulado por tipo de activo:**")
                df_inv_tot = df_inv.groupby('Subcategoria')['Monto'].sum().reset_index()
                st.dataframe(df_inv_tot, hide_index=True, use_container_width=True)
            
            with col_inv2:
                # Inversiones por Mes y Subcategoría (Acciones vs Emprendimientos)
                df_inv_month = df_inv.groupby(['Mes', 'Subcategoria'])['Monto'].sum().reset_index()
                fig_inv = px.bar(
                    df_inv_month, 
                    x='Mes', 
                    y='Monto', 
                    color='Subcategoria',
                    barmode='group', 
                    title="Inversiones Mensuales por Activo (Acciones vs Emprendimientos)",
                    text_auto='.2s', 
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig_inv, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Detalle de Movimientos Filtrados")
    st.dataframe(df_filtrado[['Fecha', 'Tipo', 'Categoria', 'Subcategoria', 'Monto', 'Descripcion']], 
                 use_container_width=True, hide_index=True)
