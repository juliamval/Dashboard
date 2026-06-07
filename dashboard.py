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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Lightning_Bolt_on_Circle.svg/960px-Lightning_Bolt_on_Circle.svg.png", width=50)
    st.title("Panel de Control")
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
# SECCIÓN 6 — FNCER (si el archivo existe)
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

# ══════════════════════════════════════════════════════════════════
# CARGA ADICIONAL — EMBALSES REGIONALES
# ══════════════════════════════════════════════════════════════════
@st.cache_data
def cargar_embalses():
    try:
        emb = pd.read_excel('Embalse.xlsx', sheet_name='Hoja1')
        emb.columns = ['fecha','antioquia','caribe','centro','oriente','valle']
        emb['fecha'] = pd.to_datetime(emb['fecha'], errors='coerce')
        emb = emb.dropna(subset=['fecha']).sort_values('fecha')
        regiones = ['antioquia','caribe','centro','oriente','valle']
        for r in regiones:
            emb[r] = pd.to_numeric(emb[r], errors='coerce') * 100
        emb['fecha_mes'] = emb['fecha'].dt.to_period('M').dt.to_timestamp()
        return emb.groupby('fecha_mes')[regiones].mean().reset_index().rename(columns={'fecha_mes':'fecha'})
    except:
        return None

emb_mensual = cargar_embalses()

# Empalmar embalses con df principal para los modelos
regiones = ['antioquia','caribe','centro','oriente','valle']
df_modelo = df.copy()
if emb_mensual is not None:
    emb_mensual['fecha'] = pd.to_datetime(emb_mensual['fecha'])
    df_modelo = df_modelo.merge(emb_mensual, on='fecha', how='left')

# Clasificación de intensidad del evento
df_modelo['intensidad_nino'] = pd.cut(
    df_modelo['oni'],
    bins=[-99, -1.5, -0.5, 0.5, 1.5, 99],
    labels=['La Niña Fuerte','La Niña','Neutro','El Niño Moderado','El Niño Fuerte']
)

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 8 — MODELO 1: ELASTICIDAD DEL PRECIO AL FENÓMENO DEL NIÑO
# ══════════════════════════════════════════════════════════════════
st.subheader("📐 Modelo 1 — Elasticidad del Precio al Fenómeno del Niño")
st.markdown("""
> **R² = 0.72** · Cada punto de ONI sube el precio **+28.7%** (+52.4 COP/kWh) · El Niño Fuerte → **+278% vs período neutro**
""")

col_el1, col_el2 = st.columns(2)

# ── Precio medio por intensidad del evento ────────────────────────
with col_el1:
    orden_ev    = ['La Niña Fuerte','La Niña','Neutro','El Niño Moderado','El Niño Fuerte']
    colores_ev  = ['#1565C0','#3A8DFF','#A0B4CC','#FF8C42','#FF6B6B']

    precio_ev = (df_modelo.groupby('intensidad_nino')['precio_bolsa_cop']
                 .mean().reindex(orden_ev).reset_index())
    precio_ev.columns = ['Evento','Precio']
    precio_base = precio_ev.loc[precio_ev['Evento']=='Neutro','Precio'].values[0]
    precio_ev['Variación'] = ((precio_ev['Precio'] / precio_base) - 1) * 100
    precio_ev['texto']     = precio_ev.apply(
        lambda r: f"{r['Precio']:.0f} COP<br>{'+' if r['Variación']>=0 else ''}{r['Variación']:.0f}%", axis=1)

    fig_el1 = go.Figure(go.Bar(
        x=precio_ev['Evento'],
        y=precio_ev['Precio'],
        marker_color=colores_ev,
        text=precio_ev['texto'],
        textposition='outside',
        opacity=0.85
    ))
    fig_el1.add_hline(y=precio_base, line_dash='dash', line_color='white',
                      annotation_text=f'Precio neutro ({precio_base:.0f} COP/kWh)',
                      annotation_position='bottom right', opacity=0.6)
    fig_el1.update_layout(
        title='Precio Medio por Intensidad del Evento Climático',
        height=400, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        yaxis=dict(title='COP/kWh', showgrid=True, gridcolor='#2E4A6A'),
        xaxis=dict(showgrid=False), showlegend=False,
        margin=dict(t=50, b=20)
    )
    st.plotly_chart(fig_el1, use_container_width=True)

