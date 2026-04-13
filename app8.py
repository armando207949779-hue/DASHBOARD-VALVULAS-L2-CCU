"""
Dashboard de Mantenimiento de Válvulas Krones - Llenadora CCU Línea 2
Streamlit App para GitHub + Streamlit Cloud
Conectado a Google Sheets
VERSIÓN 2.0 LÍNEA 2: 112 válvulas, 5 tipos de mantención
Orden: general → específico
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

# ============================================================================
# CONFIG STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="Dashboard Válvulas Krones Línea 2",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

st.markdown("""
    <style>
    .main { padding: 1.5rem; }
    h1 { text-align: center; margin-bottom: 0.3rem; }
    h2 { border-bottom: 2px solid #3498db; padding-bottom: 0.4rem; }
    .stMetric { border-radius: 0.5rem; padding: 0.5rem; border: 1px solid rgba(128,128,128,0.2); }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# PALETA GLOBAL
# ============================================================================

# Colores fijos por tipo de mantención (usados en Fig 9 y mantención)
COLORS_MANTENCION = {
    'O-RINGS':            '#e74c3c',
    'BLOQUE':             '#3498db',
    'RESORTE':            '#2ecc71',
    'ON/OFF':             '#f39c12',
    'OTRO (ESPECIFICAR)': '#9b59b6',
}

_GRID  = 'rgba(128,128,128,0.15)'
_LINE  = 'rgba(128,128,128,0.30)'
_HOVER = dict(bgcolor='white', font_size=12, bordercolor='#cccccc')


def _base(fig, title, height, l=70, r=65, t=65, b=55):
    """Aplica layout base consistente a todos los gráficos."""
    fig.update_layout(
        title=dict(
            text=f'<b>{title}</b>',
            font=dict(size=14, color='#1a237e', family='Arial, sans-serif'),
            x=0.01
        ),
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=l, r=r, t=t, b=b),
        font=dict(family='Arial, sans-serif', size=11),
        hoverlabel=_HOVER,
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=_GRID, zeroline=False,
        showline=True, linecolor=_LINE, linewidth=1
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=_GRID, zeroline=False,
        showline=True, linecolor=_LINE, linewidth=1
    )
    return fig


# ============================================================================
# 1. CARGAR DATOS DESDE GOOGLE SHEETS
# ============================================================================

@st.cache_data(ttl=1)
def load_data_from_sheets():
    sheet_id = "1Rai9jsZ5Qr_MdicutlvHfT3pwzENKNSD-TOW8iVknMk"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(csv_url)
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')

        columnas_requeridas = ['Fecha', 'Turno', 'Operador', 'Válvula', 'Mantención']
        if not all(col in df.columns for col in columnas_requeridas):
            st.sidebar.warning("⚠️ Columnas faltantes. Usando datos de ejemplo.")
            return load_data_example()

        df['Válvula'] = pd.to_numeric(df['Válvula'], errors='coerce').astype('Int64')

        if 'Fotografia de la falla' in df.columns:
            df = df.drop(columns=['Fotografia de la falla'])

        df = df.dropna(subset=['Fecha', 'Válvula'])

        st.sidebar.success(f"✅ {len(df):,} registros cargados desde Google Sheets")
        return df

    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")
        st.sidebar.info("Usando datos de ejemplo...")
        return load_data_example()


@st.cache_data
def load_data_example():
    np.random.seed(42)
    fechas = pd.date_range('2025-01-15', '2026-04-10', freq='D')
    n = 500
    data = {
        'Fecha':    np.random.choice(fechas, n),
        'Turno':    np.random.choice(['A', 'B', 'C'], n),
        'Operador': np.random.choice(
            ['Didimo Valero', 'Jorge González', 'Richard Ruz', 'Juan Rupertus Mondaca'], n
        ),
        'Válvula':  np.random.choice(range(1, 113), n),
        'Mantención': np.random.choice(
            ['O-RINGS', 'BLOQUE', 'RESORTE', 'ON/OFF', 'OTRO (ESPECIFICAR)'], n
        ),
        'Descripción de falla': np.random.choice(
            ['Fuga menor', 'No cierra correctamente', 'Sonido anormal',
             'Fugas presión', 'Sin novedad', ''], n
        ),
        'Comentarios': [
            f'COMENTARIO {i+1}' if np.random.random() > 0.3 else '' for i in range(n)
        ]
    }
    df = pd.DataFrame(data)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df


