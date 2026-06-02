import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Mercado Eléctrico Colombia",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main { background-color: #0F1B2D; }
    .stMetric {
        background-color: #1A2B45;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #3A8DFF;
    }
    .metric-card {
        background: #1A2B45;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #00C896;
        margin: 5px 0;
    }
    h1, h2, h3 { color: #FFFFFF; }
    .stSelectbox label { color: #A0B4CC; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════
@st.cache_data
def cargar_datos():
    df = pd.read_excel('Variables_V2.xlsx', sheet_name='Hoja1', header=2)
    
    # 16 columnas exactas confirmadas
    df.columns = [
        'fecha', 'gen_hidro_gwh', 'gen_fosil_gwh',
        'disp_hidro', 'disp_termica', 'reserva_decimal',
        'cap_util_gwh', 'vol_util_gwh', 'demanda_gwh',
        'trm', 'precio_carbon_usd', 'precio_gas_usd',
        'oferta_carbon_cop', 'oferta_gas_cop',
        'oni', 'precio_bolsa_cop'
    ]

    df = df[pd.to_datetime(df['fecha'], errors='coerce').notna()]
    df['fecha'] = pd.to_datetime(df['fecha'])

    for col in [c for c in df.columns if c != 'fecha']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.interpolate(method='linear').reset_index(drop=True)

    df['reserva_pct']       = df['reserva_decimal'] * 100
    df['part_hidro_pct']    = df['gen_hidro_gwh'] / (df['gen_hidro_gwh'] + df['gen_fosil_gwh']) * 100
    df['costo_termico_cop'] = df['precio_carbon_usd'] * df['trm']
    df['anio']              = df['fecha'].dt.year
    df['mes']               = df['fecha'].dt.month
    df['evento_climatico']  = 'Neutro'
    df.loc[df['oni'] >= 0.5,  'evento_climatico'] = 'El Niño'
    df.loc[df['oni'] <= -0.5, 'evento_climatico'] = 'La Niña'

    return df.sort_values('fecha').reset_index(drop=True)

@st.cache_data
def cargar_fncer():
    try:
        fncer = pd.read_excel('Meta_FNCER.xlsx', sheet_name='Data')
        fncer.columns = [
            'proyecto','tipo','capacidad_mw','departamento','municipio',
            'cod_depto','cod_muni','fecha_fpo','energia_kwh_dia',
            'usuarios','inversion_cop','empleos','co2_ton_año'
        ]
        fncer['fecha_fpo'] = pd.to_datetime(fncer['fecha_fpo'], errors='coerce')
        return fncer[fncer['fecha_fpo'] <= '2026-05-31'].copy()
    except:
        return None

df   = cargar_datos()
fncer = cargar_fncer()

# Colores
COLORES = {
    'El Niño': '#FF6B6B',
    'La Niña': '#3A8DFF',
    'Neutro' : '#A0B4CC',
    'bolsa'  : '#FF6B6B',
    'hidro'  : '#3A8DFF',
    'fosil'  : '#FFB347',
    'reserva': '#00C896',
    'oni'    : '#C77DFF',
}

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Simple_lightning_bolt.svg/100px-Simple_lightning_bolt.svg.png", width=50)
    st.title("⚡ Panel de Control")
    st.markdown("---")

    # Filtro de años
    anio_min, anio_max = int(df['anio'].min()), int(df['anio'].max())
    rango_anios = st.slider(
        "Período de análisis",
        min_value=anio_min,
        max_value=anio_max,
        value=(2010, anio_max)
    )

    # Filtro evento climático
    eventos = st.multiselect(
        "Eventos climáticos",
        options=['El Niño', 'La Niña', 'Neutro'],
        default=['El Niño', 'La Niña', 'Neutro']
    )

    st.markdown("---")
    st.markdown("**Fuentes de datos**")
    st.markdown("📊 XM Sinergox")
    st.markdown("🌊 NOAA Climate")
    st.markdown("💰 World Bank")
    st.markdown("🏦 Banco de la República")
    st.markdown("---")
    st.caption("Proyecto Final — Bootcamp TIC\nTalento Tech 2026")

# Filtrar datos
mask = (
    (df['anio'] >= rango_anios[0]) &
    (df['anio'] <= rango_anios[1]) &
    (df['evento_climatico'].isin(eventos))
)
df_f = df[mask].copy()

# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
st.title("⚡ Impacto del Fenómeno del Niño en el Precio de Bolsa")
st.markdown("##### Mercado Eléctrico Colombiano 2000–2025  |  Sistema Interconectado Nacional")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# MÉTRICAS PRINCIPALES
# ══════════════════════════════════════════════════════════════════
col1, col2, col3, col4, col5 = st.columns(5)

precio_nino  = df[df['evento_climatico']=='El Niño']['precio_bolsa_cop'].mean()
precio_nina  = df[df['evento_climatico']=='La Niña']['precio_bolsa_cop'].mean()
precio_max   = df['precio_bolsa_cop'].max()
reserva_min  = df['reserva_pct'].min()
n_meses      = len(df)

col1.metric("💰 Precio Máx Histórico",  f"{precio_max:,.0f} COP/kWh", "2024")
col2.metric("🌵 Precio Medio El Niño",  f"{precio_nino:,.0f} COP/kWh",
            f"+{((precio_nino/precio_nina)-1)*100:.0f}% vs La Niña")
col3.metric("🌧️ Precio Medio La Niña",  f"{precio_nina:,.0f} COP/kWh", "referencia")
col4.metric("💧 Reserva Mínima Histórica", f"{reserva_min:.1f}%", "2024")
col5.metric("📅 Meses analizados",       f"{n_meses}", "2000–2025")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 1 — SERIE DE TIEMPO PRINCIPAL
# ══════════════════════════════════════════════════════════════════
st.subheader("📈 Precio de Bolsa vs Reservas Hídricas")

fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    subplot_titles=('Precio de Bolsa Nacional (COP/kWh)',
                    'Reserva Hídrica del SIN (%)'),
    vertical_spacing=0.08,
    row_heights=[0.6, 0.4]
)

# Sombrear eventos El Niño / La Niña
for evento, color in [('El Niño','rgba(255,107,107,0.15)'),
                       ('La Niña','rgba(58,141,255,0.15)')]:
    periodos = df[df['evento_climatico'] == evento]
    if len(periodos) == 0:
        continue
    en_evento, inicio = False, None
    for _, row in df.iterrows():
        if row['evento_climatico'] == evento and not en_evento:
            en_evento, inicio = True, row['fecha']
        elif row['evento_climatico'] != evento and en_evento:
            for r in [1, 2]:
                fig.add_vrect(
                    x0=inicio, x1=row['fecha'],
                    fillcolor=color, opacity=1,
                    layer="below", line_width=0, row=r, col=1
                )
            en_evento = False

# Línea precio
fig.add_trace(go.Scatter(
    x=df_f['fecha'], y=df_f['precio_bolsa_cop'],
    name='Precio Bolsa', line=dict(color=COLORES['bolsa'], width=1.5),
    hovertemplate='%{x|%b %Y}<br>Precio: %{y:,.0f} COP/kWh<extra></extra>'
), row=1, col=1)

# Línea reservas
fig.add_trace(go.Scatter(
    x=df_f['fecha'], y=df_f['reserva_pct'],
    name='Reserva (%)', line=dict(color=COLORES['reserva'], width=1.5),
    hovertemplate='%{x|%b %Y}<br>Reserva: %{y:.1f}%<extra></extra>'
), row=2, col=1)

# Línea umbral 50%
fig.add_hline(y=50, line_dash="dash", line_color="#FFB347",
              annotation_text="Umbral crítico 50%",
              annotation_position="bottom right", row=2, col=1)

fig.update_layout(
    height=500, template='plotly_dark',
    paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    showlegend=True
)
fig.update_xaxes(showgrid=True, gridcolor='#2E4A6A')
fig.update_yaxes(showgrid=True, gridcolor='#2E4A6A')

st.plotly_chart(fig, use_container_width=True)

# Leyenda manual
col_l1, col_l2, col_l3 = st.columns(3)
col_l1.markdown("🟥 Zona roja = El Niño (ONI ≥ 0.5)")
col_l2.markdown("🟦 Zona azul = La Niña (ONI ≤ -0.5)")
col_l3.markdown("🟡 Línea naranja = Umbral crítico de reserva")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 2 — DOS COLUMNAS
# ══════════════════════════════════════════════════════════════════
col_izq, col_der = st.columns(2)

# ── Scatter reserva vs precio ─────────────────────────────────────
with col_izq:
    st.subheader("💧 Reserva vs Precio por Evento")
    fig2 = px.scatter(
        df_f, x='reserva_pct', y='precio_bolsa_cop',
        color='evento_climatico',
        color_discrete_map=COLORES,
        trendline='ols',
        labels={'reserva_pct':'Reserva hídrica (%)',
                'precio_bolsa_cop':'Precio bolsa (COP/kWh)',
                'evento_climatico':'Evento'},
        hover_data={'fecha': True, 'oni': ':.2f'},
        template='plotly_dark'
    )
    fig2.update_layout(
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        height=380
    )
    fig2.update_traces(marker=dict(size=6, opacity=0.7))
    st.plotly_chart(fig2, use_container_width=True)

# ── Boxplot por evento ────────────────────────────────────────────
with col_der:
    st.subheader("📦 Distribución del Precio por Evento")
    fig3 = px.box(
        df_f, x='evento_climatico', y='precio_bolsa_cop',
        color='evento_climatico',
        color_discrete_map=COLORES,
        points='outliers',
        labels={'evento_climatico':'Evento climático',
                'precio_bolsa_cop':'Precio bolsa (COP/kWh)'},
        template='plotly_dark',
        category_orders={'evento_climatico':['La Niña','Neutro','El Niño']}
    )
    fig3.update_layout(
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        height=380, showlegend=False
    )
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3 — MATRIZ ENERGÉTICA
# ══════════════════════════════════════════════════════════════════´´´
st.subheader("⚡ Evolución de la Matriz Energética")

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=df_f['fecha'], y=df_f['gen_hidro_gwh'],
    name='Hidráulica (GWh)', fill='tozeroy',
    fillcolor='rgba(58,141,255,0.4)',
    line=dict(color=COLORES['hidro'], width=1),
))
fig4.add_trace(go.Scatter(
    x=df_f['fecha'], y=df_f['gen_hidro_gwh'] + df_f['gen_fosil_gwh'],
    name='Fósil (GWh)', fill='tonexty',
    fillcolor='rgba(255,179,71,0.4)',
    line=dict(color=COLORES['fosil'], width=1),
))