# ── Impacto en COP por nivel de ONI ──────────────────────────────
with col_el2:
    COEF_ONI    = 0.2523
    precio_medio = df_modelo['precio_bolsa_cop'].mean()
    oni_vals     = [0.5, 1.0, 1.5, 2.0, 2.5]
    etiquetas    = ['Débil\n(0.5)','Moderado\n(1.0)','Moderado+\n(1.5)','Fuerte\n(2.0)','Muy fuerte\n(2.5)']
    impactos     = [(np.exp(COEF_ONI * v) - 1) * precio_medio for v in oni_vals]
    colores_imp  = ['#FFD700','#FFB347','#FF8C42','#FF6B6B','#CC0000']

    fig_el2 = go.Figure(go.Bar(
        x=etiquetas, y=impactos,
        marker_color=colores_imp,
        text=[f'+{v:.0f} COP/kWh' for v in impactos],
        textposition='outside', opacity=0.85
    ))
    fig_el2.update_layout(
        title='Incremento de Precio por Intensidad de El Niño (vs Neutro)',
        height=400, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        yaxis=dict(title='COP/kWh adicionales', showgrid=True, gridcolor='#2E4A6A'),
        xaxis=dict(showgrid=False), showlegend=False,
        margin=dict(t=50, b=20)
    )
    st.plotly_chart(fig_el2, use_container_width=True)

# ── Tabla resumen elasticidad ─────────────────────────────────────
with st.expander("📊 Ver tabla de resultados — Elasticidad"):
    tabla_ev = df_modelo.groupby('intensidad_nino')['precio_bolsa_cop'].agg(
        Media='mean', Mediana='median', Desv_std='std', N_meses='count'
    ).reindex(orden_ev).reset_index()
    tabla_ev.columns = ['Evento Climático','Media (COP/kWh)','Mediana','Desv. Std','N Meses']
    tabla_ev['Variación vs Neutro'] = tabla_ev['Media (COP/kWh)'].apply(
        lambda x: f"{((x/precio_base)-1)*100:+.1f}%")
    tabla_ev = tabla_ev.round(1)
    st.dataframe(tabla_ev, use_container_width=True, hide_index=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 9 — MODELO 2: VULNERABILIDAD REGIONAL
# ══════════════════════════════════════════════════════════════════
st.subheader("🗺️ Modelo 2 — Vulnerabilidad Hídrica Regional")
st.markdown("""
> **Caribe** es la región más vulnerable: sus embalses caen **−32.7 pp** durante El Niño (de 81% a 48%)
> y es la única con correlación positiva con el precio de bolsa (+0.245)
""")

if emb_mensual is not None:

    col_r1, col_r2 = st.columns(2)

    # ── Serie temporal embalses regionales ───────────────────────
    with col_r1:
        colores_region = {
            'antioquia':'#3A8DFF','caribe':'#FF6B6B',
            'centro':'#00C896','oriente':'#FFB347','valle':'#C77DFF'
        }
        fig_r1 = go.Figure()

        # Sombrear El Niño
        en_nino, inicio_n = False, None
        for _, row in df_modelo.iterrows():
            if row['oni'] >= 0.5 and not en_nino:
                en_nino, inicio_n = True, row['fecha']
            elif row['oni'] < 0.5 and en_nino:
                fig_r1.add_vrect(x0=inicio_n, x1=row['fecha'],
                                  fillcolor='rgba(255,107,107,0.12)',
                                  opacity=1, layer='below', line_width=0)
                en_nino = False

        for reg in regiones:
            sub = df_modelo[
                (df_modelo['fecha'] >= pd.to_datetime(f'{rango_anios[0]}-01-01')) &
                (df_modelo['fecha'] <= pd.to_datetime(f'{rango_anios[1]}-12-31'))
            ]
            fig_r1.add_trace(go.Scatter(
                x=sub['fecha'], y=sub[reg],
                name=reg.title(), mode='lines',
                line=dict(color=colores_region[reg], width=1.3),
                hovertemplate=f'{reg.title()}: %{{y:.1f}}%<extra></extra>'
            ))

        fig_r1.add_hline(y=50, line_dash='dash', line_color='#FFB347',
                          annotation_text='Umbral 50%', opacity=0.7)
        fig_r1.update_layout(
            title='Niveles de Embalse por Región (zonas rojas = El Niño)',
            height=380, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='% Capacidad útil', showgrid=True,
                       gridcolor='#2E4A6A', range=[0, 115]),
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            hovermode='x unified'
        )
        st.plotly_chart(fig_r1, use_container_width=True)

    # ── Comparación neutro vs El Niño por región ─────────────────
    with col_r2:
        resultados_reg = {}
        for reg in regiones:
            nino_v   = df_modelo[df_modelo['oni'] >= 0.5][reg].dropna()
            neutro_v = df_modelo[(df_modelo['oni'] > -0.5) & (df_modelo['oni'] < 0.5)][reg].dropna()
            resultados_reg[reg] = {
                'neutro': neutro_v.mean(),
                'nino'  : nino_v.mean(),
                'caida' : neutro_v.mean() - nino_v.mean(),
            }

        reg_names = [r.title() for r in regiones]
        vals_neutro = [resultados_reg[r]['neutro'] for r in regiones]
        vals_nino   = [resultados_reg[r]['nino']   for r in regiones]
        caidas      = [resultados_reg[r]['caida']  for r in regiones]

        fig_r2 = go.Figure()
        fig_r2.add_trace(go.Bar(
            name='Período Neutro', x=reg_names, y=vals_neutro,
            marker_color='#00C896', opacity=0.8,
            text=[f'{v:.1f}%' for v in vals_neutro], textposition='inside'
        ))
        fig_r2.add_trace(go.Bar(
            name='Durante El Niño', x=reg_names, y=vals_nino,
            marker_color='#FF6B6B', opacity=0.8,
            text=[f'{v:.1f}%' for v in vals_nino], textposition='inside'
        ))
        fig_r2.add_hline(y=50, line_dash='dash', line_color='#FFB347', opacity=0.8)

        # Anotaciones de caída
        for i, (reg, caida) in enumerate(zip(reg_names, caidas)):
            if caida > 0:
                fig_r2.add_annotation(
                    x=reg, y=max(vals_neutro[i], vals_nino[i]) + 3,
                    text=f'−{caida:.1f}pp',
                    showarrow=False, font=dict(color='#FFB347', size=11, family='Arial Bold')
                )

        fig_r2.update_layout(
            title='Nivel de Embalse: Neutro vs El Niño por Región',
            barmode='group', height=380, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='% Capacidad útil', showgrid=True, gridcolor='#2E4A6A'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02)
        )
        st.plotly_chart(fig_r2, use_container_width=True)

    # ── Tabla vulnerabilidad ──────────────────────────────────────
    with st.expander("📊 Ver tabla de vulnerabilidad regional"):
        tabla_vuln = pd.DataFrame([
            {
                'Región'           : r.title(),
                'Nivel Normal (%)'  : round(resultados_reg[r]['neutro'], 1),
                'Nivel El Niño (%)' : round(resultados_reg[r]['nino'], 1),
                'Caída (pp)'        : round(resultados_reg[r]['caida'], 1),
                'Corr. Precio'      : round(df_modelo[r].corr(df_modelo['precio_bolsa_cop']), 3),
            }
            for r in regiones
        ]).sort_values('Caída (pp)', ascending=False)
        st.dataframe(tabla_vuln, use_container_width=True, hide_index=True)