# ============================================================================
# FIGURA 1 — TENDENCIA TEMPORAL (más general)
# ============================================================================

def grafico_tendencia(df):
    """Tendencia diaria de registros con media móvil 7 días."""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    df_tmp = df.copy()
    df_tmp['Fecha_dia'] = df_tmp['Fecha'].dt.date
    tend = df_tmp.groupby('Fecha_dia').size().reset_index(name='Registros')
    tend['Fecha_dia'] = pd.to_datetime(tend['Fecha_dia'])
    tend = tend.sort_values('Fecha_dia')
    tend['MA7'] = tend['Registros'].rolling(7, min_periods=1).mean()

    fig = go.Figure()

    # Área rellena
    fig.add_trace(go.Scatter(
        x=tend['Fecha_dia'], y=tend['Registros'],
        mode='lines+markers',
        name='Registros diarios',
        line=dict(color='#1e88e5', width=1.5),
        marker=dict(size=4, color='#1e88e5'),
        fill='tozeroy', fillcolor='rgba(30,136,229,0.10)',
        hovertemplate='<b>%{x|%d-%m-%Y}</b><br>Registros: %{y}<extra></extra>'
    ))

    # Media móvil 7 días
    fig.add_trace(go.Scatter(
        x=tend['Fecha_dia'], y=tend['MA7'].round(1),
        mode='lines', name='Media móvil 7 días',
        line=dict(color='#e53935', width=2, dash='dot'),
        hovertemplate='<b>%{x|%d-%m-%Y}</b><br>MA7: %{y:.1f}<extra></extra>'
    ))

    _base(fig, 'Tendencia Temporal de Registros de Mantención', 380, r=120)
    fig.update_layout(
        xaxis_title='Fecha', yaxis_title='Registros',
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'
        ),
        xaxis=dict(rangeslider=dict(visible=True, thickness=0.04))
    )
    return fig


# ============================================================================
# FIGURA 2 — REGISTROS POR TURNO
# ============================================================================

def grafico_turno(df):
    """Distribución de registros por turno (barras con % anotado)."""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    vc = df['Turno'].value_counts().reset_index()
    vc.columns = ['Turno', 'Cantidad']
    vc = vc.sort_values('Turno')
    total = vc['Cantidad'].sum()
    vc['Pct'] = (vc['Cantidad'] / total * 100).round(1)

    COLORES_TURNO = {'A': '#1e88e5', 'B': '#43a047', 'C': '#fb8c00'}
    colores = [COLORES_TURNO.get(t, '#607d8b') for t in vc['Turno']]

    fig = go.Figure(go.Bar(
        x=vc['Turno'], y=vc['Cantidad'],
        marker_color=colores,
        text=[f"{c}<br>({p}%)" for c, p in zip(vc['Cantidad'], vc['Pct'])],
        textposition='outside',
        hovertemplate='<b>Turno %{x}</b><br>Registros: %{y}<br>Porcentaje: %{customdata[0]:.1f}%<extra></extra>',
        customdata=vc[['Pct']].values
    ))
    _base(fig, 'Distribución de Registros por Turno', 360)
    fig.update_layout(xaxis_title='Turno', yaxis_title='Registros',
                      showlegend=False)
    fig.update_yaxes(range=[0, vc['Cantidad'].max() * 1.18])
    return fig


# ============================================================================
# FIGURA 3 — REGISTROS POR OPERADOR
# ============================================================================

def grafico_operador(df):
    """Registros por operador con barra horizontal y % anotado."""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    vc = df['Operador'].value_counts().reset_index()
    vc.columns = ['Operador', 'Cantidad']
    total = vc['Cantidad'].sum()
    vc['Pct'] = (vc['Cantidad'] / total * 100).round(1)
    vc = vc.sort_values('Cantidad', ascending=True)

    fig = go.Figure(go.Bar(
        y=vc['Operador'], x=vc['Cantidad'],
        orientation='h',
        marker=dict(color=vc['Cantidad'], colorscale='Teal', showscale=False),
        text=[f"{c}  ({p}%)" for c, p in zip(vc['Cantidad'], vc['Pct'])],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Registros: %{x}<br>%{customdata[0]:.1f}% del total<extra></extra>',
        customdata=vc[['Pct']].values
    ))
    _base(fig, 'Registros por Operador', max(360, 85 * len(vc)),
          l=160, r=90)
    fig.update_layout(xaxis_title='Registros', showlegend=False)
    fig.update_xaxes(range=[0, vc['Cantidad'].max() * 1.22])
    return fig


