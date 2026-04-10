"""
Dashboard de Mantenimiento de Válvulas Krones - Llenadora CCU Línea 2
Streamlit App para GitHub + Streamlit Cloud
Conectado a Google Sheets
VERSIÓN 1.0 LÍNEA 2: 112 válvulas, 5 tipos de mantención
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import re

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
# 1. CARGAR DATOS DESDE GOOGLE SHEETS
# ============================================================================

@st.cache_data(ttl=3600)
def load_data_from_sheets():
    """Carga datos desde Google Sheets de Válvulas Krones"""
    sheet_id = "1Rai9jsZ5Qr_MdicutlvHfT3pwzENKNSD-TOW8iVknMk"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    try:
        df = pd.read_csv(csv_url)
        
        # Convertir Fecha
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')

        # Columnas requeridas
        columnas_requeridas = ['Fecha', 'Turno', 'Operador', 'Válvula', 'Mantención']
        if not all(col in df.columns for col in columnas_requeridas):
            st.sidebar.warning("⚠️ Columnas faltantes. Usando datos de ejemplo.")
            return load_data_example()

        # Convertir Válvula a numérica
        df['Válvula'] = pd.to_numeric(df['Válvula'], errors='coerce').astype('Int64')
        
        # Eliminar fotografía si existe (no la mostramos en el dashboard)
        if 'Fotografia de la falla' in df.columns:
            df = df.drop(columns=['Fotografia de la falla'])
        
        # Mantener columnas Descripción de falla y Comentarios si existen
        # (se usan en hover del heatmap)
        
        # Eliminar registros sin fecha o válvula
        df = df.dropna(subset=['Fecha', 'Válvula'])

        n = len(df)
        st.sidebar.success(f"✅ {n:,} registros cargados desde Google Sheets")
        return df

    except Exception as e:
        st.sidebar.error(f"❌ Error: {e}")
        st.sidebar.info("Usando datos de ejemplo...")
        return load_data_example()


@st.cache_data
def load_data_example():
    """Genera datos de ejemplo para pruebas"""
    np.random.seed(42)
    fechas = pd.date_range('2025-01-15', '2026-04-10', freq='D')
    n = 500
    
    data = {
        'Fecha':    np.random.choice(fechas, n),
        'Turno':    np.random.choice(['A', 'B', 'C'], n),
        'Operador': np.random.choice(['Didimo Valero', 'Jorge González', 'Richard Ruz', 'Juan Rupertus Mondaca'], n),
        'Válvula':  np.random.choice(range(1, 113), n),
        'Mantención': np.random.choice(['O-RINGS', 'BLOQUE', 'RESORTE', 'ON/OFF', 'OTRO (ESPECIFICAR)'], n),
        'Descripción de falla': np.random.choice([
            'Fuga menor', 'No cierra correctamente', 'Sonido anormal', 
            'Fugas presión', 'Sin novedad', 'HOLA', ''
        ], n),
        'Comentarios': [f'COMENTARIO {i+1}' if np.random.random() > 0.3 else '' for i in range(n)]
    }
    df = pd.DataFrame(data)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df


# ============================================================================
# 2. VISUALIZACIÓN PRINCIPAL: GRÁFICO DE VÁLVULAS REGISTRADAS
# ============================================================================

def crear_grafico_valvulas_principales(df_filtrado):
    """
    Crea un gráfico de barras VERTICAL que muestra TODAS las 112 válvulas
    ordenadas de 1 a 112, independientemente de si tienen registros o no.
    Incluye barra deslizadora para navegar.
    """
    # Crear serie con todas las válvulas 1-112
    todas_valvulas = pd.DataFrame({'Válvula': range(1, 113)})
    
    # Contar registros por válvula
    if len(df_filtrado) > 0:
        conteos = df_filtrado['Válvula'].value_counts().reset_index()
        conteos.columns = ['Válvula', 'Registros']
        todas_valvulas = todas_valvulas.merge(conteos, on='Válvula', how='left')
        todas_valvulas['Registros'] = todas_valvulas['Registros'].fillna(0).astype(int)
    else:
        todas_valvulas['Registros'] = 0
    
    # Crear etiquetas
    todas_valvulas['Válvula_label'] = 'V' + todas_valvulas['Válvula'].astype(str)
    
    # Determinar colores: rojo si tiene registros, gris claro si no
    colores = ['#d32f2f' if r > 0 else '#b0bec5' for r in todas_valvulas['Registros']]
    
    # Crear gráfico de barras vertical
    fig = go.Figure(go.Bar(
        x=todas_valvulas['Válvula_label'],
        y=todas_valvulas['Registros'],
        marker=dict(color=colores),
        text=todas_valvulas['Registros'],
        textposition='outside',
        hovertemplate='<b>Válvula %{x}</b><br>Registros: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text='<b>Registros de Mantenimiento por Válvula (1-112)</b>', font=dict(size=14, color='#2c3e50')),
        xaxis_title='Válvula',
        yaxis_title='Cantidad de Registros',
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=70, r=60, t=70, b=60),
        xaxis=dict(
            tickfont=dict(size=8),
            tickangle=45
        ),
        yaxis=dict(tickfont=dict(size=10)),
        hovermode='closest',
        # Agregar rangeslider (barra deslizadora)
        xaxis_rangeslider=dict(visible=True, thickness=0.05)
    )
    
    return fig


# ============================================================================
# 4. GRÁFICOS DE ANÁLISIS
# ============================================================================

def grafico_top_valvulas(df):
    """Top 15 válvulas con más mantenimientos - SIEMPRE muestra 15 o menos si hay menos datos"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    top_v = df['Válvula'].value_counts().head(15).reset_index()
    top_v.columns = ['Válvula', 'Cantidad']
    top_v['Válvula'] = 'Válvula ' + top_v['Válvula'].astype(str)
    top_v = top_v.sort_values('Cantidad', ascending=True)

    fig = go.Figure(go.Bar(
        y=top_v['Válvula'], x=top_v['Cantidad'],
        orientation='h',
        marker=dict(color=top_v['Cantidad'], colorscale='Reds', showscale=False),
        text=top_v['Cantidad'], textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} registros<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='<b>Top 15 Válvulas con Mayor Mantenimiento</b>', font=dict(size=13)),
        xaxis_title='Registros',
        height=max(350, 40 * len(top_v)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=130, r=60, t=55, b=45),
        yaxis=dict(tickfont=dict(size=10)),
    )
    return fig


