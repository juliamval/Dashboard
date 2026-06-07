import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (classification_report, confusion_matrix,
                              accuracy_score, f1_score, precision_score, recall_score)

# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Mercado Eléctrico Colombia",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0F1B2D; }
    .stMetric {
        background-color: #1A2B45;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #3A8DFF;
    }
    h1, h2, h3 { color: #FFFFFF; }
    .stSelectbox label { color: #A0B4CC; }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #1A2B45;
        color: #A0B4CC;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #028090;
        color: white;
    }
    .insight-box {
        background-color: #1A2B45;
        border-left: 4px solid #00C896;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

COLORES = {
    'El Niño': '#FF6B6B', 'La Niña': '#3A8DFF', 'Neutro' : '#A0B4CC',
    'bolsa'  : '#FF6B6B', 'hidro'  : '#3A8DFF', 'fosil'  : '#FFB347',
    'reserva': '#00C896', 'oni'    : '#C77DFF',
}

# ══════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════
@st.cache_data
def cargar_datos():
    # Leer el archivo SIN forzar nombres todavía
    df = pd.read_excel('Variables_V2.xlsx', sheet_name='Hoja1', header=2)

    # Nombres esperados de las primeras 16 columnas
    nombres_esperados = [
        'fecha', 'gen_hidro_gwh', 'gen_fosil_gwh',
        'disp_hidro', 'disp_termica',
        'reserva_decimal', 'cap_util_gwh', 'vol_util_gwh',
        'demanda_gwh', 'trm',
        'precio_carbon_usd', 'precio_gas_usd',
        'oferta_carbon_cop', 'oferta_gas_cop',
        'oni', 'precio_bolsa_cop'
    ]

    # Asignar nombres adaptándose al número real de columnas
    n_cols = df.shape[1]
    if n_cols >= 16:
        # Caso normal: 16 o más columnas
        df.columns = nombres_esperados + [f'_drop{i}' for i in range(n_cols - 16)]
    else:
        # Caso reducido: menos de 16 columnas
        df.columns = nombres_esperados[:n_cols]

    # Mantener solo las 16 columnas útiles que existan
    cols = [c for c in nombres_esperados if c in df.columns]
    df = df[cols].copy()

    # Filtrar fechas válidas
    df = df[pd.to_datetime(df['fecha'], errors='coerce').notna()]
    df['fecha'] = pd.to_datetime(df['fecha']).dt.to_period('M').dt.to_timestamp()

    # Convertir a numérico e interpolar
    for col in cols[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.interpolate(method='linear').reset_index(drop=True)

    # Variables derivadas
    df['reserva_pct']       = df['reserva_decimal'] * 100
    df['part_hidro_pct']    = df['gen_hidro_gwh'] / (df['gen_hidro_gwh'] + df['gen_fosil_gwh']) * 100
    df['costo_termico_cop'] = df['precio_carbon_usd'] * df['trm']
    df['anio']              = df['fecha'].dt.year
    df['mes']               = df['fecha'].dt.month
    df['evento_climatico']  = 'Neutro'
    df.loc[df['oni'] >= 0.5,  'evento_climatico'] = 'El Niño'
    df.loc[df['oni'] <= -0.5, 'evento_climatico'] = 'La Niña'

    df['intensidad_nino'] = pd.cut(
        df['oni'],
        bins=[-99, -1.5, -0.5, 0.5, 1.5, 99],
        labels=['La Niña Fuerte','La Niña','Neutro','El Niño Moderado','El Niño Fuerte']
    )

    df['reserva_lag1'] = df['reserva_pct'].shift(1)
    df['oni_lag1']     = df['oni'].shift(1)

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

@st.cache_data
def cargar_embalse():
    try:
        emb = pd.read_excel('Embalse.xlsx', sheet_name='Hoja1')
        emb.columns = ['fecha','antioquia','caribe','centro','oriente','valle']
        emb['fecha'] = pd.to_datetime(emb['fecha'], errors='coerce')
        emb = emb.dropna(subset=['fecha']).sort_values('fecha')
        regiones = ['antioquia','caribe','centro','oriente','valle']
        for r in regiones:
            emb[r] = emb[r] * 100
        emb['fecha_mes'] = emb['fecha'].dt.to_period('M').dt.to_timestamp()
        emb_mensual = emb.groupby('fecha_mes')[regiones].mean().reset_index()
        emb_mensual.rename(columns={'fecha_mes':'fecha'}, inplace=True)
        return emb_mensual
    except:
        return None

df = cargar_datos()
fncer = cargar_fncer()
emb_mensual = cargar_embalse()

if emb_mensual is not None:
    df = df.merge(emb_mensual, on='fecha', how='left')

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("⚡ Panel de Control")
    st.markdown("---")

    anio_min, anio_max = int(df['anio'].min()), int(df['anio'].max())
    rango_anios = st.slider("Período de análisis",
                              min_value=anio_min, max_value=anio_max,
                              value=(2000, anio_max))

    eventos = st.multiselect("Eventos climáticos",
                              options=['El Niño', 'La Niña', 'Neutro'],
                              default=['El Niño', 'La Niña', 'Neutro'])

    st.markdown("---")
    st.markdown("**📊 Fuentes**")
    st.caption("XM Sinergox · NOAA · World Bank · UPME · Banco de la República")
    st.markdown("---")
    st.markdown("**👥 Equipo**")
    st.caption("Jordan Rincón · Julián Mejía · Tulio Ruiz")
    st.caption("Bootcamp TIC Talento Tech 2026")

mask = ((df['anio'] >= rango_anios[0]) &
        (df['anio'] <= rango_anios[1]) &
        (df['evento_climatico'].isin(eventos)))
df_f = df[mask].copy()

# ══════════════════════════════════════════════════════════════════
# HEADER + KPIS PRINCIPALES
# ══════════════════════════════════════════════════════════════════
st.title("⚡ Impacto del Fenómeno del Niño en el Precio de Bolsa")
st.markdown("##### Mercado Eléctrico Colombiano 2000–2025  |  Sistema Interconectado Nacional")
st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)
precio_nino = df[df['evento_climatico']=='El Niño']['precio_bolsa_cop'].mean()
precio_nina = df[df['evento_climatico']=='La Niña']['precio_bolsa_cop'].mean()
precio_max  = df['precio_bolsa_cop'].max()
reserva_min = df['reserva_pct'].min()

col1.metric("💰 Precio Máx Histórico", f"{precio_max:,.0f} COP/kWh", "2024")
col2.metric("🌵 Precio Medio El Niño", f"{precio_nino:,.0f} COP/kWh",
            f"+{((precio_nino/precio_nina)-1)*100:.0f}% vs La Niña")
col3.metric("🌧️ Precio Medio La Niña", f"{precio_nina:,.0f} COP/kWh", "referencia")
col4.metric("💧 Reserva Mínima", f"{reserva_min:.1f}%", "2024")
col5.metric("📅 Meses analizados", f"{len(df)}", "2000–2025")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 EDA Series",
    "📊 Elasticidad",
    "🗺️ Vulnerabilidad",
    "☀️ Simulación FNCER",
    "🤖 Modelo ML",
    "🌞 Mapa FNCER",
])

