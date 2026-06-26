"""
Página: Resumen ejecutivo
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

TITLE = "Resumen ejecutivo"


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

    hero(
        st,
        eyebrow="Informe integral",
        title="La actividad upstream en Vaca Muerta",
        subtitle="Inteligencia de datos para la cadena de servicios petroleros. "
                 "Producción, empleo, precios y pipeline de inversión a partir de fuentes oficiales.",
        chips=["Vaca Muerta", "13 secciones", "Datos oficiales"],
        byline=f"Datos al <strong>{pd.Timestamp(max_fecha).strftime('%B %Y').capitalize()}</strong> · "
               "Fuentes: Secretaría de Energía · BCRA · INDEC · Min. Trabajo · World Bank",
    )

    iap = q("SELECT * FROM mart_iap_ceipa ORDER BY fecha")
    ultimo = iap.iloc[-1] if len(iap) else None
    prev = iap.iloc[-13] if len(iap) >= 13 else None

    pozos_12m = q(f"""
        SELECT SUM(pozos_activos) pozos FROM mart_produccion_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}' AND {_prov_filter()} AND {_cuenca_filter()}
    """).iloc[0]["pozos"] or 0
    prod = q(f"""
        SELECT SUM(prod_petroleo_m3) pet, SUM(prod_gas_mm3) gas
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}' AND {_prov_filter()} AND {_cuenca_filter()}
    """).iloc[0]

    # Sparklines — 12m series
    iap_spark = iap.tail(24)["iap_ceipa"].tolist()
    prod_spark = q(f"""
        SELECT fecha, SUM(prod_petroleo_m3)/1000 p
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{(fecha_desde - pd.DateOffset(months=12)).date()}'
          AND {_prov_filter()} AND {_cuenca_filter()}
        GROUP BY 1 ORDER BY 1
    """)["p"].tolist()
    gas_spark = q(f"""
        SELECT fecha, SUM(prod_gas_mm3)/1000 g
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{(fecha_desde - pd.DateOffset(months=12)).date()}'
          AND {_prov_filter()} AND {_cuenca_filter()}
        GROUP BY 1 ORDER BY 1
    """)["g"].tolist()
    frac_spark = q(f"""
        SELECT fecha, SUM(etapas_totales) e FROM mart_fracturas_mensual
        WHERE fecha >= DATE '{(fecha_desde - pd.DateOffset(months=12)).date()}'
        GROUP BY 1 ORDER BY 1
    """)["e"].fillna(0).tolist()

    iap_delta = f"{ultimo['iap_ceipa']:.0f} vs {prev['iap_ceipa']:.0f}" if (ultimo is not None and prev is not None) else None
    iap_up = (ultimo["iap_ceipa"] > prev["iap_ceipa"]) if (ultimo is not None and prev is not None) else None

    cards = [
        stat_card(
            "Índice CEIPA", f"{ultimo['iap_ceipa']:.1f}" if ultimo is not None else "—",
            delta=iap_delta, delta_up=iap_up,
            spark=iap_spark, variant="hero accent", palette=PALETTE,
        ),
        stat_card(
            "Pozos-mes activos", f"{int(pozos_12m):,}",
            delta=f"Ventana {rango}", spark=None, palette=PALETTE,
        ),
        stat_card(
            "Petróleo", f"{(prod['pet'] or 0)/1e6:.1f}", unit="Mm³",
            spark=prod_spark, palette=PALETTE,
        ),
        stat_card(
            "Gas natural", f"{(prod['gas'] or 0)/1e3:.1f}", unit="km³",
            spark=gas_spark, palette=PALETTE,
        ),
    ]
    bento_grid(st, cards, variant="hero")

    # Segundo nivel: 3 cards adicionales
    emp_mp = q("""SELECT valor FROM mart_macro WHERE clave='empleo_mineria_petroleo' ORDER BY fecha DESC LIMIT 1""")
    emp_val = int(emp_mp.iloc[0]["valor"]) if len(emp_mp) else 0

    # WTI spot diario real (EIA/FRED); fallback al promedio mensual WB si no está cargado.
    wti = q("""SELECT fecha, valor FROM raw_wti_spot_diario ORDER BY fecha DESC LIMIT 1""")
    if len(wti):
        wti_val = wti.iloc[0]["valor"]
        wti_fecha = wti.iloc[0]["fecha"]
        wti_label = f"WTI spot ({wti_fecha:%d-%m-%Y})"
        wti_prev = q("""SELECT valor FROM raw_wti_spot_diario ORDER BY fecha DESC LIMIT 30""")["valor"].tolist()
    else:
        wti = q("""SELECT fecha, valor FROM raw_wb_commodity_prices WHERE commodity = 'crude_oil__wti____bbl_' ORDER BY fecha DESC LIMIT 1""")
        wti_val = wti.iloc[0]["valor"] if len(wti) else None
        wti_label = "WTI (prom. mensual WB)"
        wti_prev = q("""SELECT valor FROM raw_wb_commodity_prices WHERE commodity = 'crude_oil__wti____bbl_' ORDER BY fecha DESC LIMIT 13""")["valor"].tolist()
    wti_spark = list(reversed(wti_prev))

    tc = q("""SELECT valor FROM mart_macro WHERE clave='tc_mayorista' ORDER BY fecha DESC LIMIT 1""")
    tc_val = tc.iloc[0]["valor"] if len(tc) else None
    tc_spark_df = q("""SELECT valor FROM mart_macro WHERE clave='tc_mayorista' ORDER BY fecha DESC LIMIT 60""")
    tc_spark = list(reversed(tc_spark_df["valor"].tolist()))

    cards_2 = [
        stat_card("Etapas de fractura (ventana)",
                  f"{int(sum(v for v in frac_spark if v)):,}",
                  spark=frac_spark, palette=PALETTE),
        stat_card("Empleo Minería y Petróleo",
                  f"{emp_val:,}", unit="puestos", palette=PALETTE),
        stat_card(wti_label,
                  f"{wti_val:.1f}" if wti_val else "—", unit="USD/bbl",
                  spark=wti_spark, palette=PALETTE),
        stat_card("Dólar mayorista",
                  f"{tc_val:,.0f}" if tc_val else "—", unit="ARS",
                  spark=tc_spark, palette=PALETTE),
    ]
    bento_grid(st, cards_2, variant="4")

    section_header(st, "Actividad proveedora", "Índice de Actividad Proveedora CEIPA",
                   "Proxy de demanda de servicios de estimulación hidráulica y logística. "
                   "Base 100 = promedio mensual 2017-2019. Construido desde el Adjunto IV de Sec. Energía.")
    iap_chart = iap[iap["fecha"] >= fecha_desde]
    fig = px.line(iap_chart, x="fecha", y="iap_ceipa", markers=True,
                  color_discrete_sequence=[PALETTE["primary"]])
    fig.add_hline(y=100, line_dash="dash", line_color=PALETTE["text_soft"],
                  annotation_text="Base 100", annotation_font_size=10)
    fig.update_layout(height=360, yaxis_title="IAP-CEIPA", xaxis_title=None,
                      margin=dict(l=8, r=8, t=16, b=28))
    st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        section_header(st, "Upstream Vaca Muerta", "Producción no convencional",
                       "Volumen mensual de petróleo y gas en la ventana seleccionada.")
        df = q(f"""
            SELECT fecha,
                   SUM(prod_petroleo_m3)/1000 AS pet_km3,
                   SUM(prod_gas_mm3)/1000 AS gas_km3m3
            FROM mart_produccion_mensual
            WHERE fecha >= DATE '{fecha_desde.date()}'
              AND {_prov_filter()} AND {_cuenca_filter()}
            GROUP BY 1 ORDER BY 1
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["fecha"], y=df["pet_km3"], name="Petróleo (km³)", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df["fecha"], y=df["gas_km3m3"], name="Gas (kMm³)", mode="lines+markers", yaxis="y2"))
        fig.update_layout(
            height=360,
            yaxis=dict(title="Petróleo (km³)"),
            yaxis2=dict(title="Gas (kMm³)", overlaying="y", side="right"),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        section_header(st, "Servicios especiales", "Actividad de fracturas",
                       "Etapas mensuales completadas — demanda directa de servicios de estimulación.")
        df = q(f"""
            SELECT fecha,
                   COALESCE(SUM(pozos_fracturados), 0) AS pozos,
                   COALESCE(SUM(etapas_totales), 0) AS etapas
            FROM mart_fracturas_mensual
            WHERE fecha >= DATE '{fecha_desde.date()}'
            GROUP BY 1 ORDER BY 1
        """)
        df["etapas"] = df["etapas"].fillna(0)
        fig = px.bar(df, x="fecha", y="etapas", labels={"etapas": "Etapas fractura", "fecha": ""})
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    section_header(st, "Export", "Descargas",
                   "Descargá los datos de esta sección o un reporte PDF completo.")
    from src.dashboard.export import csv_button, pdf_report_button
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        csv_button(iap, "ceipa_iap_mensual.csv", "IAP-CEIPA mensual")
    with col_b:
        csv_button(
            q("SELECT * FROM mart_produccion_mensual ORDER BY fecha"),
            "ceipa_produccion_mensual.csv", "Producción mensual",
        )
    with col_c:
        pdf_report_button()
