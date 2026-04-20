"""
Página: Mapa GIS
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

TITLE = "Mapa GIS"


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
        st, "Geointeligencia • deck.gl",
        "Mapa de actividad upstream",
        "84.000 pozos, 4.500 fracturas, polígonos de yacimientos, sísmicas 3D y permisos de exploración. "
        "Todas las capas son togglables.",
    )

    # Controles
    c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.3, 1.1])
    with c1:
        region = st.selectbox(
            "Región",
            ["Vaca Muerta (Nqn+RN)", "Cuenca Neuquina", "Golfo San Jorge", "Austral", "Toda Argentina"],
            index=0,
        )
    with c2:
        color_by = st.selectbox(
            "Colorear pozos por",
            ["Tipo de reservorio", "Cuenca", "Provincia", "Producción 12m"],
            index=0,
        )
    with c3:
        solo_productivos = st.checkbox("Solo pozos productivos (12m)", value=True)
    with c4:
        show_layers = st.multiselect(
            "Capas visibles",
            ["Pozos", "Hexbin fracturas", "Yacimientos", "Sísmicas 3D", "Permisos exploración"],
            default=["Pozos", "Hexbin fracturas", "Yacimientos"],
        )

    # Filtro base por región y pozos
    region_filter = {
        "Vaca Muerta (Nqn+RN)": "provincia IN ('NEUQUÉN','RIO NEGRO')",
        "Cuenca Neuquina":      "cuenca = 'NEUQUINA'",
        "Golfo San Jorge":      "cuenca = 'GOLFO SAN JORGE'",
        "Austral":              "cuenca = 'AUSTRAL'",
        "Toda Argentina":       "1=1",
    }[region]
    prod_filter = "(pet_12m > 0 OR gas_12m > 0)" if solo_productivos else "1=1"

    pozos = q(f"""
        SELECT sigla, yacimiento, cuenca, provincia, tipo_reservorio, clasificacion,
               lon, lat, pet_12m, gas_12m, fecha_terminacion
        FROM mart_pozos_geo
        WHERE {region_filter} AND {prod_filter}
        LIMIT 80000
    """)

    # Viewport por región
    viewports = {
        "Vaca Muerta (Nqn+RN)": (-69.2, -38.5, 6.5),
        "Cuenca Neuquina":      (-69.5, -38.0, 6.3),
        "Golfo San Jorge":      (-68.5, -45.8, 6.5),
        "Austral":              (-68.5, -52.0, 6.0),
        "Toda Argentina":       (-65.5, -38.5, 4.2),
    }
    lon0, lat0, zoom0 = viewports[region]

    # Paleta para tipo de reservorio
    RESERV_COLORS = {
        "SHALE":        [14, 165, 164, 180],
        "TIGHT":        [245, 158, 11, 180],
        "CONVENCIONAL": [99, 102, 241, 180],
        "SIN_DATO":     [148, 163, 184, 120],
    }

    def _row_color(r) -> list:
        if color_by == "Tipo de reservorio":
            key = (r["tipo_reservorio"] or "SIN_DATO").upper()
            for k, v in RESERV_COLORS.items():
                if k in key:
                    return v
            return RESERV_COLORS["SIN_DATO"]
        if color_by == "Producción 12m":
            val = (r.get("pet_12m") or 0) + (r.get("gas_12m") or 0) * 0.9
            if val <= 0:
                return [148, 163, 184, 100]
            if val < 500:      return [14, 165, 164, 180]
            if val < 5000:     return [245, 158, 11, 200]
            if val < 20000:    return [225, 29, 72, 220]
            return [139, 0, 30, 240]
        if color_by == "Cuenca":
            palette = {"NEUQUINA":[14,165,164,180],"GOLFO SAN JORGE":[245,158,11,180],
                       "AUSTRAL":[99,102,241,180],"CUYANA":[225,29,72,180],
                       "NOROESTE":[22,163,74,180]}
            return palette.get(r["cuenca"], [148,163,184,120])
        palette = {"NEUQUÉN":[14,165,164,200],"RIO NEGRO":[245,158,11,200],
                   "MENDOZA":[225,29,72,180],"CHUBUT":[99,102,241,180],
                   "SANTA CRUZ":[22,163,74,180]}
        return palette.get(r["provincia"], [148,163,184,120])

    if len(pozos):
        pozos["color"] = pozos.apply(_row_color, axis=1)
        pozos["radio"] = pozos.apply(
            lambda r: 400 + 0.05 * ((r["pet_12m"] or 0) + (r["gas_12m"] or 0) * 0.9) ** 0.5,
            axis=1,
        ).clip(upper=1800)

    layers = []

    if "Pozos" in show_layers and len(pozos):
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=pozos,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius="radio",
            radius_min_pixels=2,
            radius_max_pixels=18,
            stroked=False,
            pickable=True,
            auto_highlight=True,
        ))

    if "Hexbin fracturas" in show_layers:
        frac = q(f"""
            SELECT lon, lat, etapas, arena_tn, empresa, fecha_fin_fractura
            FROM mart_fracturas_geo
            WHERE lon IS NOT NULL AND lat IS NOT NULL
              AND fecha_fin_fractura >= (CURRENT_DATE - INTERVAL 36 MONTH)
        """)
        if len(frac):
            layers.append(pdk.Layer(
                "HexagonLayer",
                data=frac,
                get_position="[lon, lat]",
                radius=2500,
                elevation_scale=80,
                elevation_range=[0, 3500],
                extruded=True,
                coverage=0.85,
                pickable=True,
                opacity=0.55,
                color_range=[
                    [14, 165, 164, 80], [14, 165, 164, 140], [245, 158, 11, 180],
                    [225, 29, 72, 200], [225, 29, 72, 230], [139, 0, 30, 240],
                ],
            ))

    if "Yacimientos" in show_layers:
        yac_raw = q("SELECT areayacimiento, empresa_operadora, geojson FROM raw_yacimientos WHERE geojson IS NOT NULL")
        features = []
        for _, r in yac_raw.iterrows():
            try:
                geom = json.loads(r["geojson"])
                features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "areayacimiento": r["areayacimiento"],
                        "empresa_operadora": r.get("empresa_operadora", ""),
                    },
                })
            except Exception:
                continue
        if features:
            layers.insert(0, pdk.Layer(
                "GeoJsonLayer",
                data={"type": "FeatureCollection", "features": features},
                stroked=True,
                filled=True,
                get_fill_color=[14, 165, 164, 25],
                get_line_color=[14, 165, 164, 160],
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
            ))

    if "Sísmicas 3D" in show_layers:
        sis = q("SELECT proyecto, empresa, geojson FROM mart_sismicas_3d WHERE geojson IS NOT NULL")
        features = []
        for _, r in sis.iterrows():
            try:
                geom = json.loads(r["geojson"])
                features.append({"type": "Feature", "geometry": geom,
                                 "properties": {"proyecto": r["proyecto"], "empresa": r["empresa"]}})
            except Exception:
                continue
        if features:
            layers.insert(0, pdk.Layer(
                "GeoJsonLayer",
                data={"type": "FeatureCollection", "features": features},
                stroked=True, filled=True,
                get_fill_color=[245, 158, 11, 40],
                get_line_color=[245, 158, 11, 200],
                line_width_min_pixels=1,
                pickable=True, auto_highlight=True,
            ))

    if "Permisos exploración" in show_layers:
        per = q("SELECT area, operadora, geojson FROM mart_permisos_exploracion WHERE geojson IS NOT NULL")
        features = []
        for _, r in per.iterrows():
            try:
                geom = json.loads(r["geojson"])
                features.append({"type": "Feature", "geometry": geom,
                                 "properties": {"area": r["area"], "operadora": r["operadora"]}})
            except Exception:
                continue
        if features:
            layers.insert(0, pdk.Layer(
                "GeoJsonLayer",
                data={"type": "FeatureCollection", "features": features},
                stroked=True, filled=True,
                get_fill_color=[99, 102, 241, 35],
                get_line_color=[99, 102, 241, 200],
                line_width_min_pixels=1,
                pickable=True, auto_highlight=True,
            ))

    view_state = pdk.ViewState(latitude=lat0, longitude=lon0, zoom=zoom0, pitch=35, bearing=0)

    tooltip = {
        "html": (
            "<b>{sigla}</b><br/>"
            "<span style='color:#94a3b8'>Yacimiento:</span> {yacimiento}<br/>"
            "<span style='color:#94a3b8'>Cuenca:</span> {cuenca}<br/>"
            "<span style='color:#94a3b8'>Reservorio:</span> {tipo_reservorio}<br/>"
            "<span style='color:#94a3b8'>Pet 12m (m³):</span> {pet_12m}<br/>"
            "<span style='color:#94a3b8'>Gas 12m (Mm³):</span> {gas_12m}<br/>"
            "<span style='color:#94a3b8'>Yacimiento:</span> {areayacimiento} {empresa_operadora}"
        ),
        "style": {
            "backgroundColor": "#0F172A",
            "color": "white",
            "fontFamily": "Inter",
            "fontSize": "12px",
            "padding": "8px",
            "borderRadius": "6px",
        },
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip=tooltip,
    )
    st.pydeck_chart(deck, use_container_width=True, height=620)

    # Indicadores resumen
    st.markdown("#### Resumen de la región visible")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pozos en mapa", f"{len(pozos):,}")
    c2.metric("Pozos productivos 12m", f"{int(((pozos['pet_12m']>0)|(pozos['gas_12m']>0)).sum()):,}" if len(pozos) else "0")
    c3.metric("Petróleo 12m (km³)", f"{(pozos['pet_12m'].sum()/1000 if len(pozos) else 0):.1f}")
    c4.metric("Gas 12m (kMm³)", f"{(pozos['gas_12m'].sum()/1000 if len(pozos) else 0):.1f}")

    with st.expander("Top 10 yacimientos por producción en la vista"):
        if len(pozos):
            top = (
                pozos.groupby("yacimiento")
                     .agg(pozos_n=("sigla", "count"),
                          pet_12m=("pet_12m", "sum"),
                          gas_12m=("gas_12m", "sum"))
                     .sort_values("pet_12m", ascending=False)
                     .head(10)
                     .round(1)
                     .reset_index()
            )
            st.table(top)

    with st.expander("Notas"):
        st.markdown(
            """
- **Puntos** = pozos del Listado de Operadoras (Sec. Energía). Tamaño proporcional a producción 12m.
- **Hexbin** = cantidad de fracturas por celda de ~2.5 km en los últimos 36 meses. Altura y color escalan con densidad.
- **Polígonos** = yacimientos declarados (shapefile oficial publicado en GeoJSON).
- Toggle de capas en el selector superior derecho. Hacer **clic sobre un punto** muestra detalle del pozo.
- Basemap = Carto Positron (tiles libres).
            """
        )