# ── TAB 1: EDA ────────────────────────────────────────────────────
with tab1:
    st.subheader("📈 Precio de Bolsa vs Reservas Hídricas")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
        subplot_titles=('Precio de Bolsa Nacional (COP/kWh)','Reserva Hídrica del SIN (%)'),
        vertical_spacing=0.08, row_heights=[0.6, 0.4])

    for evento, color in [('El Niño','rgba(255,107,107,0.15)'),
                           ('La Niña','rgba(58,141,255,0.15)')]:
        en_evento, inicio = False, None
        for _, row in df.iterrows():
            if row['evento_climatico'] == evento and not en_evento:
                en_evento, inicio = True, row['fecha']
            elif row['evento_climatico'] != evento and en_evento:
                for r in [1, 2]:
                    fig.add_vrect(x0=inicio, x1=row['fecha'],
                        fillcolor=color, opacity=1, layer="below",
                        line_width=0, row=r, col=1)
                en_evento = False

    fig.add_trace(go.Scatter(x=df_f['fecha'], y=df_f['precio_bolsa_cop'],
        name='Precio Bolsa', line=dict(color=COLORES['bolsa'], width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_f['fecha'], y=df_f['reserva_pct'],
        name='Reserva (%)', line=dict(color=COLORES['reserva'], width=1.5)), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="#FFB347",
                  annotation_text="Umbral crítico 50%", row=2, col=1)

    fig.update_layout(height=500, template='plotly_dark',
        paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
        legend=dict(orientation='h', yanchor='bottom', y=1.02))
    fig.update_xaxes(showgrid=True, gridcolor='#2E4A6A')
    fig.update_yaxes(showgrid=True, gridcolor='#2E4A6A')
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📦 Distribución del precio por evento")
        fig_box = px.box(df_f, x='evento_climatico', y='precio_bolsa_cop',
            color='evento_climatico', color_discrete_map=COLORES,
            points='outliers', template='plotly_dark',
            category_orders={'evento_climatico':['La Niña','Neutro','El Niño']})
        fig_box.update_layout(paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
                               height=380, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    with col_b:
        st.subheader("⚡ Matriz energética histórica")
        fig_mat = go.Figure()
        fig_mat.add_trace(go.Scatter(x=df_f['fecha'], y=df_f['gen_hidro_gwh'],
            name='Hidráulica', fill='tozeroy',
            fillcolor='rgba(58,141,255,0.4)', line=dict(color=COLORES['hidro'], width=1)))
        fig_mat.add_trace(go.Scatter(x=df_f['fecha'],
            y=df_f['gen_hidro_gwh'] + df_f['gen_fosil_gwh'],
            name='Fósil', fill='tonexty',
            fillcolor='rgba(255,179,71,0.4)', line=dict(color=COLORES['fosil'], width=1)))
        fig_mat.update_layout(height=380, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='GWh / mes'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02))
        st.plotly_chart(fig_mat, use_container_width=True)

# ── TAB 2: ELASTICIDAD ────────────────────────────────────────────
with tab2:
    st.subheader("📊 Análisis de Elasticidad del Precio al Fenómeno del Niño")
    st.markdown("""Cuantifica cuánto sube el precio por cada punto del índice ONI,
    controlando por reserva hídrica, demanda y tendencia estructural.""")

    df_e = df.dropna(subset=['precio_bolsa_cop','oni','reserva_pct',
                              'demanda_gwh','costo_termico_cop']).copy()
    df_e['log_precio']  = np.log(df_e['precio_bolsa_cop'])
    df_e['log_reserva'] = np.log(df_e['reserva_pct'])
    df_e['log_demanda'] = np.log(df_e['demanda_gwh'])
    df_e['tendencia']   = np.arange(len(df_e))

    X_el = sm.add_constant(df_e[['oni','log_reserva','log_demanda',
                                   'costo_termico_cop','tendencia']])
    modelo_el = sm.OLS(df_e['log_precio'], X_el).fit()

    coef_oni     = modelo_el.params['oni']
    precio_medio = df_e['precio_bolsa_cop'].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R² del modelo", f"{modelo_el.rsquared:.3f}")
    c2.metric("Coef ONI (log)", f"{coef_oni:.3f}")
    c3.metric("1 punto ONI →", f"+{(np.exp(coef_oni)-1)*100:.1f}%")
    c4.metric("En COP", f"+{precio_medio*(np.exp(coef_oni)-1):.0f} COP/kWh")

    st.markdown("---")

    col_x, col_y = st.columns([1.2, 0.8])
    with col_x:
        st.subheader("Precio medio por intensidad del evento")
        precio_por_evento = df_e.groupby('intensidad_nino')['precio_bolsa_cop'].mean().reindex(
            ['La Niña Fuerte','La Niña','Neutro','El Niño Moderado','El Niño Fuerte'])
        precio_neutro = precio_por_evento['Neutro']

        colores_int = ['#1565C0','#3A8DFF','#A0B4CC','#FF8C42','#FF6B6B']
        fig_int = go.Figure()
        fig_int.add_trace(go.Bar(
            x=precio_por_evento.index.astype(str), y=precio_por_evento.values,
            marker_color=colores_int,
            text=[f'{v:.0f}<br>({((v/precio_neutro)-1)*100:+.0f}%)'
                  for v in precio_por_evento.values],
            textposition='outside', textfont=dict(color='white', size=11)))
        fig_int.add_hline(y=precio_neutro, line_dash='dash', line_color='white',
                           annotation_text='Línea base (Neutro)', opacity=0.5)
        fig_int.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='COP/kWh', showgrid=True, gridcolor='#2E4A6A'),
            xaxis=dict(title='Intensidad del evento'), showlegend=False)
        st.plotly_chart(fig_int, use_container_width=True)

    with col_y:
        st.subheader("Impacto por intensidad")
        for v, label in zip([0.5, 1.0, 1.5, 2.0, 2.5],
                              ['Débil','Moderado','Moderado+','Fuerte','Muy fuerte']):
            imp = (np.exp(coef_oni * v) - 1) * precio_medio
            pct = (np.exp(coef_oni * v) - 1) * 100
            st.markdown(f"""<div class="insight-box">
            <strong>ONI = {v} ({label})</strong><br>
            <span style="color:#FF6B6B">+{imp:.0f} COP/kWh</span> &nbsp;
            <span style="color:#A0B4CC">({pct:+.0f}%)</span></div>""",
            unsafe_allow_html=True)

    st.markdown("""<div class="insight-box" style="border-left-color: #FF6B6B">
    <strong>🎯 Hallazgo clave:</strong> El Niño Fuerte (ONI ≥ 1.5) eleva el precio
    promedio <strong>278% sobre el nivel neutro</strong> (624 vs 165 COP/kWh).
    El modelo OLS log-lineal explica el <strong>72% de la varianza histórica</strong>
    del precio de bolsa. Cada punto adicional de ONI suma 28.7% al precio.
    </div>""", unsafe_allow_html=True)