else:
    st.info("⚠️ Archivo Embalse.xlsx no encontrado. Colócalo en la misma carpeta que dashboard.py")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 10 — MODELO 3: SIMULACIÓN DE MITIGACIÓN FNCER
# ══════════════════════════════════════════════════════════════════
st.subheader("☀️ Modelo 3 — Simulación de Mitigación FNCER")
st.markdown("""
> Con **+100% de capacidad FNCER** (6,000 → 12,000 MW), el precio durante El Niño 2023–2024
> habría bajado **−262 COP/kWh (−42%)** — ahorro de **$471,000 COP** por hogar estrato 2
""")

# ── Parámetros interactivos en sidebar ───────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**⚙️ Simulación FNCER**")
    consumo_hogar = st.slider("Consumo hogar (kWh/mes)", 100, 300, 150, 25)
    meses_nino_sim = st.slider("Duración episodio Niño (meses)", 6, 18, 13, 1)

# Parámetros del modelo
BETA_FOSIL              = 0.2678
FACTOR_CAP_SOLAR        = 0.22
FACTOR_CAP_EOLICO       = 0.38
HORAS_MES               = 730
CAP_SOLAR_ACTUAL        = 4384
CAP_EOLICO_ACTUAL       = 1615

periodo_nino_sim = df_modelo[
    (df_modelo['fecha'] >= '2023-01-01') &
    (df_modelo['fecha'] <= '2024-12-31') &
    (df_modelo['oni'] >= 0.5)
].copy()

