"""
Página: Trayectorias shale
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

TITLE = "Trayectorias shale"


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

    section_header(
        st, "Vaca Muerta • Eficiencia shale",
        "Trayectorias de pozos horizontales",
        "Evolución de los parámetros técnicos que determinan la productividad del shale: "
        "longitud de rama horizontal, profundidad vertical y curva de aprendizaje del sector.",
    )

    df = q("""
        SELECT * FROM mart_trayectorias
        WHERE fecha_terminacion >= '2014-01-01'
          AND rama_horizontal_m > 0
    """)
    df["anio"] = pd.to_datetime(df["fecha_terminacion"]).dt.year

    c1, c2, c3, c4 = st.columns(4)
    ult_12m = df[df["fecha_terminacion"] >= (pd.Timestamp.today() - pd.DateOffset(months=12))]
    c1.metric("Pozos con trayectoria", f"{len(df):,}")
    c2.metric("Terminados último año", f"{len(ult_12m):,}")
    c3.metric("Rama horizontal media (m)", f"{df['rama_horizontal_m'].mean():.0f}")
    c4.metric("Último año — media (m)", f"{ult_12m['rama_horizontal_m'].mean():.0f}" if len(ult_12m) else "—")

    st.subheader("Evolución de la longitud de rama horizontal")
    anual = df.groupby("anio").agg(
        rama_media=("rama_horizontal_m", "mean"),
        rama_p90=("rama_horizontal_m", lambda x: x.quantile(0.9)),
        pozos=("sigla", "count"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=anual["anio"], y=anual["pozos"], name="Pozos",
                         marker_color=COLORS["border"], yaxis="y2", opacity=0.5))
    fig.add_trace(go.Scatter(x=anual["anio"], y=anual["rama_media"], name="Rama media (m)",
                             line=dict(color=COLORS["primary"], width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=anual["anio"], y=anual["rama_p90"], name="Rama P90 (m)",
                             line=dict(color=COLORS["accent"], width=2, dash="dash"), mode="lines+markers"))
    fig.update_layout(
        height=420, hovermode="x unified",
        yaxis=dict(title="Longitud rama (m)"),
        yaxis2=dict(title="Pozos", overlaying="y", side="right", showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distribución de longitudes de rama — últimos 24 meses")
    recent = df[df["fecha_terminacion"] >= (pd.Timestamp.today() - pd.DateOffset(months=24))]
    fig = px.histogram(
        recent, x="rama_horizontal_m", nbins=40,
        color_discrete_sequence=[COLORS["primary"]],
        labels={"rama_horizontal_m": "Longitud rama horizontal (m)"},
    )
    fig.update_layout(height=340, bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Profundidad vertical vs. rama horizontal")
    fig = px.scatter(
        df.sample(min(1500, len(df))),
        x="prof_vertical_m", y="rama_horizontal_m", color="anio",
        labels={"prof_vertical_m": "Profundidad vertical (m)",
                "rama_horizontal_m": "Rama horizontal (m)", "anio": "Año"},
        opacity=0.55,
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(df if 'df' in locals() else None,
               "ceipa_trayectorias_vm.csv", "Trayectorias pozos VM")