# ============================================================================
# FIGURA 4 — TIPOS DE MANTENCIÓN
# ============================================================================

def grafico_mantencion(df):
    """Tipos de mantención más frecuentes con colores fijos y % anotado."""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    mant = df['Mantención'].value_counts().reset_index()
    mant.columns = ['Mantención', 'Cantidad']
    total = mant['Cantidad'].sum()
    mant['Pct'] = (mant['Cantidad'] / total * 100).round(1)
    mant = mant.sort_values('Cantidad', ascending=True)

    colores = [COLORS_MANTENCION.get(m, '#607d8b') for m in mant['Mantención']]

    fig = go.Figure(go.Bar(
        y=mant['Mantención'], x=mant['Cantidad'],
        orientation='h',
        marker_color=colores,
        text=[f"{c}  ({p}%)" for c, p in zip(mant['Cantidad'], mant['Pct'])],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Registros: %{x}<br>%{customdata[0]:.1f}% del total<extra></extra>',
        customdata=mant[['Pct']].values
    ))
    _base(fig, 'Distribución por Tipo de Mantención', max(360, 90 * len(mant)),
          l=190, r=90)
    fig.update_layout(xaxis_title='Registros', showlegend=False)
    fig.update_xaxes(range=[0, mant['Cantidad'].max() * 1.22])
    return fig


# ============================================================================
# FIGURA 5 — TODAS LAS 112 VÁLVULAS
# ============================================================================

def crear_grafico_valvulas_principales(df_filtrado):
    """
    Barras verticales para las 112 válvulas (1-112).
    Gradiente de color proporcional a los registros; grises las sin registros.
    """
    todas = pd.DataFrame({'Válvula': range(1, 113)})

    if len(df_filtrado) > 0:
        cnt = df_filtrado['Válvula'].value_counts().reset_index()
        cnt.columns = ['Válvula', 'Registros']
        todas = todas.merge(cnt, on='Válvula', how='left')
        todas['Registros'] = todas['Registros'].fillna(0).astype(int)
    else:
        todas['Registros'] = 0

    todas['Label'] = 'V' + todas['Válvula'].astype(str)
    max_r = todas['Registros'].max() or 1
    prom  = todas[todas['Registros'] > 0]['Registros'].mean() if todas['Registros'].sum() > 0 else 0

    # Color: escala roja para con registros, gris para sin
    def _color(r):
        if r == 0:
            return '#cfd8dc'
        intensity = 0.35 + 0.65 * (r / max_r)
        red   = int(255 * intensity)
        blue  = int(30  * (1 - intensity))
        return f'rgb({red},{30},{blue})'

    colores = [_color(r) for r in todas['Registros']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=todas['Label'], y=todas['Registros'],
        marker_color=colores,
        text=todas['Registros'].apply(lambda v: str(v) if v > 0 else ''),
        textposition='outside',
        textfont=dict(size=7),
        hovertemplate='<b>Válvula %{x}</b><br>Registros: %{y}<extra></extra>'
    ))

    # Línea de promedio
    if prom > 0:
        fig.add_hline(
            y=prom, line_dash='dash', line_color='#f57c00', line_width=1.5,
            annotation_text=f'Promedio: {prom:.1f}',
            annotation_position='top right',
            annotation_font=dict(color='#f57c00', size=11)
        )

    _base(fig, 'Registros de Mantención por Válvula (1 – 112)', 460, l=65, r=80)
    fig.update_layout(
        xaxis_title='Válvula', yaxis_title='Registros',
        xaxis=dict(
            tickfont=dict(size=7), tickangle=45,
            rangeslider=dict(visible=True, thickness=0.04)
        ),
    )
    fig.update_yaxes(range=[0, max_r * 1.20])
    return fig


# ============================================================================
# FIGURA 6 — TOP 15 VÁLVULAS
# ============================================================================

