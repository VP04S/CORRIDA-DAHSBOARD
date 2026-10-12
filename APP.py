import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
import re
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="Dashboard Corridas",
    page_icon="📦",
    layout="wide"
)

# ==========================
# RUTA
# ==========================

import sqlite3

DB_FILE = "corridas.db"

archivos = st.file_uploader(
    "📤 Subir CSV de Corridas",
    type=["csv"],
    accept_multiple_files=True
)
if archivos:

    conn = sqlite3.connect(DB_FILE)

    for archivo in archivos:

        try:

        df_temp = pd.read_csv(
        archivo,
        sep="|",
        encoding="utf-8",
        low_memory=False
    )

except:

    archivo.seek(0)

    df_temp = pd.read_csv(
        archivo,
        sep="|",
        encoding="latin-1",
        low_memory=False
    )
    
        nombre = archivo.name

        fecha_match = re.search(
            r"(\d{2})-(\d{2})-(\d{4})",
            nombre
        )

        if fecha_match:

            fecha_archivo = datetime.strptime(
                fecha_match.group(),
                "%d-%m-%Y"
            )
            df_temp["fecha_archivo"] = fecha_archivo
            
        df_temp.to_sql(
            "corridas",
            conn,
            if_exists="append",
            index=False
        )    
                            
# ==========================
# CARGA DESDE SQLITE
# ==========================

conn = sqlite3.connect(DB_FILE)

try:

    df = pd.read_sql(
        "SELECT * FROM corridas",
        conn
    )

except:

    df = pd.DataFrame()

conn.close()
st.success(f"📁 Registros históricos: {len(df):,}")
if df.empty:

    st.error("No se encontraron archivos")

    st.stop()

# ==========================
# LIMPIEZA
# ==========================

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
)

df["fecha_archivo"] = pd.to_datetime(
    df["fecha_archivo"]
)

# ==========================
# TITULO
# ==========================

st.title("📦 Dashboard Corridas")

st.caption("Últimos 100 CSV")

# ==========================
# SIDEBAR
# ==========================

st.sidebar.title("Filtros")

rango_fecha = st.sidebar.date_input(
    "Fecha Archivo",
    value=(
        df["fecha_archivo"].min().date(),
        df["fecha_archivo"].max().date()
    )
)

if len(rango_fecha) == 2:

    inicio, fin = rango_fecha

    df = df[
        (df["fecha_archivo"].dt.date >= inicio)
        &
        (df["fecha_archivo"].dt.date <= fin)
    ]

for campo in [
    "zona",
    "tienda",
    "tipo_carton",
    "tipo_pedido",
    "origen",
    "bodega",
    "clase_ubicacion",
    "stat_code"
]:

    valores = st.sidebar.multiselect(
        campo.upper(),
        sorted(
            df[campo]
            .dropna()
            .astype(str)
            .unique()
        )
    )

    if valores:

        df = df[
            df[campo]
            .astype(str)
            .isin(valores)
        ]

# ==========================
# KPI
# ==========================

k1,k2,k3,k4 = st.columns(4)

k1.metric(
    "📦 Cartones",
    f"{df['carton_nbr'].nunique():,}"
)

k2.metric(
    "📋 SKU",
    f"{df['sku_id'].nunique():,}"
)

k3.metric(
    "🏪 Tiendas",
    f"{df['tienda'].nunique():,}"
)

k4.metric(
    "🌊 Waves",
    f"{df['wave_nbr'].nunique():,}"
)

k5,k6,k7,k8 = st.columns(4)

k5.metric(
    "📍 Ubicaciones",
    f"{df['ubicacion_picking'].nunique():,}"
)

k6.metric(
    "🎯 Zonas",
    f"{df['zona'].nunique():,}"
)

k7.metric(
    "📦 Unidades",
    f"{pd.to_numeric(df['und_solicitadas'], errors='coerce').sum():,.0f}"
)

k8.metric(
    "🚚 Manifiestos",
    f"{df['manif_nbr'].nunique():,}"
)

# ==========================
# GRAFICOS
# ==========================

c1,c2 = st.columns(2)

zona_pie = (
    df.groupby("zona")["carton_nbr"]
    .nunique()
    .reset_index(name="cartones")
)

fig1 = px.pie(
    zona_pie,
    values="cartones",
    names="zona",
    hole=0.4,
    title="Distribución por Zona"
)

c1.plotly_chart(fig1, use_container_width=True)

fig2 = px.bar(
    zona_pie.sort_values(
        "cartones",
        ascending=False
    ),
    x="zona",
    y="cartones",
    color="cartones",
    title="Cartones por Zona"
)

c2.plotly_chart(fig2, use_container_width=True)

# ==========================
# CARTONES POR FECHA
# ==========================

fecha_df = (
    df.groupby("fecha_archivo")["carton_nbr"]
    .nunique()
    .reset_index(name="cartones")
)

fig3 = px.line(
    fecha_df,
    x="fecha_archivo",
    y="cartones",
    markers=True,
    title="Cartones por Fecha"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

# ==========================
# TOP TIENDAS
# ==========================

col1,col2 = st.columns(2)

top_tiendas = (
    df.groupby("tienda")["carton_nbr"]
    .nunique()
    .reset_index(name="cartones")
    .sort_values(
        "cartones",
        ascending=False
    )
    .head(20)
)

fig4 = px.bar(
    top_tiendas,
    y="tienda",
    x="cartones",
    orientation="h",
    color="cartones",
    title="Top Tiendas"
)

col1.plotly_chart(
    fig4,
    use_container_width=True
)

# ==========================
# TOP SKU
# ==========================

top_sku = (
    df.groupby("sku_id")["und_solicitadas"]
    .sum()
    .reset_index()
    .sort_values(
        "und_solicitadas",
        ascending=False
    )
    .head(20)
)

fig5 = px.bar(
    top_sku,
    y="sku_id",
    x="und_solicitadas",
    orientation="h",
    color="und_solicitadas",
    title="Top SKU"
)

col2.plotly_chart(
    fig5,
    use_container_width=True
)

# ==========================
# TABLA DINAMICA
# ==========================

st.subheader(
    "📊 Matriz Zona x Fecha"
)

pivot = pd.pivot_table(
    df,
    index="zona",
    columns="fecha_archivo",
    values="carton_nbr",
    aggfunc=pd.Series.nunique,
    fill_value=0
)

st.dataframe(
    pivot,
    use_container_width=True,
    height=450
)

# ==========================
# DETALLE
# ==========================

with st.expander(
    "📋 Ver detalle"
):

    st.dataframe(
        df,
        use_container_width=True
    )

# ==========================
# DESCARGA
# ==========================

buffer = BytesIO()

with pd.ExcelWriter(
    buffer,
    engine="openpyxl"
) as writer:

    df.to_excel(
        writer,
        index=False,
        sheet_name="Detalle"
    )

buffer.seek(0)

st.download_button(
    "📥 Descargar Datos Filtrados",
    data=buffer,
    file_name="Corridas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
