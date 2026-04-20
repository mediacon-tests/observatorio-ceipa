"""
Página: Precios de gas
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

TITLE = "Precios de gas"


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
        st, "Gas natural • Res. 1/2018",
        "Precios por cuenca y segmento",
        "Precio del gas natural por cuenca, tipo de contrato y destino (distribuidora, GNC, usina, "
        "industria, exportación, PPP). USD/MMBTU. Fuente: Secretaría de Energía.",
    )

    df = q("SELECT * FROM mart_precios_gas ORDER BY fecha")
    df["fecha"] = pd.to_datetime(df["fecha"])

    c1, c2, c3, c4 = st.columns(4)
    ult = df.sort_values("fecha").groupby("cuenca").last().reset_index()
    vm = ult[ult["cuenca"] == "NEUQUINA"]
    if len(vm):
        v = vm.iloc[0]
        c1.metric("Neuquina — industria", f"{v['p_industria']:.2f}")
        c2.metric("Neuquina — distribuidora", f"{v['p_distribuidora']:.2f}")
        c3.metric("Neuquina — export", f"{v['p_export']:.2f}")
        c4.metric("Neuquina — usina", f"{v['p_usina']:.2f}")

    st.subheader("Evolución de precios (Cuenca Neuquina)")
    nqn = df[df["cuenca"] == "NEUQUINA"].copy()
    if "contrato" in nqn.columns:
        nqn = nqn[nqn["contrato"] == "FIRME"]
    melted = nqn.melt(
        id_vars="fecha",
        value_vars=["p_distribuidora", "p_gnc", "p_usina", "p_industria", "p_ppp", "p_export"],
        var_name="segmento", value_name="precio",
    )
    melted["segmento"] = melted["segmento"].str.replace("p_", "").str.upper()
    fig = px.line(
        melted, x="fecha", y="precio", color="segmento", markers=True,
        labels={"precio": "USD/MMBTU", "fecha": "", "segmento": "Destino"},
    )
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Comparativa de precios entre cuencas — último mes")
    last = df["fecha"].max()
    comp = df[(df["fecha"] == last)].copy()
    if "contrato" in comp.columns:
        comp = comp[comp["contrato"] == "FIRME"]
    fig = px.bar(
        comp, x="cuenca", y=["p_industria", "p_usina", "p_distribuidora", "p_ppp", "p_export"],
        barmode="group",
        labels={"value": "USD/MMBTU", "cuenca": "", "variable": "Segmento"},
    )
    fig.update_layout(height=380, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(df if 'df' in locals() else None,
               "ceipa_precios_gas.csv", "Precios gas (histórico completo)")