def grafico_tendencia(df):
    """Tendencia temporal de registros"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    df_tmp = df.copy()
    df_tmp['Fecha_dia'] = df_tmp['Fecha'].dt.date
    tendencia = df_tmp.groupby('Fecha_dia').size().reset_index(name='Registros')
    
    fig = go.Figure(go.Scatter(
        x=tendencia['Fecha_dia'], y=tendencia['Registros'],
        mode='lines+markers',
        line=dict(color='#3498db', width=2),
        marker=dict(size=6),
        hovertemplate='<b>%{x}</b><br>%{y} registros<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='<b>Tendencia Temporal</b>', font=dict(size=13)),
        xaxis_title='Fecha',
        yaxis_title='Registros',
        height=350,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=70, r=60, t=55, b=45)
    )
    return fig


def grafico_turno(df):
    """Distribución por turno"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    turno_vc = df['Turno'].value_counts().reset_index()
    turno_vc.columns = ['Turno', 'Cantidad']
    turno_vc = turno_vc.sort_values('Turno')

    fig = go.Figure(go.Bar(
        x=turno_vc['Turno'], y=turno_vc['Cantidad'],
        marker=dict(color=turno_vc['Cantidad'], colorscale='Viridis', showscale=False),
        text=turno_vc['Cantidad'], textposition='outside',
        hovertemplate='<b>Turno %{x}</b><br>%{y} registros<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='<b>Registros por Turno</b>', font=dict(size=13)),
        xaxis_title='Turno',
        yaxis_title='Registros',
        height=350,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=70, r=60, t=55, b=45)
    )
    return fig