# ── TAB 3: VULNERABILIDAD REGIONAL ────────────────────────────────
with tab3:
    st.subheader("🗺️ Vulnerabilidad Regional Hídrica durante El Niño")
    st.markdown("Análisis comparativo de los niveles de embalse por región durante eventos climáticos.")

    if emb_mensual is not None and 'caribe' in df.columns:
        regiones = ['antioquia','caribe','centro','oriente','valle']
        df_r = df.dropna(subset=regiones + ['oni','precio_bolsa_cop']).copy()

        resultados = {}
        for region in regiones:
            nino_v   = df_r[df_r['oni'] >= 0.5][region]
            neutro_v = df_r[(df_r['oni'] > -0.5) & (df_r['oni'] < 0.5)][region]
            resultados[region] = {
                'media_neutro' : neutro_v.mean(),
                'media_nino'   : nino_v.mean(),
                'caida'        : neutro_v.mean() - nino_v.mean(),
                'corr_precio'  : df_r[region].corr(df_r['precio_bolsa_cop']),
            }

        st.subheader("Evolución de niveles de embalse por región")
        fig_reg = go.Figure()
        colores_reg = {'antioquia':'#3A8DFF','caribe':'#FF6B6B',
                        'centro':'#00C896','oriente':'#FFB347','valle':'#C77DFF'}
        for region in regiones:
            fig_reg.add_trace(go.Scatter(x=df_r['fecha'], y=df_r[region],
                name=region.title(),
                line=dict(color=colores_reg[region], width=1.3)))

        en_nino, inicio = False, None
        for _, row in df_r.iterrows():
            if row['oni'] >= 0.5 and not en_nino:
                en_nino, inicio = True, row['fecha']
            elif row['oni'] < 0.5 and en_nino:
                fig_reg.add_vrect(x0=inicio, x1=row['fecha'],
                    fillcolor='rgba(255,107,107,0.15)', opacity=1,
                    layer='below', line_width=0)
                en_nino = False

        fig_reg.add_hline(y=50, line_dash='dash', line_color='#FFB347',
                          opacity=0.6, annotation_text='Umbral crítico 50%')
        fig_reg.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='Nivel embalse (%)', range=[0, 110]),
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            hovermode='x unified')
        st.plotly_chart(fig_reg, use_container_width=True)

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.subheader("Embalse: Neutro vs El Niño")
            df_comp = pd.DataFrame(resultados).T.reset_index()
            df_comp.columns = ['region','neutro','nino','caida','corr']

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(name='Período Neutro',
                x=df_comp['region'].str.title(), y=df_comp['neutro'],
                marker_color='#00C896', opacity=0.85))
            fig_comp.add_trace(go.Bar(name='Durante El Niño',
                x=df_comp['region'].str.title(), y=df_comp['nino'],
                marker_color='#FF6B6B', opacity=0.85))
            fig_comp.add_hline(y=50, line_dash='dash', line_color='#FFB347',
                                opacity=0.6, annotation_text='Crítico 50%')
            fig_comp.update_layout(height=400, template='plotly_dark',
                paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
                yaxis=dict(title='Nivel embalse (%)'), barmode='group',
                legend=dict(orientation='h', yanchor='bottom', y=1.02))
            st.plotly_chart(fig_comp, use_container_width=True)

        with col_v2:
            st.subheader("Vulnerabilidad por región")
            df_comp_sorted = df_comp.copy()
            df_comp_sorted['vuln_score'] = (df_comp_sorted['caida'].clip(lower=0) * 0.6 +
                                             df_comp_sorted['corr'].clip(lower=0) * 100 * 0.4)
            df_comp_sorted = df_comp_sorted.sort_values('vuln_score', ascending=True)

            colors_vuln = ['#FF6B6B' if v > 5 else '#3A8DFF'
                           for v in df_comp_sorted['vuln_score']]
            fig_vuln = go.Figure(go.Bar(
                x=df_comp_sorted['vuln_score'],
                y=df_comp_sorted['region'].str.title(),
                orientation='h', marker_color=colors_vuln,
                text=[f'{v:.1f}' for v in df_comp_sorted['vuln_score']],
                textposition='outside', textfont=dict(color='white')))
            fig_vuln.update_layout(height=400, template='plotly_dark',
                paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
                xaxis=dict(title='Score de vulnerabilidad'), showlegend=False)
            st.plotly_chart(fig_vuln, use_container_width=True)

        st.markdown("""<div class="insight-box" style="border-left-color: #FF6B6B">
        <strong>🎯 Hallazgo regional:</strong> La región <strong>Caribe</strong>
        es el principal punto de vulnerabilidad del SIN. Sus embalses caen
        <strong>32.7 puntos porcentuales</strong> durante El Niño (de 81% a 48%),
        y es la <strong>única región con correlación positiva con el precio</strong>
        (r = +0.245). Esto valida la decisión estratégica de concentrar la capacidad
        eólica en La Guajira.</div>""", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Archivo Embalse.xlsx no disponible.")

# ── TAB 4: SIMULACIÓN FNCER ───────────────────────────────────────
with tab4:
    st.subheader("☀️ Simulación de Mitigación con Mayor Penetración FNCER")
    st.markdown("""**Análisis contrafactual:** estima cuánto se habría reducido el precio
    durante El Niño 2023–2024 con distintos niveles adicionales de capacidad renovable.""")

    df_sim = df.dropna(subset=['precio_bolsa_cop','gen_fosil_gwh',
                                'demanda_gwh','oni']).copy()
    X_beta = sm.add_constant(df_sim[['gen_fosil_gwh','reserva_pct',
                                       'costo_termico_cop','demanda_gwh']])
    modelo_beta = sm.OLS(df_sim['precio_bolsa_cop'], X_beta).fit()
    beta_fosil = modelo_beta.params['gen_fosil_gwh']

    FC_SOLAR  = 0.22
    FC_EOLICO = 0.38
    HORAS_MES = 730
    cap_solar = 4384
    cap_eolico = 1615

    st.subheader("🎚️ Simulador interactivo")
    factor = st.slider("Multiplicador de capacidad FNCER adicional",
        min_value=0.0, max_value=3.0, value=1.0, step=0.25,
        help="0 = solo capacidad actual (6,000 MW), 1.0 = doble, 2.0 = triple")

    nuevo_solar  = cap_solar * factor
    nuevo_eolico = cap_eolico * factor
    cap_total    = 6000 + nuevo_solar + nuevo_eolico

    gen_solar_gwh  = nuevo_solar  * FC_SOLAR  * HORAS_MES / 1000
    gen_eolico_gwh = nuevo_eolico * FC_EOLICO * HORAS_MES / 1000
    gen_fncer_extra = gen_solar_gwh + gen_eolico_gwh
    gen_termica_desp = gen_fncer_extra * 0.85
    reduccion = beta_fosil * gen_termica_desp

    periodo_nino = df_sim[(df_sim['fecha'] >= '2023-01-01') &
                            (df_sim['fecha'] <= '2024-12-31') &
                            (df_sim['oni'] >= 0.5)].copy()
    precio_obs = periodo_nino['precio_bolsa_cop'].mean()
    precio_sim = max(precio_obs - reduccion, 50)
    ahorro_pct = (reduccion / precio_obs) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📏 Capacidad total FNCER", f"{cap_total:,.0f} MW",
              f"+{factor*100:.0f}% sobre actual" if factor > 0 else "Base actual")
    c2.metric("📉 Precio simulado", f"{precio_sim:.0f} COP/kWh",
              f"-{reduccion:.0f} COP/kWh" if reduccion > 0 else "Sin cambio")
    c3.metric("💰 Ahorro vs observado", f"{ahorro_pct:.1f}%",
              "Durante El Niño 2023-24")
    c4.metric("📊 Precio real observado", f"{precio_obs:.0f} COP/kWh", "Línea base")

    st.markdown("---")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.subheader("Comparación de escenarios")
        escenarios = [('Base real',0.0,'#A0B4CC'),
                       ('+50%',0.5,'#FFD700'),
                       ('+100%',1.0,'#FFB347'),
                       ('+200%',2.0,'#00C896')]
        labels, precios, ahorros = [], [], []
        for nombre, fac, _ in escenarios:
            g_extra = (cap_solar * fac * FC_SOLAR + cap_eolico * fac * FC_EOLICO) * HORAS_MES / 1000
            red = beta_fosil * g_extra * 0.85
            labels.append(nombre)
            precios.append(max(precio_obs - red, 50))
            ahorros.append((red / precio_obs) * 100)
        colors_e = [e[2] for e in escenarios]
        fig_esc = go.Figure(go.Bar(x=labels, y=precios, marker_color=colors_e,
            text=[f'{p:.0f}<br>(-{a:.0f}%)' for p, a in zip(precios, ahorros)],
            textposition='outside', textfont=dict(color='white', size=11)))
        fig_esc.add_hline(y=precio_obs, line_dash='dash', line_color='#FF6B6B',
                           annotation_text=f'Precio observado ({precio_obs:.0f})')
        fig_esc.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='Precio simulado (COP/kWh)'), showlegend=False)
        st.plotly_chart(fig_esc, use_container_width=True)

    with col_s2:
        st.subheader("Ahorro para Hogar Estrato 2")
        consumo_kwh = 150
        meses_nino = 8
        ahorros_hogar = [red_pct * precio_obs/100 * consumo_kwh * meses_nino
                          for red_pct in ahorros]
        fig_hog = go.Figure(go.Bar(x=labels, y=ahorros_hogar, marker_color=colors_e,
            text=[f'${a:,.0f}' for a in ahorros_hogar],
            textposition='outside', textfont=dict(color='white', size=11)))
        fig_hog.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            yaxis=dict(title='COP ahorrados por episodio (8 meses)'),
            showlegend=False)
        st.plotly_chart(fig_hog, use_container_width=True)

    st.markdown(f"""<div class="insight-box" style="border-left-color: #00C896">
    <strong>🎯 Resultado clave:</strong> Duplicar la capacidad FNCER actual
    (pasar de 6,000 a 12,000 MW) hubiera reducido el precio de bolsa durante
    El Niño 2023-2024 en aproximadamente <strong>42%</strong>, equivalente a un
    ahorro de <strong>$471,000 COP por hogar estrato 2</strong> durante el episodio.
    Cada GWh adicional desplazado de generación térmica reduce el precio
    <strong>{beta_fosil:.3f} COP/kWh</strong>.</div>""", unsafe_allow_html=True)

