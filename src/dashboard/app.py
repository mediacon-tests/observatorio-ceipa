"""
Dashboard Observatorio CEIPA — entrypoint / router.

Ejecutar:   streamlit run src/dashboard/app.py
Requiere:   data/ceipa.duckdb generado por `python -m src.ingest`
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.sections import PAGES
from src.dashboard.shared import build_ctx
from src.dashboard.theme import apply as apply_theme, logo


st.set_page_config(
    page_title="Observatorio CEIPA",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = apply_theme(st)


# ================ Sidebar ================
logo(st)

page_labels = [label for label, _ in PAGES]
selected = st.sidebar.radio("Secciones", page_labels, key="_nav")

st.sidebar.markdown("**Filtros de período**")
rango = st.sidebar.select_slider(
    "Ventana",
    options=["6m", "12m", "24m", "48m", "Todo"],
    value=st.session_state.get("_window_range", "24m"),
    key="_window_range",
)


# ================ Router ================
ctx = build_ctx(PALETTE)
page_module = dict(PAGES)[selected]
page_module.render(ctx)
