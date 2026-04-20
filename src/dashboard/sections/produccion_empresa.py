"""
Página: Producción por empresa
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

TITLE = "Producción por empresa"


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

    st.title("Producción por empresa operadora")

    df = q(f"""
        SELECT empresa,
               SUM(prod_petroleo_m3) pet_m3,
               SUM(prod_gas_mm3) gas_mm3,
               SUM(pozos_activos) pozos_mes
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
          AND {_prov_filter()} AND {_cuenca_filter()}
        GROUP BY 1
        ORDER BY pet_m3 DESC NULLS LAST
        LIMIT 20
    """)
    df = df.fillna({"pet_m3": 0, "gas_mm3": 0, "pozos_mes": 0})
    df["pet_km3"] = df["pet_m3"] / 1000
    df["gas_km3m3"] = df["gas_mm3"] / 1000

    st.subheader("Top 20 por petróleo")
    fig = px.bar(df.head(20), x="pet_km3", y="empresa", orientation="h",
                 labels={"pet_km3": "Petróleo (km³)", "empresa": ""},
                 color_discrete_sequence=[COLORS["primary"]])
    fig.update_layout(height=560, yaxis=dict(autorange="reversed"),
                      margin=dict(l=10, r=10, t=20, b=30))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 por gas")
    df_gas = df.sort_values("gas_km3m3", ascending=False).head(20)
    fig = px.bar(df_gas, x="gas_km3m3", y="empresa", orientation="h",
                 labels={"gas_km3m3": "Gas (kMm³)", "empresa": ""},
                 color_discrete_sequence=[COLORS["accent"]])
    fig.update_layout(height=560, yaxis=dict(autorange="reversed"),
                      margin=dict(l=10, r=10, t=20, b=30))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Evolución mensual — empresas seleccionadas")
    top5 = df.head(5)["empresa"].tolist()
    sel = st.multiselect("Empresas", df["empresa"].tolist(), default=top5)
    if sel:
        vals = ",".join([f"'{e}'" for e in sel])
        ts = q(f"""
            SELECT fecha, empresa, SUM(prod_petroleo_m3)/1000 pet_km3, SUM(prod_gas_mm3)/1000 gas_km3m3
            FROM mart_produccion_mensual
            WHERE fecha >= DATE '{fecha_desde.date()}'
              AND empresa IN ({vals})
              AND {_prov_filter()} AND {_cuenca_filter()}
            GROUP BY 1,2 ORDER BY 1
        """)
        tab1, tab2 = st.tabs(["Petróleo", "Gas"])
        with tab1:
            fig = px.line(ts, x="fecha", y="pet_km3", color="empresa", markers=True,
                          labels={"pet_km3": "Petróleo (km³)", "fecha": ""})
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            fig = px.line(ts, x="fecha", y="gas_km3m3", color="empresa", markers=True,
                          labels={"gas_km3m3": "Gas (kMm³)", "fecha": ""})
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(df if 'df' in locals() else None,
               "ceipa_top_empresas.csv", "Top 20 empresas (ventana)")
