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
                "Fecha_Raw": fecha_str,
                "Tipo": tipo,
                "Categoria": categoria,
                "Subcategoria": subcat,
                "Monto": float(monto),
                "Descripcion": desc
            })
            
        df = pd.DataFrame(datos)
        if not df.empty:
            df['Fecha_Raw'] = pd.to_datetime(df['Fecha_Raw'])
            df = df.sort_values(by='Fecha_Raw', ascending=True)
            df['Mes'] = df['Fecha_Raw'].dt.strftime('%m/%Y')
        return df
    except:
        return pd.DataFrame()

df_raw = cargar_datos()

# ==========================================
# 📋 FILTROS INTELIGENTES (SIDEBAR LIMPIO)
# ==========================================
st.sidebar.header("🎯 Filtros de Visualización")
st.sidebar.caption("💡 Si dejas un filtro vacío, se mostrarán TODOS los datos por defecto.")

if not df_raw.empty:
    meses_disp = df_raw['Mes'].unique()[::-1]
    mes_sel = st.sidebar.multiselect("Filtrar por Mes (MM/YYYY)", meses_disp, default=[])
    
    tipos_disp = df_raw['Tipo'].unique()
    tipo_sel = st.sidebar.multiselect("Filtrar por Tipo de Movimiento", tipos_disp, default=[])

    cat_disp = sorted(df_raw['Categoria'].unique())
    cat_sel = st.sidebar.multiselect("Filtrar por Categoría", cat_disp, default=[])

    subcat_disp = sorted(df_raw['Subcategoria'].unique())
    subcat_sel = st.sidebar.multiselect("Filtrar por Subcategoría", subcat_disp, default=[])

    df_filtrado = df_raw.copy()
    
    if mes_sel:
        df_filtrado = df_filtrado[df_filtrado['Mes'].isin(mes_sel)]
    if tipo_sel:
        df_filtrado = df_filtrado[df_filtrado['Tipo'].isin(tipo_sel)]
    if cat_sel:
        df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(cat_sel)]
    if subcat_sel:
        df_filtrado = df_filtrado[df_filtrado['Subcategoria'].isin(subcat_sel)]
else:
    df_filtrado = pd.DataFrame()

# ==========================================
# 📊 LÓGICA DE CÁLCULO
# ==========================================
st.title("🏦 Dashboard de Finanzas Personales")

if df_raw.empty:
    st.error("No se pudo cargar la información. Revisa la conexión con Notion.")