def grafico_mantencion(df):
    """Tipos de mantención más frecuentes"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    mant = df['Mantención'].value_counts().reset_index()
    mant.columns = ['Mantención', 'Cantidad']
    mant = mant.sort_values('Cantidad', ascending=True)

    fig = go.Figure(go.Bar(
        y=mant['Mantención'], x=mant['Cantidad'],
        orientation='h',
        marker=dict(color=mant['Cantidad'], colorscale='Blues', showscale=False),
        text=mant['Cantidad'], textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} registros<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='<b>Tipos de Mantención Registrados</b>', font=dict(size=13)),
        xaxis_title='Registros',
        height=max(350, 80 * len(mant)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=180, r=60, t=55, b=45),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def grafico_operador(df):
    """Registros por operador"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    _vc = df['Operador'].value_counts()
    dist = pd.DataFrame({'Operador': _vc.index, 'Cantidad': _vc.values})
    dist = dist.sort_values('Cantidad', ascending=True)

    fig = go.Figure(go.Bar(
        y=dist['Operador'], x=dist['Cantidad'],
        orientation='h',
        marker=dict(color=dist['Cantidad'], colorscale='Greens', showscale=False),
        text=dist['Cantidad'], textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} registros<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='<b>Registros por Operador</b>', font=dict(size=13)),
        xaxis_title='Registros',
        height=max(350, 80 * len(dist)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=160, r=60, t=55, b=45),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def grafico_mantencion_por_valvula(df):
    """
    Heatmap: Válvula × Tipo de Mantención (TODAS las 112 válvulas)
    Con hover que muestra Descripción de falla y Comentarios
    """
    if len(df) == 0:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    # Crear matriz para todas las 112 válvulas
    tipos_mantencion = sorted(df['Mantención'].unique())
    matriz_z = np.zeros((112, len(tipos_mantencion)))
    matriz_hover = [[f"Válvula {i+1}<br>Sin registros" for _ in tipos_mantencion] for i in range(112)]
    
    # Llenar matriz con conteos y datos para hover
    for _, row in df.iterrows():
        valvula_idx = int(row['Válvula']) - 1
        mant_idx = tipos_mantencion.index(row['Mantención'])
        
        if 0 <= valvula_idx < 112:
            matriz_z[valvula_idx, mant_idx] += 1
            
            # Construir texto hover con descripción y comentarios
            desc = str(row.get('Descripción de falla', ''))
            coment = str(row.get('Comentarios', ''))
            
            hover_text = f"<b>Válvula {int(row['Válvula'])}</b><br>"
            hover_text += f"<b>{row['Mantención']}</b><br>"
            hover_text += f"Registros: {int(matriz_z[valvula_idx, mant_idx])}<br>"
            if desc and desc != 'nan':
                hover_text += f"<br><i>Descripción:</i> {desc[:50]}..."
            if coment and coment != 'nan':
                hover_text += f"<br><i>Comentario:</i> {coment[:50]}..."
            
            matriz_hover[valvula_idx][mant_idx] = hover_text
    
    # Etiquetas de válvulas (1-112)
    etiquetas_valvulas = [f"V{i+1}" for i in range(112)]
    
    fig = go.Figure(data=go.Heatmap(
        z=matriz_z,
        x=tipos_mantencion,
        y=etiquetas_valvulas,
        colorscale='YlOrRd',
        hovertext=matriz_hover,
        hoverinfo='text',
        colorbar=dict(title="Registros")
    ))
    
    fig.update_layout(
        title=dict(text='<b>Heatmap: Todas las 112 Válvulas × Tipos de Mantención</b>', font=dict(size=13)),
        xaxis_title='Tipo de Mantención',
        yaxis_title='Válvula',
        height=900,  # Altura fija para mostrar todas las 112
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=120, t=60, b=60),
        yaxis=dict(tickfont=dict(size=7)),
        xaxis=dict(tickfont=dict(size=10))
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
    Elaborado por: <b>Enrique Brun</b> · Jefe de Operaciones: <b>Gaston Flores</b>
  </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - FILTROS
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

