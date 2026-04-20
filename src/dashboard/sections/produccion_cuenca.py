"""
Página: Producción por cuenca / provincia
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

TITLE = "Producción por cuenca / provincia"


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

    st.title("Producción por cuenca y provincia")

    df = q(f"""
        SELECT fecha, cuenca, provincia,
               SUM(prod_petroleo_m3) pet_m3,
               SUM(prod_gas_mm3) gas_mm3
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
        GROUP BY 1,2,3 ORDER BY 1
    """)

    tab1, tab2 = st.tabs(["Por cuenca", "Por provincia"])
    with tab1:
        agg = df.groupby(["fecha", "cuenca"], as_index=False).agg(pet=("pet_m3", "sum"), gas=("gas_mm3", "sum"))
        fig = px.area(agg, x="fecha", y="pet", color="cuenca", labels={"pet": "Petróleo m³"})
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
        fig = px.area(agg, x="fecha", y="gas", color="cuenca", labels={"gas": "Gas Mm³"})
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        agg = df.groupby(["fecha", "provincia"], as_index=False).agg(pet=("pet_m3", "sum"), gas=("gas_mm3", "sum"))
        fig = px.area(agg, x="fecha", y="pet", color="provincia", labels={"pet": "Petróleo m³"})
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
        fig = px.area(agg, x="fecha", y="gas", color="provincia", labels={"gas": "Gas Mm³"})
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