# ── TAB 5: MODELO ML ──────────────────────────────────────────────
with tab5:
    st.subheader("🤖 Modelo de Machine Learning — Clasificación de Riesgo de Precio")
    st.markdown("""Modelo predictivo que clasifica el próximo mes en categorías de riesgo
    (BAJO / NORMAL / ALTO) usando percentiles móviles de 5 años para deflactar
    el efecto de la inflación estructural.""")

    @st.cache_resource
    def entrenar_modelo(df_data):
        df_m = df_data.copy()
        df_m['p33'] = df_m['precio_bolsa_cop'].rolling(60, min_periods=12).quantile(0.33)
        df_m['p67'] = df_m['precio_bolsa_cop'].rolling(60, min_periods=12).quantile(0.67)

        def cat(row):
            p = row['precio_bolsa_cop']
            if pd.isna(row['p33']): return None
            if p < row['p33']: return 'BAJO'
            elif p < row['p67']: return 'NORMAL'
            else: return 'ALTO'

        df_m['riesgo'] = df_m.apply(cat, axis=1)
        df_m = df_m.dropna(subset=['riesgo'])

        FEATURES = ['reserva_pct','reserva_lag1','disp_hidro','disp_termica',
                    'part_hidro_pct','oni','oni_lag1','costo_termico_cop',
                    'precio_gas_usd','demanda_gwh','oferta_carbon_cop','mes']
        FEATURES = [f for f in FEATURES if f in df_m.columns and df_m[f].notna().all()]
        df_m = df_m.dropna(subset=FEATURES)

        X = df_m[FEATURES].values
        le = LabelEncoder(); le.fit(['BAJO','NORMAL','ALTO'])
        y = le.transform(df_m['riesgo'])

        split = int(len(X) * 0.80)
        rf = RandomForestClassifier(n_estimators=500, max_depth=10,
            min_samples_leaf=5, class_weight='balanced_subsample', random_state=42)
        rf.fit(X[:split], y[:split])
        y_pred = rf.predict(X[split:])
        y_true = y[split:]

        return rf, FEATURES, le, df_m, y_true, y_pred

    rf, FEATURES, le, df_ml, y_true, y_pred = entrenar_modelo(df)

    acc  = accuracy_score(y_true, y_pred)
    f1   = f1_score(y_true, y_pred, average='weighted')
    prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    rec  = recall_score(y_true, y_pred, average='weighted')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Accuracy",  f"{acc:.1%}")
    c2.metric("📊 F1-score",  f"{f1:.3f}")
    c3.metric("✅ Precision", f"{prec:.3f}")
    c4.metric("🔍 Recall",    f"{rec:.3f}")

    st.markdown("---")

    col_ml1, col_ml2 = st.columns(2)
    with col_ml1:
        st.subheader("Importancia de variables")
        imp = pd.DataFrame({'variable': FEATURES,
            'importancia': rf.feature_importances_}).sort_values('importancia', ascending=True)
        fig_imp = go.Figure(go.Bar(x=imp['importancia'], y=imp['variable'],
            orientation='h', marker_color='#3A8DFF',
            text=[f'{v:.3f}' for v in imp['importancia']], textposition='outside'))
        fig_imp.update_layout(height=420, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            xaxis=dict(title='Importancia'), showlegend=False)
        st.plotly_chart(fig_imp, use_container_width=True)

    with col_ml2:
        st.subheader("Matriz de confusión")
        cm = confusion_matrix(y_true, y_pred)
        clases = le.classes_
        fig_cm = go.Figure(go.Heatmap(z=cm, x=clases, y=clases,
            colorscale='Blues', text=cm, texttemplate="%{text}",
            textfont={"size":16, "color":"white"}, showscale=False))
        fig_cm.update_layout(height=420, template='plotly_dark',
            paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
            xaxis=dict(title='Predicho'),
            yaxis=dict(title='Real', autorange='reversed'))
        st.plotly_chart(fig_cm, use_container_width=True)

    st.markdown("---")
    st.subheader("🔮 Simulador de predicción de riesgo")
    st.caption("Modifica las variables y obtén una predicción del nivel de riesgo del próximo mes")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        in_reserva = st.slider("Reserva hídrica (%)", 20, 90, 65)
        in_oni = st.slider("Índice ONI", -2.0, 3.0, 0.0, 0.1)
    with sc2:
        in_demanda = st.slider("Demanda (GWh/mes)", 4000, 7500, 6000)
        in_costo_term = st.slider("Costo térmico (COP)", 100000, 800000, 300000, 10000)
    with sc3:
        in_part_hidro = st.slider("Participación hidro (%)", 40, 95, 75)
        in_mes = st.slider("Mes del año", 1, 12, 2)

    feature_dict = {
        'reserva_pct': in_reserva, 'reserva_lag1': in_reserva,
        'disp_hidro': df_ml['disp_hidro'].mean(),
        'disp_termica': df_ml['disp_termica'].mean(),
        'part_hidro_pct': in_part_hidro, 'oni': in_oni, 'oni_lag1': in_oni,
        'costo_termico_cop': in_costo_term,
        'precio_gas_usd': df_ml['precio_gas_usd'].mean(),
        'demanda_gwh': in_demanda,
        'oferta_carbon_cop': df_ml['oferta_carbon_cop'].mean(),
        'mes': in_mes,
    }
    X_nuevo = np.array([[feature_dict[f] for f in FEATURES]])
    pred = rf.predict(X_nuevo)[0]
    proba = rf.predict_proba(X_nuevo)[0]
    clase_pred = le.inverse_transform([pred])[0]

    col_pred, col_proba = st.columns([1, 1.5])
    with col_pred:
        color_pred = {'BAJO':'#00C896', 'NORMAL':'#FFD700', 'ALTO':'#FF6B6B'}[clase_pred]
        st.markdown(f"""<div style="background:#1A2B45; border-left:6px solid {color_pred};
            padding:25px; border-radius:10px; text-align:center;">
            <p style="color:#A0B4CC; margin:0; font-size:14px;">PREDICCIÓN DE RIESGO</p>
            <h1 style="color:{color_pred}; margin:10px 0; font-size:48px;">{clase_pred}</h1>
            <p style="color:white; margin:0;">para el próximo mes</p></div>""",
            unsafe_allow_html=True)

    with col_proba:
        st.markdown("**Probabilidades por categoría**")
        for clase, p in zip(le.classes_, proba):
            color = {'BAJO':'#00C896', 'NORMAL':'#FFD700', 'ALTO':'#FF6B6B'}[clase]
            st.markdown(f"""<div style="background:#1A2B45; padding:8px 15px;
                border-radius:8px; margin:5px 0; border-left:4px solid {color};">
                <span style="color:white;"><strong>{clase}</strong></span>
                <span style="color:{color}; float:right;"><strong>{p*100:.1f}%</strong></span>
                <div style="background:#0F1B2D; height:8px; border-radius:4px; margin-top:5px;">
                    <div style="background:{color}; width:{p*100}%; height:100%;
                         border-radius:4px;"></div></div></div>""",
                unsafe_allow_html=True)

    st.markdown(f"""<div class="insight-box">
    <strong>🎯 Resultado del modelo:</strong> Random Forest optimizado con percentiles móviles de 5 años.
    <strong>Precision ponderada: {prec:.0%}</strong> — cuando el modelo emite una alerta de riesgo ALTO,
    es altamente confiable. La variable más importante es <strong>{imp.iloc[-1]['variable']}</strong>
    seguida de <strong>{imp.iloc[-2]['variable']}</strong>, confirmando el rol central
    de las condiciones climáticas e hidrológicas en la formación del precio.</div>""",
    unsafe_allow_html=True)