def grafico_top_valvulas(df):
    """Top 15 válvulas con más mantenimientos — con % sobre el total."""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    top = df['Válvula'].value_counts().head(15).reset_index()
    top.columns = ['Válvula', 'Cantidad']
    total = len(df)
    top['Pct'] = (top['Cantidad'] / total * 100).round(1)
    top['Label'] = 'Válvula ' + top['Válvula'].astype(str)
    top = top.sort_values('Cantidad', ascending=True)

    fig = go.Figure(go.Bar(
        y=top['Label'], x=top['Cantidad'],
        orientation='h',
        marker=dict(color=top['Cantidad'], colorscale='Reds', showscale=False,
                    line=dict(width=0)),
        text=[f"{c}  ({p}%)" for c, p in zip(top['Cantidad'], top['Pct'])],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Registros: %{x}<br>%{customdata[0]:.1f}% del total<extra></extra>',
        customdata=top[['Pct']].values
    ))
    _base(fig, 'Top 15 Válvulas con Mayor Número de Mantenciones', max(380, 42 * len(top)),
          l=130, r=95)
    fig.update_layout(xaxis_title='Registros', showlegend=False)
    fig.update_xaxes(range=[0, top['Cantidad'].max() * 1.25])
    return fig


# ============================================================================
# FIGURA 7 — HEATMAP: VÁLVULA × TIPO DE MANTENCIÓN
# ============================================================================

def grafico_mantencion_por_valvula(df):
    """
    Heatmap: todas las 112 válvulas × tipos de mantención.
    Hover con resumen de Descripción y Comentarios.
    """
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    tipos = sorted(df['Mantención'].unique())
    # Pre-agregar conteos
    resumen = (
        df.groupby(['Válvula', 'Mantención'])
          .agg(
              Conteo=('Mantención', 'count'),
              Desc=('Descripción de falla',
                    lambda x: '; '.join(set(v for v in x if v and str(v) != 'nan'))[:60]),
              Coment=('Comentarios',
                      lambda x: '; '.join(set(v for v in x if v and str(v) != 'nan'))[:60])
          )
          .reset_index()
    )

    matriz_z     = np.zeros((112, len(tipos)))
    matriz_hover = [['' for _ in tipos] for _ in range(112)]

    for _, row in resumen.iterrows():
        vi = int(row['Válvula']) - 1
        ti = tipos.index(row['Mantención'])
        if 0 <= vi < 112:
            matriz_z[vi, ti] = row['Conteo']
            h = (f"<b>Válvula {int(row['Válvula'])}</b><br>"
                 f"<b>{row['Mantención']}</b><br>"
                 f"Registros: {int(row['Conteo'])}")
            if row['Desc']:
                h += f"<br><i>Desc:</i> {row['Desc']}"
            if row['Coment']:
                h += f"<br><i>Coment:</i> {row['Coment']}"
            matriz_hover[vi][ti] = h

    # Llenar hover vacíos
    for vi in range(112):
        for ti in range(len(tipos)):
            if not matriz_hover[vi][ti]:
                matriz_hover[vi][ti] = f"<b>Válvula {vi+1}</b><br>{tipos[ti]}<br>Sin registros"

    etiquetas_y = [f"V{i+1}" for i in range(112)]

    fig = go.Figure(go.Heatmap(
        z=matriz_z,
        x=tipos,
        y=etiquetas_y,
        colorscale='YlOrRd',
        hovertext=matriz_hover,
        hoverinfo='text',
        colorbar=dict(
            title=dict(text='Registros', side='right'),
            thickness=14, len=0.8
        )
    ))
    _base(fig, 'Heatmap: Válvula × Tipo de Mantención (112 válvulas)',
          900, l=55, r=100, t=65, b=55)
    fig.update_layout(
        xaxis_title='Tipo de Mantención',
        yaxis_title='Válvula',
        yaxis=dict(tickfont=dict(size=7))
    )
    return fig


# ============================================================================
# FIGURA 8 — BURBUJAS: TIPO DE MANTENCIÓN × VÁLVULA (eje Y numérico)
# ============================================================================

