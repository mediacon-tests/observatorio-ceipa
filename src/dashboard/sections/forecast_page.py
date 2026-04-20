"""
Página: Forecast IAP-CEIPA
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

TITLE = "Forecast IAP-CEIPA"


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
        st, "Modelo predictivo",
        "Proyección del Índice de Actividad Proveedora",
        "SARIMAX(1,1,1)(1,0,1,12) con variables exógenas (tipo de cambio mayorista, IPC mensual). "
        "Escenarios: base = pronóstico puntual · optimista/pesimista = intervalo de confianza 80%.",
    )

    try:
        hist = q("SELECT * FROM mart_iap_historical ORDER BY fecha")
        fc = q("SELECT * FROM mart_iap_forecast ORDER BY fecha")
        bt = q("SELECT * FROM mart_iap_backtest")
    except Exception as e:
        st.warning(
            "No hay forecast generado todavía. Ejecutar:  `python -m src.forecast`  "
            f"(detalle: {e})"
        )
        hist = fc = bt = pd.DataFrame()

    if len(hist) and len(fc):
        c1, c2, c3, c4 = st.columns(4)
        ult_obs = hist.iloc[-1]
        base_prom = fc["base"].mean()
        c1.metric("Último observado", f"{ult_obs['observado']:.1f}",
                  help=f"Mes {pd.to_datetime(ult_obs['fecha']).strftime('%Y-%m')}")
        c2.metric("Base 12m (promedio)", f"{base_prom:.1f}",
                  delta=f"{(base_prom - ult_obs['observado']):+.1f} vs último")
        c3.metric("Optimista 12m", f"{fc['optimista'].mean():.1f}")
        c4.metric("Pesimista 12m", f"{fc['pesimista'].mean():.1f}")

        st.subheader("Histórico + escenarios proyectados")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(hist["fecha"]), y=hist["observado"],
            mode="lines+markers", name="Observado",
            line=dict(color=COLORS["primary"], width=2.2),
            marker=dict(size=5),
        ))
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(hist["fecha"]), y=hist["ajustado"],
            mode="lines", name="Ajuste modelo",
            line=dict(color=COLORS["primary"], dash="dot", width=1),
            opacity=0.45,
        ))
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(fc["fecha"]), y=fc["base"],
            mode="lines+markers", name="Base",
            line=dict(color=COLORS["accent"], width=2.5),
            marker=dict(size=6),
        ))
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(fc["fecha"]), y=fc["optimista"],
            mode="lines", name="Optimista",
            line=dict(color=COLORS["success"], dash="dash", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(fc["fecha"]), y=fc["pesimista"],
            mode="lines", name="Pesimista",
            line=dict(color=COLORS["danger"], dash="dash", width=1.5),
            fill="tonexty", fillcolor="rgba(245, 158, 11, 0.08)",
        ))
        fig.add_hline(y=100, line_dash="dot", line_color="#94A3B8",
                      annotation_text="Base 100 (promedio 2017-19)",
                      annotation_font_size=10)
        fig.update_layout(height=500, hovermode="x unified",
                          yaxis_title="IAP-CEIPA",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabla de proyección mensual")
        fc_tabla = fc.copy()
        fc_tabla["fecha"] = pd.to_datetime(fc_tabla["fecha"]).dt.strftime("%Y-%m")
        st.table(fc_tabla.round(1))

        st.subheader("Backtest walk-forward (6m)")
        st.caption(
            "Performance del modelo en ventanas históricas sucesivas. "
            "MAPE alto indica alta volatilidad del sector — el modelo es orientativo."
        )
        if len(bt):
            bt_v = bt.copy()
            if "fecha_corte" in bt_v.columns:
                bt_v["fecha_corte"] = pd.to_datetime(bt_v["fecha_corte"]).dt.strftime("%Y-%m")
            st.table(bt_v)
            if "mape_pct" in bt_v.columns:
                st.metric("MAPE medio", f"{bt_v['mape_pct'].mean():.1f}%")

        st.info(
            "**Lectura honesta:** la serie IAP-CEIPA tiene alta volatilidad mensual porque las "
            "campañas de fractura son discretas. El modelo captura tendencia y estacionalidad, "
            "pero no eventos idiosincráticos (una detención de 2-3 sets de fractura puede mover "
            "30 puntos de índice). Usar el promedio trimestral para decisión."
        )

    st.markdown("---")
    from src.dashboard.export import csv_button
    col_a, col_b = st.columns(2)
    with col_a:
        csv_button(fc if 'fc' in locals() and len(fc) else None,
                   "ceipa_forecast_iap.csv", "Forecast 12m (escenarios)")
    with col_b:
        csv_button(hist if 'hist' in locals() and len(hist) else None,
                   "ceipa_iap_historico.csv", "Histórico + ajuste")