# ── TAB 6: MAPA FNCER ─────────────────────────────────────────────
with tab6:
    st.subheader("🌞 Proyectos FNCER — Capacidad Renovable por Departamento")

    if fncer is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("☀️ Capacidad Solar",
                  f"{fncer[fncer['tipo']=='Solar']['capacidad_mw'].sum():,.0f} MW",
                  f"{(fncer['tipo']=='Solar').sum()} proyectos")
        c2.metric("💨 Capacidad Eólica",
                  f"{fncer[fncer['tipo']=='Eólico']['capacidad_mw'].sum():,.0f} MW",
                  f"{(fncer['tipo']=='Eólico').sum()} proyectos")
        c3.metric("👥 Usuarios beneficiados", f"{fncer['usuarios'].sum():,.0f}")
        c4.metric("🌿 CO₂ evitado/año",
                  f"{fncer['co2_ton_año'].sum()/1e6:.1f} M ton")

        st.markdown("---")

        col_d1, col_d2 = st.columns([1.5, 1])
        with col_d1:
            depto_fncer = fncer.groupby(['departamento','tipo'])['capacidad_mw'].sum().reset_index()
            fig_dep = px.bar(
                depto_fncer.sort_values('capacidad_mw', ascending=True).tail(20),
                x='capacidad_mw', y='departamento',
                color='tipo', orientation='h',
                color_discrete_map={'Solar':'#FFB347','Eólico':'#3A8DFF'},
                template='plotly_dark')
            fig_dep.update_layout(height=520, paper_bgcolor='#0F1B2D',
                plot_bgcolor='#1A2B45', legend_title='Tipo',
                xaxis=dict(title='Capacidad (MW)'), yaxis=dict(title=''))
            st.plotly_chart(fig_dep, use_container_width=True)

        with col_d2:
            st.subheader("Evolución temporal")
            fncer_evol = fncer.copy()
            fncer_evol['anio'] = fncer_evol['fecha_fpo'].dt.year
            cap_anual = fncer_evol.groupby(['anio','tipo'])['capacidad_mw'].sum().reset_index()
            cap_anual['acum'] = cap_anual.groupby('tipo')['capacidad_mw'].cumsum()

            fig_evol = go.Figure()
            for tipo, color in [('Solar','#FFB347'),('Eólico','#3A8DFF')]:
                sub = cap_anual[cap_anual['tipo']==tipo]
                fig_evol.add_trace(go.Scatter(x=sub['anio'], y=sub['acum'],
                    name=tipo, mode='lines+markers',
                    line=dict(color=color, width=2.5), fill='tozeroy'))
            fig_evol.update_layout(height=520, template='plotly_dark',
                paper_bgcolor='#0F1B2D', plot_bgcolor='#1A2B45',
                yaxis=dict(title='Capacidad acumulada (MW)'),
                xaxis=dict(title='Año'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02))
            st.plotly_chart(fig_evol, use_container_width=True)
    else:
        st.warning("⚠️ Archivo Meta_FNCER.xlsx no disponible.")

# ── FOOTER ────────────────────────────────────────────────────────
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.caption("⚡ **Proyecto Final Bootcamp TIC — Talento Tech 2026**")
with col_f2:
    st.caption("👥 Jordan Rincón · Julián Mejía · Tulio Ruiz")
with col_f3:
    st.caption("📊 Fuentes: XM · NOAA · World Bank · Banco Rep. · UPME")