def grafico_burbujas_valvula_mantencion(df):
    """
    Mapa de burbujas: eje X = Tipo de Mantención (5 categorías),
    eje Y = N° de válvula (numérico 1-112, ordenado correctamente).
    Solo muestra combinaciones con ≥1 registro.
    Tamaño y color de burbuja = cantidad de registros.
    """
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    resumen = (
        df.groupby(['Mantención', 'Válvula'])
          .size()
          .reset_index(name='Cantidad')
    )

    tipos   = sorted(resumen['Mantención'].unique())
    tipo_x  = {t: i for i, t in enumerate(tipos)}   # posición X numérica
    resumen['X'] = resumen['Mantención'].map(tipo_x)

    max_c = resumen['Cantidad'].max()
    # Sizeref: ajusta para que la burbuja más grande tenga ~40px de radio
    sizeref = 2.0 * max_c / (40 ** 2)

    fig = go.Figure(go.Scatter(
        x=resumen['X'],
        y=resumen['Válvula'].astype(int),
        mode='markers',
        marker=dict(
            size=resumen['Cantidad'],
            sizemode='area',
            sizeref=sizeref,
            sizemin=4,
            color=resumen['Cantidad'],
            colorscale='YlOrRd',
            showscale=True,
            colorbar=dict(
                title=dict(text='Registros', side='right'),
                thickness=14, len=0.75
            ),
            line=dict(width=0.6, color='white'),
            opacity=0.88
        ),
        text=resumen['Cantidad'],
        customdata=resumen[['Mantención', 'Válvula', 'Cantidad']].values,
        hovertemplate=(
            '<b>Válvula %{y}</b><br>'
            'Mantención: %{customdata[0]}<br>'
            'Registros: %{customdata[2]}<extra></extra>'
        )
    ))

    # Etiquetas X personalizadas
    fig.update_xaxes(
        tickmode='array',
        tickvals=list(tipo_x.values()),
        ticktext=list(tipo_x.keys()),
        tickfont=dict(size=11),
        title_text='Tipo de Mantención'
    )
    fig.update_yaxes(
        title_text='N° de Válvula',
        autorange='reversed',   # V1 arriba, V112 abajo
        tickmode='linear', dtick=10,
        tickfont=dict(size=9),
        range=[113, 0]
    )

    _base(fig, 'Mapa de Burbujas: Tipo de Mantención × N° de Válvula',
          900, l=70, r=110, t=65, b=65)
    fig.update_layout(showlegend=False)
    return fig


# ============================================================================
# FIGURA 9 — BURBUJAS: POSICIÓN DE VÁLVULA × TIPO (eje X continuo 1-112)
# ============================================================================

def grafico_burbujas_numero_valvula_tipo(df):
    """
    Mapa de burbujas: eje X = N° de válvula (1-112, continuo),
    eje Y = Tipo de mantención (5 filas categóricas).
    Color fijo por tipo de mantención; tamaño = cantidad de registros.
    Permite identificar zonas de la llenadora con alta incidencia.
    """
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    resumen = (
        df.groupby(['Válvula', 'Mantención'])
          .size()
          .reset_index(name='Cantidad')
    )

    tipos    = sorted(resumen['Mantención'].unique())
    tipo_y   = {t: i for i, t in enumerate(tipos)}  # posición Y numérica
    resumen['Y'] = resumen['Mantención'].map(tipo_y)

    max_c    = resumen['Cantidad'].max()
    sizeref  = 2.0 * max_c / (35 ** 2)

    fig = go.Figure()

    for tipo in tipos:
        sub = resumen[resumen['Mantención'] == tipo]
        color = COLORS_MANTENCION.get(tipo, '#607d8b')
        fig.add_trace(go.Scatter(
            x=sub['Válvula'].astype(int),
            y=sub['Y'],
            mode='markers',
            name=tipo,
            marker=dict(
                size=sub['Cantidad'],
                sizemode='area',
                sizeref=sizeref,
                sizemin=5,
                color=color,
                opacity=0.82,
                line=dict(width=0.8, color='white')
            ),
            customdata=sub[['Mantención', 'Cantidad']].values,
            hovertemplate=(
                '<b>Válvula %{x}</b><br>'
                'Mantención: %{customdata[0]}<br>'
                'Registros: %{customdata[1]}<extra></extra>'
            )
        ))

    # Etiquetas Y personalizadas
    fig.update_yaxes(
        tickmode='array',
        tickvals=list(tipo_y.values()),
        ticktext=list(tipo_y.keys()),
        tickfont=dict(size=11),
        title_text='Tipo de Mantención',
        showgrid=True, gridcolor=_GRID
    )
    fig.update_xaxes(
        title_text='N° de Válvula',
        tickmode='linear', dtick=5,
        range=[0, 113],
        tickfont=dict(size=9),
        showgrid=True, gridcolor=_GRID
    )

    _base(fig, 'Distribución de Mantenciones a lo Largo de la Llenadora (Válvulas 1 – 112)',
          540, l=195, r=65, t=65, b=60)
    fig.update_layout(
        legend=dict(
            title_text='Tipo',
            orientation='v',
            yanchor='middle', y=0.5,
            xanchor='left', x=1.01,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=10)
        ),
        showlegend=True
    )
    return fig