else:
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

    tab_general, tab_inversiones = st.tabs(["📊 Análisis Operativo", "🚀 Rendimiento Inversiones"])

    with tab_general:
        col_salidas, col_entradas = st.columns(2)
        
        with col_salidas:
            st.subheader("📅 Composición de Gastos por Mes")
            df_solo_gastos_mes = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
            
            if not df_solo_gastos_mes.empty:
                df_mes_sal = df_solo_gastos_mes.groupby(['Mes', 'Categoria'])['Monto'].sum().reset_index()
                fig_bar_sal = px.bar(
                    df_mes_sal, x="Mes", y="Monto", color="Categoria",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_bar_sal.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_sal.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Categorías")
                st.plotly_chart(fig_bar_sal, use_container_width=True)
            else:
                st.info("No hay gastos registrados en este periodo.")
            
        with col_entradas:
            st.subheader("📅 Composición de Ingresos por Mes")
            df_ingresos_mes = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']
            
            if not df_ingresos_mes.empty:
                # CORRECCIÓN: Agrupamos y coloreamos por 'Subcategoria' en lugar de 'Categoria'
                df_mes_ing = df_ingresos_mes.groupby(['Mes', 'Subcategoria'])['Monto'].sum().reset_index()
                fig_bar_ing = px.bar(
                    df_mes_ing, x="Mes", y="Monto", color="Subcategoria",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_bar_ing.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_ing.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Tipos de Ingreso")
                st.plotly_chart(fig_bar_ing, use_container_width=True)
            else:
                st.info("No hay ingresos registrados.")

        st.markdown("---")
        st.subheader("🔍 Desglose y Ranking de Gastos Operativos")
        df_solo_gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
        
        if not df_solo_gastos.empty:
            df_pareto_gastos = df_solo_gastos.groupby(['Categoria', 'Subcategoria'])['Monto'].sum().reset_index()
            df_pareto_gastos = df_pareto_gastos.sort_values(by="Monto", ascending=True)
            df_pareto_gastos['Cat_Sub'] = df_pareto_gastos['Categoria'] + " / " + df_pareto_gastos['Subcategoria']
            
            fig_gastos = px.bar(
                df_pareto_gastos, x="Monto", y="Cat_Sub", orientation="h",
                color="Categoria", text_auto='.2f', color_discrete_sequence=px.colors.qualitative.Dark24
            )
            fig_gastos.update_traces(hovertemplate="<b>Monto:</b> S/. %{x:,.2f}<extra></extra>")
            fig_gastos.update_layout(yaxis_title="", xaxis_title="Monto total gastado (S/.)", showlegend=False)
            st.plotly_chart(fig_gastos, use_container_width=True)
        else:
            st.info("No hay registros clasificados como 'Gasto' para mostrar el ranking.")

    with tab_inversiones:
        st.subheader("🚀 Análisis Detallado de Capital Invertido")
        df_inv = df_filtrado[df_filtrado['Tipo'] == 'Inversión']
        
        if df_inv.empty:
            st.info("No hay registros de 'Inversión' que coincidan con los filtros actuales.")
        else:
            df_inv['Activo_Especifico'] = df_inv.apply(
                lambda r: f"{r['Categoria']} {r['Subcategoria']}" if "Emprendimiento" in r['Categoria'] else r['Subcategoria'], 
                axis=1
            )
            
            col_inv_mes, col_inv_tipo = st.columns(2)
            
            with col_inv_mes:
                st.markdown("#### 📅 Ritmo de Inversión Mensual")
                df_inv_month = df_inv.groupby(['Mes'])['Monto'].sum().reset_index()
                fig_inv_cron = px.bar(
                    df_inv_month, x='Mes', y='Monto', text_auto='.2f',
                    title="Monto Total Inyectado por Mes", color_discrete_sequence=['#2b5c8f']
                )
                fig_inv_cron.update_traces(hovertemplate="<b>Total Invertido:</b> S/. %{y:,.2f}<extra></extra>")
                fig_inv_cron.update_layout(xaxis_title="Mes", yaxis_title="Total Invertido (S/.)")
                st.plotly_chart(fig_inv_cron, use_container_width=True)
            
            with col_inv_tipo:
                st.markdown("#### 📅 Composición de Inversiones por Mes")
                df_mes_inv = df_inv.groupby(['Mes', 'Activo_Especifico'])['Monto'].sum().reset_index()
                fig_bar_inv_comp = px.bar(
                    df_mes_inv, x="Mes", y="Monto", color="Activo_Especifico",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_bar_inv_comp.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_inv_comp.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Activos / Proyectos")
                st.plotly_chart(fig_bar_inv_comp, use_container_width=True)

            st.markdown("---")
            st.markdown("##### 📋 Historial Consolidado de Inversiones")
            st.dataframe(df_inv[['Fecha_Raw', 'Categoria', 'Subcategoria', 'Activo_Especifico', 'Monto', 'Descripcion']].rename(columns={'Fecha_Raw': 'Fecha'}), 
                         use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Detalle General de Movimientos Filtrados")
    df_tabla_visible = df_filtrado.copy()
    df_tabla_visible['Fecha'] = df_tabla_visible['Fecha_Raw'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_tabla_visible[['Fecha', 'Tipo', 'Categoria', 'Subcategoria', 'Monto', 'Descripcion']], 
                 use_container_width=True, hide_index=True)
