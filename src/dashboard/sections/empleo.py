"""
Página: Empleo y salarios
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

TITLE = "Empleo y salarios"


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
        st, "Trabajo y salarios",
        "Empleo registrado y remuneraciones",
        "Fuente: Secretaría de Trabajo / SSPM. La categoría 'Minería y Petróleo' agrupa CIIU 061/062 "
        "(extracción) y servicios asociados. Series trimestrales desde 1996.",
    )

    emp = q("""
        SELECT fecha, clave, valor FROM mart_macro
        WHERE clave LIKE 'empleo_%%'
        ORDER BY fecha
    """)
    emp["fecha"] = pd.to_datetime(emp["fecha"])

    ult = (
        emp[emp["clave"] == "empleo_mineria_petroleo"]
        .sort_values("fecha").tail(8).set_index("fecha")
    )

    c1, c2, c3 = st.columns(3)
    if len(ult):
        last = ult["valor"].iloc[-1]
        yoy = ult["valor"].iloc[-1] - ult["valor"].iloc[-5] if len(ult) >= 5 else 0
        c1.metric("Empleo Minería y Petróleo (último)", f"{int(last):,}",
                  delta=f"{yoy:+,.0f} vs hace 12m")
    # Peso del sector en empleo total
    tot = emp[emp["clave"] == "empleo_total_privado"].sort_values("fecha").tail(1)
    mp = emp[emp["clave"] == "empleo_mineria_petroleo"].sort_values("fecha").tail(1)
    if len(tot) and len(mp):
        share = mp["valor"].iloc[0] / tot["valor"].iloc[0] * 100
        c2.metric("Participación sobre empleo privado total", f"{share:.2f}%")

    sal = q("""
        SELECT fecha, valor FROM mart_macro
        WHERE clave = 'salarios_privado' ORDER BY fecha DESC LIMIT 1
    """)
    if len(sal):
        c3.metric("Índice salarios sector privado (último)", f"{sal['valor'].iloc[0]:.1f}")

    st.markdown("---")
    st.subheader("Evolución del empleo por rama")
    sectores = ["empleo_mineria_petroleo", "empleo_construccion", "empleo_industria"]
    sub = emp[emp["clave"].isin(sectores)]
    fig = px.line(sub, x="fecha", y="valor", color="clave", markers=True,
                  labels={"valor": "Puestos de trabajo", "fecha": "", "clave": "Sector"})
    fig.update_layout(height=420, legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Índices salariales (base 2016)")
    sal_all = q("""
        SELECT fecha, clave, valor FROM mart_macro
        WHERE clave LIKE 'salarios_%%' OR clave = 'remuneracion_media_real'
        ORDER BY fecha
    """)
    if len(sal_all):
        fig = px.line(sal_all, x="fecha", y="valor", color="clave",
                      labels={"valor": "Índice", "fecha": "", "clave": "Serie"})
        fig.update_layout(height=380, legend=dict(orientation="h", y=-0.18))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Ratio empleo petrolero / empleo privado total")
    piv = emp.pivot_table(index="fecha", columns="clave", values="valor", aggfunc="last")
    if {"empleo_mineria_petroleo", "empleo_total_privado"}.issubset(piv.columns):
        piv["ratio_pct"] = piv["empleo_mineria_petroleo"] / piv["empleo_total_privado"] * 100
        fig = px.line(piv.reset_index(), x="fecha", y="ratio_pct",
                      labels={"ratio_pct": "% sobre empleo privado", "fecha": ""})
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Notas metodológicas"):
        st.markdown(
            """
- Las series de empleo registrado vienen **trimestralmente** y con cierto rezago.
- La categoría "Minería y Petróleo" es la agregación publicada por SSPM. Para el perfil
  específico de CEIPA (proveedores de servicios de upstream), la referencia más precisa
  es el CIIU 0910 — **pendiente de integración desde OEDE** en la próxima iteración.
- Los índices salariales son relativos (base 2016). Para análisis de poder adquisitivo
  deben deflactarse por IPC.
            """
        )

    st.markdown("---")
    from src.dashboard.export import csv_button
    csv_button(
        q("SELECT fecha, clave, valor FROM mart_macro WHERE clave LIKE 'empleo_%' OR clave LIKE 'salarios_%' ORDER BY fecha"),
        "ceipa_empleo_salarios.csv", "Empleo y salarios",
    )
