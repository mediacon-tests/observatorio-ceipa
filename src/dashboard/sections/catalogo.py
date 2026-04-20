"""
Página: Catálogo de fuentes
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

TITLE = "Catálogo de fuentes"


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

    st.title("Catálogo de fuentes abiertas")
    st.markdown(
        """
El Observatorio se alimenta de las siguientes fuentes públicas, descargadas automáticamente
por el pipeline `src/ingest.py`. Todas las series son reproducibles desde el código.
        """
    )
    st.subheader("Secretaría de Energía")
    en_df = pd.DataFrame([
        {"key": s.key, "título": s.title, "formato": s.fmt, "frecuencia": s.frequency, "notas": s.notes}
        for s in ENERGIA_SOURCES
    ])
    st.table(en_df)

    st.subheader("BCRA — API estadísticas v4")
    st.table(
        pd.DataFrame([{"id": k, "clave": v[0], "descripción": v[1]} for k, v in BCRA_VARIABLES.items()])
    )

    st.subheader("INDEC / SSPM — Series de tiempo")
    st.table(
        pd.DataFrame([{"clave": k, "serie_id": v} for k, v in SERIES_SSPM.items()])
    )

    st.markdown("---")
    st.markdown(
        """
**Pendientes de integración (roadmap):**
- Empleo registrado por CIIU 0610/0620/0910 (OEDE — Min. Trabajo).
- Remuneraciones SIPA por rama.
- Rig count SESCO (PDF mensual — OCR).
- Homologaciones CCT 644/12 (Boletín Oficial — NLP).
- Regalías petroleras provinciales (Neuquén).
- Comercio exterior: importación de tubulares y arena (INDEC).
        """
    )

st.sidebar.markdown("---")
st.sidebar.caption(
    "MVP v0.1 — datos oficiales AR. Fuentes: Sec. Energía, BCRA, INDEC. "
    "Construcción reproducible: `python -m src.ingest`."
)