turnos_opciones = sorted(df['Turno'].dropna().unique())
turnos_sel = st.sidebar.multiselect("Turnos", turnos_opciones, default=turnos_opciones)

operadores_opciones = sorted(df['Operador'].dropna().unique())
operadores_sel = st.sidebar.multiselect("Operadores", operadores_opciones, default=operadores_opciones)

mantencion_opciones = sorted(df['Mantención'].dropna().unique())
mantencion_sel = st.sidebar.multiselect("Tipos de Mantención", mantencion_opciones, default=mantencion_opciones)

# Aplicar filtros
df_f = df[
    (df['Fecha'].dt.date >= fecha_inicio) &
    (df['Fecha'].dt.date <= fecha_fin) &
    (df['Turno'].isin(turnos_sel)) &
    (df['Operador'].isin(operadores_sel)) &
    (df['Mantención'].isin(mantencion_sel))
].copy()

# ============================================================================
# MÉTRICAS
# ============================================================================

st.markdown("### 📊 KPIs")
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric("📝 Total Registros", f"{len(df_f):,}")
with m2:
    st.metric("📅 Días Activos", df_f['Fecha'].nunique())
with m3:
    st.metric("👥 Operadores", df_f['Operador'].nunique())
with m4:
    st.metric("🔧 Válvulas Afectadas", df_f['Válvula'].nunique())
with m5:
    prom = len(df_f) / max(df_f['Fecha'].nunique(), 1)
    st.metric("📊 Reg/Día Prom.", f"{prom:.1f}")

# ============================================================================
# GRÁFICOS
# ============================================================================

st.markdown("---")

if len(df_f) == 0:
    st.warning("⚠️ Sin datos para los filtros seleccionados.")
else:
    # GRÁFICO PRINCIPAL: VÁLVULAS CON MAYOR MANTENIMIENTO
    st.markdown("### 🔴 Válvulas con Mayor Número de Registros")
    st.info(
        "💡 Este gráfico muestra todas las válvulas que han registrado mantenimiento, "
        "ordenadas por cantidad de eventos. Se adapta automáticamente al número de válvulas registradas."
    )
    fig_valvulas = crear_grafico_valvulas_principales(df_f)
    st.plotly_chart(fig_valvulas, use_container_width=True)

    # TOP VÁLVULAS + TENDENCIA
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_top_valvulas(df_f), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_tendencia(df_f), use_container_width=True)

    # TURNO + OPERADORES
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafico_turno(df_f), use_container_width=True)
    with col2:
        st.plotly_chart(grafico_operador(df_f), use_container_width=True)

    # TIPOS DE MANTENCIÓN
    st.markdown("---")
    st.plotly_chart(grafico_mantencion(df_f), use_container_width=True)

    # HEATMAP VÁLVULA × MANTENCIÓN
    st.markdown("---")
    st.plotly_chart(grafico_mantencion_por_valvula(df_f), use_container_width=True)

# ============================================================================
# TABLA Y DESCARGAS
# ============================================================================

st.markdown("---")
st.markdown("### 📋 Datos Detallados")

if st.checkbox("Mostrar tabla completa"):
    df_show = df_f.copy()
    df_show['Fecha'] = df_show['Fecha'].dt.strftime('%d-%m-%Y')
    # Omitir columna de fotografía si existe
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
    f"**Google Sheets** (caché 1h)\n\n"
    f"- {len(df):,} registros totales\n"
    f"- Período: {fmt_min} → {fmt_max}\n"
    f"- Válvulas: hasta 112\n"
    f"- Tipos: O-RINGS, BLOQUE, RESORTE, ON/OFF, OTRO\n"
    f"- Operadores: {df['Operador'].nunique()}\n"
    f"- Turnos: {', '.join(sorted(df['Turno'].unique()))}"
)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;opacity:0.6;font-size:0.82rem;'>"
    "<b>Dashboard Mantenimiento Válvulas Krones Línea 2</b> · Llenadora CCU<br>"
    "Streamlit + Plotly · v1.0"
    "</div>",
    unsafe_allow_html=True
)
