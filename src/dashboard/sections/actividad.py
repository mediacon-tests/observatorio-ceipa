"""
Página: Actividad de perforación y fractura
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

TITLE = "Actividad de perforación y fractura"


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

    st.title("Actividad de perforación y fractura")
    st.caption("Datos Adjunto IV (diario) y listado de pozos operadoras.")

    df = q(f"""
        SELECT fecha, empresa,
               SUM(pozos_fracturados) pozos,
               SUM(etapas_totales) etapas,
               SUM(arena_nacional_tn + COALESCE(arena_importada_tn,0)) arena_tn,
               SUM(agua_inyectada_m3) agua_m3
        FROM mart_fracturas_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
        GROUP BY 1,2 ORDER BY 1
    """)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pozos fracturados (ventana)", f"{int(df['pozos'].sum()):,}")
    c2.metric("Etapas totales", f"{int(df['etapas'].sum()):,}")
    c3.metric("Arena bombeada (tn)", f"{(df['arena_tn'].sum() or 0)/1000:,.0f} k·tn")

    st.subheader("Etapas mensuales por operadora")
    top = df.groupby("empresa")["etapas"].sum().nlargest(10).index.tolist()
    sub = df[df["empresa"].isin(top)]
    fig = px.area(sub, x="fecha", y="etapas", color="empresa")
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Arena bombeada (nacional vs. importada)")
    df_arena = q(f"""
        SELECT fecha,
               SUM(arena_nacional_tn) AS nacional_tn,
               SUM(arena_importada_tn) AS importada_tn
        FROM mart_fracturas_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
        GROUP BY 1 ORDER BY 1
    """)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_arena["fecha"], y=df_arena["nacional_tn"], name="Nacional"))
    fig.add_trace(go.Bar(x=df_arena["fecha"], y=df_arena["importada_tn"], name="Importada"))
    fig.update_layout(barmode="stack", height=360, yaxis_title="Toneladas")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pozos terminados por mes (listado operadoras)")
    perf = q(f"""
        SELECT fecha_terminacion AS fecha, SUM(pozos_terminados) AS pozos
        FROM mart_perforacion_mensual
        WHERE fecha_terminacion >= DATE '{fecha_desde.date()}'
          AND {_prov_filter()}
        GROUP BY 1 ORDER BY 1
    """)
    fig = px.bar(perf, x="fecha", y="pozos")
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(df if 'df' in locals() else None,
               "ceipa_actividad_fracturas.csv", "Fracturas por empresa/mes")
