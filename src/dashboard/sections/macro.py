"""
Página: Macroeconomía y precios
Refactorizada automáticamente desde app.py el 2026-04-20.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src.dashboard.theme import (
    bento_grid, chip, hero, section_header, stat_card,
)
from src.dashboard.export import csv_button
from src.sources import BCRA_VARIABLES, ENERGIA_SOURCES, SERIES_SSPM

if TYPE_CHECKING:
    from src.dashboard.shared import Ctx

TITLE = "Macroeconomía y precios"


def render(ctx: "Ctx") -> None:
    # Desempaqueto el contexto para minimizar diffs con el app.py viejo
    q = ctx.q
    PALETTE = ctx.palette
    COLORS = ctx.palette
    fecha_desde = ctx.fecha_desde
    rango = ctx.rango
    max_fecha = ctx.max_fecha
    _prov_filter = ctx.prov_filter
    _cuenca_filter = ctx.cuenca_filter

    st.title("Contexto macro — BCRA + INDEC")

    series = q("SELECT DISTINCT clave, descripcion FROM mart_macro ORDER BY 1")
    with st.expander("Variables disponibles en el warehouse"):
        st.table(series)

    sel = st.multiselect(
        "Series a graficar",
        series["clave"].tolist(),
        default=["tc_mayorista", "ipc_mensual", "emae_original"],
    )
    if sel:
        vals = ",".join([f"'{s}'" for s in sel])
        df = q(f"""
            SELECT fecha, clave, valor
            FROM mart_macro
            WHERE clave IN ({vals})
              AND fecha >= DATE '{fecha_desde.date()}'
            ORDER BY fecha
        """)
        for k in sel:
            sub = df[df["clave"] == k]
            if len(sub):
                fig = px.line(sub, x="fecha", y="valor", title=k, markers=False)
                fig.update_layout(height=260, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Precio internacional del crudo (Dec. 488/2020)")
    try:
        df = q("SELECT * FROM raw_precio_internacional_crudo ORDER BY 1 DESC LIMIT 20")
        st.table(df)
    except Exception as e:
        st.warning(f"No disponible: {e}")