precio_obs_sim = periodo_nino_sim['precio_bolsa_cop'].mean() if len(periodo_nino_sim) > 0 else 626.2

escenarios_sim = {
    'Base real\n(6,000 MW)'    : 0,
    '+50%\n(9,000 MW)'         : CAP_SOLAR_ACTUAL * 0.5,
    '+100%\n(12,000 MW)'       : CAP_SOLAR_ACTUAL * 1.0,
    '+200%\n(18,000 MW)'       : CAP_SOLAR_ACTUAL * 2.0,
}
cap_eolico_extra = {k: v * (CAP_EOLICO_ACTUAL / CAP_SOLAR_ACTUAL) for k, v in escenarios_sim.items()}

resultados_escenarios = {}
for nombre, cap_solar_extra in escenarios_sim.items():
    gen_solar_extra  = cap_solar_extra  * FACTOR_CAP_SOLAR  * HORAS_MES / 1000
    gen_eolico_extra = cap_eolico_extra[nombre] * FACTOR_CAP_EOLICO * HORAS_MES / 1000
    gen_extra_total  = (gen_solar_extra + gen_eolico_extra) * 0.85
    reduccion        = BETA_FOSIL * gen_extra_total
    precio_sim       = max(precio_obs_sim - reduccion, 50)
    ahorro_mes       = reduccion * consumo_hogar
    resultados_escenarios[nombre] = {
        'precio_sim' : precio_sim,
        'reduccion'  : reduccion,
        'ahorro_pct' : (reduccion / precio_obs_sim) * 100,
        'ahorro_mes' : ahorro_mes,
        'ahorro_ep'  : ahorro_mes * meses_nino_sim,
    }

nombres_esc  = list(resultados_escenarios.keys())
precios_sim  = [resultados_escenarios[n]['precio_sim']  for n in nombres_esc]
reducciones  = [resultados_escenarios[n]['reduccion']   for n in nombres_esc]
ahorros_pct  = [resultados_escenarios[n]['ahorro_pct']  for n in nombres_esc]
ahorros_ep   = [resultados_escenarios[n]['ahorro_ep']   for n in nombres_esc]
colores_esc  = ['#A0B4CC','#FFD700','#FFB347','#00C896']

col_s1, col_s2, col_s3 = st.columns(3)

# ── Panel 1: Precio simulado ──────────────────────────────────────
with col_s1:
    fig_s1 = go.Figure(go.Bar(
        x=nombres_esc, y=precios_sim,
        marker_color=colores_esc, opacity=0.85,
        text=[f'{p:.0f} COP/kWh<br>(-{pct:.0f}%)' for p, pct in zip(precios_sim, ahorros_pct)],
        textposition='outside'
    ))
    fig_s1.add_hline(y=precio_obs_sim, line_dash='dash', line_color='#FF6B6B',
                      annotation_text=f'Precio real ({precio_obs_sim:.0f} COP/kWh)',
                      annotation_position='top right', opacity=0.9)
    fig_s1.update_layout(
        title='Precio Simulado por Escenario<br>(El Niño 2023-2024)',
        height=380, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        yaxis=dict(title='COP/kWh', showgrid=True, gridcolor='#2E4A6A', range=[0, precio_obs_sim*1.2]),
        xaxis=dict(showgrid=False), showlegend=False
    )
    st.plotly_chart(fig_s1, use_container_width=True)

# ── Panel 2: Precio contrafactual en el tiempo ───────────────────
with col_s2:
    fig_s2 = go.Figure()
    if len(periodo_nino_sim) > 0:
        fig_s2.add_trace(go.Scatter(
            x=periodo_nino_sim['fecha'], y=periodo_nino_sim['precio_bolsa_cop'],
            name='Real observado', line=dict(color='#FF6B6B', width=2),
            fill='tozeroy', fillcolor='rgba(255,107,107,0.1)'
        ))
        for nombre, col_c in [('+100%\n(12,000 MW)','#FFB347'),('+200%\n(18,000 MW)','#00C896')]:
            red = resultados_escenarios[nombre]['reduccion']
            precio_cf = (periodo_nino_sim['precio_bolsa_cop'] - red).clip(lower=50)
            label = nombre.replace('\n',' ')
            fig_s2.add_trace(go.Scatter(
                x=periodo_nino_sim['fecha'], y=precio_cf,
                name=f'{label}: −{red:.0f} COP/kWh',
                line=dict(color=col_c, width=1.8, dash='dash')
            ))
    fig_s2.update_layout(
        title='Precio Real vs Contrafactual FNCER<br>(El Niño 2023-2024)',
        height=380, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        yaxis=dict(title='COP/kWh', showgrid=True, gridcolor='#2E4A6A'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=9)),
        hovermode='x unified'
    )
    st.plotly_chart(fig_s2, use_container_width=True)