# Participación hidro en eje secundario
fig4.add_trace(go.Scatter(
    x=df_f['fecha'], y=df_f['part_hidro_pct'],
    name='Participación hidro (%)',
    line=dict(color='white', width=1.2, dash='dot'),
    yaxis='y2', opacity=0.7
))

fig4.update_layout(
    height=350, template='plotly_dark',
    paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
    yaxis=dict(title='GWh / mes', showgrid=True, gridcolor='#2E4A6A'),
    yaxis2=dict(title='% Participación hidráulica',
                overlaying='y', side='right',
                range=[40, 100], showgrid=False),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    hovermode='x unified'
)
st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 4 — ONI Y CORRELACIONES
# ══════════════════════════════════════════════════════════════════
col_oni, col_cor = st.columns([1.2, 0.8])

with col_oni:
    st.subheader("🌊 ONI vs Precio de Bolsa (estandarizados)")
    oni_norm    = (df_f['oni'] - df['oni'].mean()) / df['oni'].std()
    precio_norm = (df_f['precio_bolsa_cop'] - df['precio_bolsa_cop'].mean()) / df['precio_bolsa_cop'].std()

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=df_f['fecha'], y=oni_norm,
        name='ONI (normalizado)', line=dict(color=COLORES['oni'], width=1.4)
    ))
    fig5.add_trace(go.Scatter(
        x=df_f['fecha'], y=precio_norm,
        name='Precio bolsa (normalizado)',
        line=dict(color=COLORES['bolsa'], width=1.4)
    ))
    fig5.add_hline(y=0, line_dash='dot', line_color='white', opacity=0.3)
    fig5.update_layout(
        height=320, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        yaxis=dict(title='Z-score', showgrid=True, gridcolor='#2E4A6A'),
        hovermode='x unified'
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_cor:
    st.subheader("🔥 Top Correlaciones con Precio")
    vars_corr = ['reserva_pct','gen_hidro_gwh','gen_fosil_gwh',
                 'part_hidro_pct','disp_hidro','demanda_gwh',
                 'trm','precio_carbon_usd','precio_gas_usd',
                 'oferta_carbon_cop','costo_termico_cop','oni']
    corrs = df[vars_corr].corrwith(df['precio_bolsa_cop']).sort_values()

    colores_bar = ['#3A8DFF' if v < 0 else '#FF6B6B' for v in corrs.values]
    fig6 = go.Figure(go.Bar(
        x=corrs.values, y=corrs.index,
        orientation='h',
        marker_color=colores_bar,
        text=[f'{v:.2f}' for v in corrs.values],
        textposition='outside'
    ))
    fig6.update_layout(
        height=320, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        xaxis=dict(range=[-1, 1], showgrid=True, gridcolor='#2E4A6A'),
        yaxis=dict(showgrid=False),
        showlegend=False,
        margin=dict(l=0)
    )
    fig6.add_vline(x=0, line_color='white', line_width=0.8)
    st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 5 — ESTACIONALIDAD
# ══════════════════════════════════════════════════════════════════
st.subheader("📅 Estacionalidad Mensual del Precio")

meses_labels = ['Ene','Feb','Mar','Abr','May','Jun',
                 'Jul','Ago','Sep','Oct','Nov','Dic']
precio_mes = df.groupby('mes')['precio_bolsa_cop'].agg(['mean','median','std']).reset_index()

fig7 = go.Figure()
fig7.add_trace(go.Bar(
    x=meses_labels, y=precio_mes['mean'],
    name='Media', marker_color=COLORES['bolsa'],
    opacity=0.8, error_y=dict(type='data', array=precio_mes['std'], visible=True)
))
fig7.add_trace(go.Scatter(
    x=meses_labels, y=precio_mes['median'],
    name='Mediana', line=dict(color='white', width=2, dash='dot'),
    mode='lines+markers', marker=dict(size=6)
))
fig7.update_layout(
    height=320, template='plotly_dark',
    paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
    yaxis=dict(title='COP/kWh', showgrid=True, gridcolor='#2E4A6A'),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    hovermode='x unified'
)
st.plotly_chart(fig7, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 6 — FNCER
# ══════════════════════════════════════════════════════════════════
if fncer is not None:
    st.subheader("🌞 Proyectos FNCER — Capacidad Renovable por Departamento")

    col_mapa, col_top = st.columns([1.5, 1])

    with col_mapa:
        depto_fncer = fncer.groupby(['departamento','tipo'])['capacidad_mw'].sum().reset_index()
        fig8 = px.bar(
            depto_fncer.sort_values('capacidad_mw', ascending=True).tail(20),
            x='capacidad_mw', y='departamento',
            color='tipo', orientation='h',
            color_discrete_map={'Solar':'#FFB347','Eólico':'#3A8DFF'},
            labels={'capacidad_mw':'Capacidad (MW)', 'departamento':'Departamento'},
            template='plotly_dark'
        )
        fig8.update_layout(
            height=420, paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            legend_title='Tipo', yaxis=dict(showgrid=False),
            xaxis=dict(showgrid=True, gridcolor='#2E4A6A')
        )
        st.plotly_chart(fig8, use_container_width=True)

    with col_top:
        st.markdown("##### 📊 Resumen FNCER")
        total_solar  = fncer[fncer['tipo']=='Solar']['capacidad_mw'].sum()
        total_eolico = fncer[fncer['tipo']=='Eólico']['capacidad_mw'].sum()
        total_usuarios = fncer['usuarios'].sum()
        total_empleos  = fncer['empleos'].sum()
        total_co2      = fncer['co2_ton_año'].sum()

        st.metric("☀️ Capacidad Solar",  f"{total_solar:,.0f} MW")
        st.metric("💨 Capacidad Eólica", f"{total_eolico:,.0f} MW")
        st.metric("👥 Usuarios beneficiados", f"{total_usuarios:,.0f}")
        st.metric("💼 Empleos generados",     f"{total_empleos:,.0f}")
        st.metric("🌿 CO₂ evitado/año",       f"{total_co2/1e6:.1f} M ton")

    st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 7 — TABLA DE DATOS
# ══════════════════════════════════════════════════════════════════
with st.expander("📋 Ver datos filtrados"):
    cols_mostrar = ['fecha','precio_bolsa_cop','reserva_pct',
                    'gen_hidro_gwh','gen_fosil_gwh','oni',
                    'evento_climatico','costo_termico_cop','demanda_gwh']
    st.dataframe(
        df_f[cols_mostrar].rename(columns={
            'fecha':'Fecha','precio_bolsa_cop':'Precio Bolsa (COP/kWh)',
            'reserva_pct':'Reserva (%)','gen_hidro_gwh':'Gen. Hidro (GWh)',
            'gen_fosil_gwh':'Gen. Fósil (GWh)','oni':'ONI',
            'evento_climatico':'Evento','costo_termico_cop':'Costo Térmico',
            'demanda_gwh':'Demanda (GWh)'
        }).style.background_gradient(subset=['Precio Bolsa (COP/kWh)'],
                                      cmap='RdYlGn_r'),
        use_container_width=True, height=300
    )
    st.download_button(
        "⬇️ Descargar datos filtrados",
        data=df_f[cols_mostrar].to_csv(index=False),
        file_name='mercado_electrico_filtrado.csv',
        mime='text/csv'
    )

# Footer
st.markdown("---")
st.caption("⚡ Proyecto Final Bootcamp TIC — Talento Tech 2026 | Jordan Rincón · Julián Mejía · Tulio Ruiz | Fuentes: XM Sinergox · NOAA · World Bank · Banco de la República")
