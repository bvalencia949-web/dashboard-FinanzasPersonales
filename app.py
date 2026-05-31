import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# ==========================================
# 🔒 CONFIGURACIÓN Y CREDENCIALES
# ==========================================
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

st.set_page_config(
    page_title="Gestión Financiera Pro", 
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS avanzados para un Look & Feel Premium
st.markdown("""
    <style>
    /* Estilización general del fondo y contenedores */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Tarjetas para Métricas */
    div[data-testid="stMetric"] {
        background-color: var(--background-secondary-color);
        padding: 20px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border: 1px solid rgba(128, 128, 128, 0.15);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] { 
        font-size: 32px !important; 
        font-weight: 700 !important;
    }
    
    /* Líneas divisorias estéticas */
    hr {
        margin: 2rem 0;
        border: 0;
        height: 1px;
        background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(128, 128, 128, 0.4), rgba(0, 0, 0, 0));
    }
    
    /* Personalización de pestañas (Tabs) */
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
    }
    
    /* Ajustes de títulos de gráficos */
    .graph-title {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 10px;
        color: var(--text-color);
    }
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
# 📋 FILTROS INTELIGENTES (SIDEBAR LIMPIO Y MODERNO)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/781/781831.png", width=60) # Icono sutil de finanzas
    st.title("Panel de Control")
    st.markdown("Filtra la información del ecosistema financiero.")
    st.markdown("---")
    
    if not df_raw.empty:
        meses_disp = df_raw['Mes'].unique()[::-1]
        mes_sel = st.multiselect("📅 Periodo (Mes)", meses_disp, default=[])
        
        tipos_disp = df_raw['Tipo'].unique()
        tipo_sel = st.multiselect("🔄 Tipo de Movimiento", tipos_disp, default=[])

        cat_disp = sorted(df_raw['Categoria'].unique())
        cat_sel = st.multiselect("📁 Categoría", cat_disp, default=[])

        subcat_disp = sorted(df_raw['Subcategoria'].unique())
        subcat_sel = st.multiselect("🏷️ Subcategoría", subcat_disp, default=[])

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
# 📊 LÓGICA DE CÁLCULO Y RENDERIZADO
# ==========================================
# Encabezado Principal Limpio
st.markdown("# 🏦 Control de Finanzas Personales")
st.markdown("Dashboard operativo de ingresos, egresos corporativos y balance patrimonial.")

if df_raw.empty:
    st.error("⚠️ No se pudo establecer conexión con las bases de datos de Notion. Verifica las credenciales de tus Secrets.")
else:
    # Cálculos Financieros
    ingresos = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']['Monto'].sum()
    gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']['Monto'].sum()
    inversiones = df_filtrado[df_filtrado['Tipo'] == 'Inversión']['Monto'].sum()
    saldo_neto = ingresos - gastos - inversiones

    # Renderizado estético de métricas clave (KPI Cards)
    st.markdown("### 📈 Indicadores Financieros")
    m1, m2, m3, m4 = st.columns(4)
    
    # Se añade un truco CSS inline para cambiar sutilmente el color de la métrica por su naturaleza
    m1.metric("💰 Saldo Neto disponible", f"S/. {saldo_neto:,.2f}")
    m2.metric("📈 Ingresos Totales", f"S/. {ingresos:,.2f}")
    m3.metric("📉 Gastos Operativos", f"S/. {gastos:,.2f}")
    m4.metric("🧱 Capital Invertido", f"S/. {inversiones:,.2f}")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Tabs de navegación limpios
    tab_general, tab_inversiones = st.tabs(["📊 Análisis Operativo General", "🚀 Portafolio de Inversiones"])

    with tab_general:
        col_salidas, col_entradas = st.columns(2)
        
        with col_salidas:
            st.markdown('<p class="graph-title">📉 Distribución de Gastos Mensuales</p>', unsafe_allow_html=True)
            df_solo_gastos_mes = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
            
            if not df_solo_gastos_mes.empty:
                df_mes_sal = df_solo_gastos_mes.groupby(['Mes', 'Categoria'])['Monto'].sum().reset_index()
                fig_bar_sal = px.bar(
                    df_mes_sal, x="Mes", y="Monto", color="Categoria",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_bar_sal.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_sal.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Categorías", margin=dict(t=10, b=10))
                st.plotly_chart(fig_bar_sal, use_container_width=True)
            else:
                st.info("No se registran egresos en el rango de fechas seleccionado.")
            
        with col_entradas:
            st.markdown('<p class="graph-title">📈 Flujo de Ingresos por Subcategoría</p>', unsafe_allow_html=True)
            df_ingresos_mes = df_filtrado[df_filtrado['Tipo'] == 'Ingreso']
            
            if not df_ingresos_mes.empty:
                df_mes_ing = df_ingresos_mes.groupby(['Mes', 'Subcategoria'])['Monto'].sum().reset_index()
                fig_bar_ing = px.bar(
                    df_mes_ing, x="Mes", y="Monto", color="Subcategoria",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_bar_ing.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_ing.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Tipos de Ingreso", margin=dict(t=10, b=10))
                st.plotly_chart(fig_bar_ing, use_container_width=True)
            else:
                st.info("No se registran ingresos en el rango de fechas seleccionado.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<p class="graph-title">🔍 Desglose Estructurado de Gastos (Treemap)</p>', unsafe_allow_html=True)
        df_solo_gastos = df_filtrado[df_filtrado['Tipo'] == 'Gasto']
        
        if not df_solo_gastos.empty:
            df_drill = df_solo_gastos.groupby(['Categoria', 'Subcategoria'])['Monto'].sum().reset_index()
            fig_drill = px.treemap(
                df_drill,
                path=['Categoria', 'Subcategoria'],
                values='Monto',
                color='Categoria',
                color_discrete_sequence=px.colors.qualitative.Dark24
            )
            fig_drill.update_traces(
                textinfo="label+value+percent parent",
                hovertemplate="<b>%{label}</b><br>Monto: S/. %{value:,.2f}<extra></extra>"
            )
            fig_drill.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_drill, use_container_width=True)
        else:
            st.info("No hay registros clasificados como 'Gasto' para generar el mapa de proporciones.")

    with tab_inversiones:
        st.markdown('<p class="graph-title">🚀 Análisis Detallado de Capital Invertido</p>', unsafe_allow_html=True)
        df_inv = df_filtrado[df_filtrado['Tipo'] == 'Inversión']
        
        if df_inv.empty:
            st.info("No se encontraron activos o movimientos de inversión vinculados al filtro.")
        else:
            df_inv['Activo_Especifico'] = df_inv.apply(
                lambda r: f"{r['Categoria']} {r['Subcategoria']}" if "Emprendimiento" in r['Categoria'] else r['Subcategoria'], 
                axis=1
            )
            
            col_inv_mes, col_inv_tipo = st.columns(2)
            
            with col_inv_mes:
                st.markdown("##### 📅 Ritmo de Inversión Mensual")
                df_inv_month = df_inv.groupby(['Mes'])['Monto'].sum().reset_index()
                fig_inv_cron = px.bar(
                    df_inv_month, x='Mes', y='Monto', text_auto='.2f',
                    title="Monto Total", color_discrete_sequence=['#2b5c8f']
                )
                fig_inv_cron.update_traces(hovertemplate="<b>Total Invertido:</b> S/. %{y:,.2f}<extra></extra>")
                fig_inv_cron.update_layout(xaxis_title="Mes", yaxis_title="Total Invertido (S/.)", margin=dict(t=30, b=10))
                st.plotly_chart(fig_inv_cron, use_container_width=True)
            
            with col_inv_tipo:
                st.markdown("##### 📅 Inversiones por Mes")
                df_mes_inv = df_inv.groupby(['Mes', 'Activo_Especifico'])['Monto'].sum().reset_index()
                fig_bar_inv_comp = px.bar(
                    df_mes_inv, x="Mes", y="Monto", color="Activo_Especifico",
                    barmode="stack", text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_bar_inv_comp.update_traces(hovertemplate="<b>Monto:</b> S/. %{y:,.2f}<extra></extra>")
                fig_bar_inv_comp.update_layout(xaxis_title="Mes", yaxis_title="Monto (S/.)", legend_title="Activos / Proyectos", margin=dict(t=30, b=10))
                st.plotly_chart(fig_bar_inv_comp, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("##### 📋 Historial de Inversiones")
            
            # Formateo visual estético a la tabla nativa de Streamlit
            st.dataframe(
                df_inv[['Fecha_Raw', 'Categoria', 'Subcategoria', 'Activo_Especifico', 'Monto', 'Descripcion']].rename(columns={'Fecha_Raw': 'Fecha'}), 
                use_container_width=True, 
                hide_index=True
            )