# ── Panel 3: Ahorro hogar estrato 2 ──────────────────────────────
with col_s3:
    fig_s3 = go.Figure(go.Bar(
        x=nombres_esc, y=ahorros_ep,
        marker_color=colores_esc, opacity=0.85,
        text=[f'${v:,.0f}' for v in ahorros_ep],
        textposition='outside'
    ))
    fig_s3.update_layout(
        title=f'Ahorro Hogar Estrato 2<br>({consumo_hogar} kWh/mes · {meses_nino_sim} meses)',
        height=380, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        yaxis=dict(title='COP por episodio', showgrid=True, gridcolor='#2E4A6A'),
        xaxis=dict(showgrid=False), showlegend=False
    )
    st.plotly_chart(fig_s3, use_container_width=True)

# ── Tabla simulación ──────────────────────────────────────────────
with st.expander("📊 Ver tabla completa — Simulación FNCER"):
    tabla_sim = pd.DataFrame([
        {
            'Escenario'              : n.replace('\n',' '),
            'Precio Simulado (COP)'  : round(resultados_escenarios[n]['precio_sim'], 1),
            'Reducción (COP/kWh)'    : round(resultados_escenarios[n]['reduccion'], 1),
            'Ahorro (%)'             : round(resultados_escenarios[n]['ahorro_pct'], 1),
            'Ahorro/mes hogar (COP)' : round(resultados_escenarios[n]['ahorro_mes'], 0),
            'Ahorro episodio (COP)'  : round(resultados_escenarios[n]['ahorro_ep'], 0),
        }
        for n in nombres_esc
    ])
    st.dataframe(tabla_sim, use_container_width=True, hide_index=True)

# ── Resumen ejecutivo ─────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Resumen Ejecutivo — Tres Hallazgos Principales")
col_h1, col_h2, col_h3 = st.columns(3)

with col_h1:
    st.markdown("""
    <div style='background:#1A2B45;border-left:4px solid #FF6B6B;padding:16px;border-radius:8px'>
    <h4 style='color:#FF6B6B;margin:0'>1. Elasticidad</h4>
    <p style='color:#A0B4CC;font-size:13px;margin-top:8px'>
    R² = 0.72 · Cada punto de ONI eleva el precio<br>
    <b style='color:white;font-size:18px'>+28.7% (+52 COP/kWh)</b><br>
    El Niño Fuerte → precio sube <b style='color:#FF6B6B'>+278%</b> vs período neutro
    </p>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown("""
    <div style='background:#1A2B45;border-left:4px solid #FFB347;padding:16px;border-radius:8px'>
    <h4 style='color:#FFB347;margin:0'>2. Vulnerabilidad Regional</h4>
    <p style='color:#A0B4CC;font-size:13px;margin-top:8px'>
    Caribe: embalses caen<br>
    <b style='color:white;font-size:18px'>−32.7 pp en El Niño</b><br>
    De 81% → 48% · Única región con correlación<br>positiva con el precio (+0.245)
    </p>
    </div>
    """, unsafe_allow_html=True)

with col_h3:
    mejor_escenario = resultados_escenarios['+100%\n(12,000 MW)']
    st.markdown(f"""
    <div style='background:#1A2B45;border-left:4px solid #00C896;padding:16px;border-radius:8px'>
    <h4 style='color:#00C896;margin:0'>3. Simulación FNCER</h4>
    <p style='color:#A0B4CC;font-size:13px;margin-top:8px'>
    Con 12,000 MW (+100% actual):<br>
    <b style='color:white;font-size:18px'>−{mejor_escenario['reduccion']:.0f} COP/kWh (−{mejor_escenario['ahorro_pct']:.0f}%)</b><br>
    Ahorro hogar estrato 2:<br>
    <b style='color:#00C896'>${mejor_escenario['ahorro_ep']:,.0f} COP</b> por episodio
    </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("⚡ Proyecto Final Bootcamp TIC — Talento Tech 2026 | Jordan Rincón · Julián Mejía · Tulio Ruiz")
