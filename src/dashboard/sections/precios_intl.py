"""
Página: Precios internacionales
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

TITLE = "Precios internacionales"


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
        st, "Banco Mundial • Pink Sheet",
        "Precios internacionales de referencia",
        "Precios mensuales de commodities publicados por el Banco Mundial. "
        "Permiten contextualizar la producción argentina contra referencias globales. Base 1960.",
    )

    df = q("""
        SELECT fecha, commodity, valor FROM raw_wb_commodity_prices
        WHERE commodity IN (
            'crude_oil__brent____bbl_',
            'crude_oil__wti____bbl_',
            'crude_oil__dubai____bbl_',
            'liquefied_natural_gas__japan____mmbtu_',
            'coal__australian____mt_'
        )
        ORDER BY fecha
    """)
    df["commodity"] = df["commodity"].str.replace("_+", "_", regex=True).str.strip("_")
    df["fecha"] = pd.to_datetime(df["fecha"])

    ult = df.sort_values("fecha").groupby("commodity").last().reset_index()
    prev = df[df["fecha"] == (df["fecha"].max() - pd.DateOffset(months=12))].groupby("commodity").last().reset_index()
    labels = {
        "crude_oil_brent_bbl": "Brent (USD/bbl)",
        "crude_oil_wti_bbl": "WTI (USD/bbl)",
        "crude_oil_dubai_bbl": "Dubai (USD/bbl)",
        "liquefied_natural_gas_japan_mmbtu": "LNG Japan (USD/MMBTU)",
        "coal_australian_mt": "Carbón Australia (USD/mt)",
    }

    cols_m = st.columns(min(5, len(ult)))
    for i, (_, row) in enumerate(ult.iterrows()):
        label = labels.get(row["commodity"], row["commodity"][:25])
        delta_row = prev[prev["commodity"] == row["commodity"]]
        delta = f"{((row['valor'] - delta_row.iloc[0]['valor']) / delta_row.iloc[0]['valor'] * 100):+.1f}% YoY" if len(delta_row) else None
        cols_m[i].metric(label, f"{row['valor']:.1f}", delta=delta)

    st.subheader("Evolución — últimos 10 años")
    recent = df[df["fecha"] >= (df["fecha"].max() - pd.DateOffset(years=10))].copy()
    recent["label"] = recent["commodity"].map(labels).fillna(recent["commodity"])
    oil = recent[recent["commodity"].str.contains("crude")]
    fig = px.line(oil, x="fecha", y="valor", color="label", markers=False,
                  labels={"valor": "USD/bbl", "fecha": "", "label": "Benchmark"})
    fig.update_layout(height=360, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    gas = recent[recent["commodity"].str.contains("lng|coal", regex=True)]
    fig = px.line(gas, x="fecha", y="valor", color="label", markers=False,
                  labels={"valor": "USD", "fecha": "", "label": "Energía"})
    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Crudo vs. serie histórica larga (1970+)")
    long = df[(df["commodity"].str.contains("brent|wti", regex=True)) & (df["fecha"] >= "1970-01-01")].copy()
    long["label"] = long["commodity"].map(labels).fillna(long["commodity"])
    fig = px.line(long, x="fecha", y="valor", color="label",
                  labels={"valor": "USD/bbl", "fecha": "", "label": ""})
    fig.update_layout(height=340, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(df if 'df' in locals() else None,
               "ceipa_precios_commodities.csv", "Commodities WB")
