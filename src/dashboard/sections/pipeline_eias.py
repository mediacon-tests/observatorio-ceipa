"""
Página: Pipeline de proyectos (EIAs)
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

TITLE = "Pipeline de proyectos (EIAs)"


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

    st.title("Pipeline de proyectos — Estudios Ambientales")
    st.caption(
        "Los Estudios de Impacto Ambiental presentados son un **leading indicator** de actividad futura. "
        "Datos de raw_estudios_ambientales (upstream)."
    )
    cols = q("DESCRIBE raw_estudios_ambientales")
    with st.expander("Columnas disponibles"):
        st.table(cols)

    try:
        total = q("SELECT COUNT(*) n FROM raw_estudios_ambientales").iloc[0]["n"]
        df = q("""
            SELECT * FROM raw_estudios_ambientales
            ORDER BY 1 DESC
            LIMIT 25
        """)
        c1, c2 = st.columns(2)
        c1.metric("Estudios registrados (total)", f"{int(total):,}")
        c2.metric("Mostrando", f"{len(df)} más recientes")
        st.table(df)
    except Exception as e:
        st.error(f"Error: {e}")