# ============================================================================
# 5. INTERFAZ STREAMLIT
# ============================================================================

df = load_data_from_sheets()

# TÍTULO
st.markdown("""
<div style='text-align:center; margin-bottom:1.2rem;'>
  <h1 style='margin-bottom:0.2rem;'>🏭 Dashboard Mantenimiento Válvulas Krones · Línea 2</h1>
  <p style='font-size:1.05rem; margin:0.1rem 0;'>Llenadora CCU</p>
  <p style='font-size:0.9rem; opacity:0.7; margin:0;'>
    Elaborado por: <b>Enrique Brun</b> · Jefe de Operaciones: <b>Gastón Flores</b>
  </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR — FILTROS
# ============================================================================

st.sidebar.markdown("## 🔍 Filtros")

fecha_min = df['Fecha'].min()
fecha_max = df['Fecha'].max()

col_f1, col_f2 = st.sidebar.columns(2)
with col_f1:
    fecha_inicio = st.date_input(
        "Desde", value=fecha_min.date(),
        min_value=fecha_min.date(), max_value=fecha_max.date()
    )
with col_f2:
    fecha_fin = st.date_input(
        "Hasta", value=fecha_max.date(),
        min_value=fecha_min.date(), max_value=fecha_max.date()
    )

turnos_opc      = sorted(df['Turno'].dropna().unique())
operadores_opc  = sorted(df['Operador'].dropna().unique())
mantencion_opc  = sorted(df['Mantención'].dropna().unique())
valvulas_opc    = list(range(1, 113))

turnos_sel     = st.sidebar.multiselect("Turnos",             turnos_opc,     default=turnos_opc)
operadores_sel = st.sidebar.multiselect("Operadores",         operadores_opc, default=operadores_opc)
mantencion_sel = st.sidebar.multiselect("Tipos de Mantención",mantencion_opc, default=mantencion_opc)
valvulas_sel   = st.sidebar.multiselect("N° de Válvula",      valvulas_opc,   default=valvulas_opc)

# Aplicar filtros
df_f = df[
    (df['Fecha'].dt.date >= fecha_inicio) &
    (df['Fecha'].dt.date <= fecha_fin) &
    (df['Turno'].isin(turnos_sel)) &
    (df['Operador'].isin(operadores_sel)) &
    (df['Mantención'].isin(mantencion_sel)) &
    (df['Válvula'].isin(valvulas_sel))
].copy()

# ============================================================================
# MÉTRICAS
# ============================================================================

st.markdown("### 📊 KPIs")
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📝 Total Registros",    f"{len(df_f):,}")
with m2:
    st.metric("📅 Días Activos",       df_f['Fecha'].nunique())
with m3:
    st.metric("👥 Operadores",         df_f['Operador'].nunique())
with m4:
    st.metric("🔧 Válvulas Afectadas", df_f['Válvula'].nunique())
with m5:
    prom = len(df_f) / max(df_f['Fecha'].nunique(), 1)
    st.metric("📊 Reg/Día Prom.",      f"{prom:.1f}")

# ============================================================================
# GRÁFICOS — orden: general → específico
# ============================================================================

st.markdown("---")

if len(df_f) == 0:
    st.warning("⚠️ Sin datos para los filtros seleccionados.")
else:

    # ── FIGURA 1: Tendencia temporal ────────────────────────────────────────
    st.markdown("### Figura 1 · Tendencia Temporal de Registros")
    st.caption(
        "Evolución diaria del total de registros ingresados. "
        "La línea punteada corresponde a la media móvil de 7 días."
    )
    st.plotly_chart(grafico_tendencia(df_f), use_container_width=True)

    # ── FIGURAS 2 Y 3: Turno y Operador ─────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Figura 2 · Registros por Turno")
        st.plotly_chart(grafico_turno(df_f), use_container_width=True)
    with col2:
        st.markdown("#### Figura 3 · Registros por Operador")
        st.plotly_chart(grafico_operador(df_f), use_container_width=True)

    # ── FIGURA 4: Tipos de mantención ───────────────────────────────────────
    st.markdown("---")
    st.markdown("### Figura 4 · Distribución por Tipo de Mantención")
    st.plotly_chart(grafico_mantencion(df_f), use_container_width=True)

    # ── FIGURA 5: Todas las 112 válvulas ────────────────────────────────────
    st.markdown("---")
    st.markdown("### Figura 5 · Registros por Válvula (1 – 112)")
    st.caption(
        "Incluye todas las válvulas, con y sin registros en el período filtrado. "
        "La línea naranja indica el promedio de las válvulas con al menos un registro."
    )
    st.plotly_chart(crear_grafico_valvulas_principales(df_f), use_container_width=True)

    # ── FIGURA 6: Top 15 ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Figura 6 · Top 15 Válvulas con Mayor Número de Mantenciones")
    st.plotly_chart(grafico_top_valvulas(df_f), use_container_width=True)

    # ── FIGURA 7: Heatmap ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Figura 7 · Heatmap: Válvula × Tipo de Mantención")
    st.caption(
        "Cada celda muestra el total de registros para esa combinación. "
        "Pase el cursor para ver descripción de falla y comentarios (si existen)."
    )
    st.plotly_chart(grafico_mantencion_por_valvula(df_f), use_container_width=True)

    # ── FIGURA 8: Burbujas (Mantención × Válvula, Y numérico) ───────────────
    st.markdown("---")
    st.markdown("### Figura 8 · Mapa de Burbujas: Tipo de Mantención × N° de Válvula")
    st.caption(
        "Eje X: tipo de mantención (5 columnas). Eje Y: número de válvula (1 arriba → 112 abajo). "
        "El tamaño y color de la burbuja representan la cantidad de registros. "
        "Solo se muestran combinaciones con al menos 1 registro."
    )
    st.plotly_chart(grafico_burbujas_valvula_mantencion(df_f), use_container_width=True)

    # ── FIGURA 9: Burbujas (Válvula continua × Tipo) ────────────────────────
    st.markdown("---")
    st.markdown("### Figura 9 · Distribución de Mantenciones a lo Largo de la Llenadora")
    st.caption(
        "Eje X: posición de la válvula (1 – 112). Eje Y: tipo de mantención. "
        "Cada color representa un tipo; el tamaño muestra cuántos registros tiene esa combinación. "
        "Permite identificar zonas de la máquina con mayor concentración de fallas."
    )
    st.plotly_chart(grafico_burbujas_numero_valvula_tipo(df_f), use_container_width=True)


# ============================================================================
# TABLA Y DESCARGA
# ============================================================================

st.markdown("---")
st.markdown("### 📋 Datos Detallados")

if st.checkbox("Mostrar tabla completa"):
    df_show = df_f.copy()
    df_show['Fecha'] = df_show['Fecha'].dt.strftime('%d-%m-%Y')
    df_show = df_show.drop(columns=['Fotografia de la falla'], errors='ignore')
    st.dataframe(df_show, use_container_width=True, height=400)

col1, col2 = st.columns(2)
with col1:
    df_dl = df_f.copy()
    df_dl['Fecha'] = df_dl['Fecha'].dt.strftime('%d-%m-%Y')
    df_dl = df_dl.drop(columns=['Fotografia de la falla'], errors='ignore')
    st.download_button(
        "⬇️ Descargar CSV",
        df_dl.to_csv(index=False).encode('utf-8'),
        file_name=f"valvulas_krones_linea2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ============================================================================
# SIDEBAR INFO
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 Fuente de Datos")
fmt_min = df['Fecha'].min().strftime('%d-%m-%Y') if pd.notna(df['Fecha'].min()) else 'N/A'
fmt_max = df['Fecha'].max().strftime('%d-%m-%Y') if pd.notna(df['Fecha'].max()) else 'N/A'
st.sidebar.info(
    f"**Google Sheets** (caché 1 segundo)\n\n"
    f"- {len(df):,} registros totales\n"
    f"- Período: {fmt_min} → {fmt_max}\n"
    f"- Válvulas: hasta 112\n"
    f"- Tipos: O-RINGS, BLOQUE, RESORTE, ON/OFF, OTRO\n"
    f"- Operadores: {df['Operador'].nunique()}\n"
    f"- Turnos: {', '.join(sorted(df['Turno'].dropna().unique()))}"
)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;opacity:0.6;font-size:0.82rem;'>"
    "<b>Dashboard Mantenimiento Válvulas Krones Línea 2</b> · Llenadora CCU<br>"
    "Streamlit + Plotly · v2.0"
    "</div>",
    unsafe_allow_html=True
)
