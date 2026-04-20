"""
Dashboard Observatorio CEIPA - MVP.

Ejecutar:   streamlit run src/dashboard/app.py
Requiere:   data/ceipa.duckdb generado por `python -m src.ingest`
"""

from __future__ import annotations

from pathlib import Path

import json
import sys

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "ceipa.duckdb"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sources import BCRA_VARIABLES, ENERGIA_SOURCES, SERIES_SSPM
from src.dashboard.theme import (
    apply as apply_theme,
    bento_grid,
    chip,
    hero,
    logo,
    section_header,
    stat_card,
)

st.set_page_config(
    page_title="Observatorio CEIPA",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = apply_theme(st)
COLORS = PALETTE  # compat con código viejo que usa COLORS["primary"] etc.


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=600)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return get_con().execute(sql, params).fetchdf()


# ---------- Sidebar ----------
logo(st)

page = st.sidebar.radio(
    "Secciones",
    [
        "Resumen ejecutivo",
        "Actividad de perforación y fractura",
        "Producción por empresa",
        "Producción por cuenca / provincia",
        "Pipeline de proyectos (EIAs)",
        "Mapa GIS",
        "Trayectorias shale",
        "Precios de gas",
        "Precios internacionales",
        "Empleo y salarios",
        "Forecast IAP-CEIPA",
        "Macroeconomía y precios",
        "Catálogo de fuentes",
    ],
)

max_fecha = q("SELECT MAX(fecha) f FROM mart_produccion_mensual").iloc[0]["f"]
min_fecha = q("SELECT MIN(fecha) f FROM mart_produccion_mensual WHERE fecha >= '2017-01-01'").iloc[0]["f"]

st.sidebar.markdown("**Filtros de período**")
rango = st.sidebar.select_slider(
    "Ventana",
    options=["6m", "12m", "24m", "48m", "Todo"],
    value="24m",
)
_months = {"6m": 6, "12m": 12, "24m": 24, "48m": 48, "Todo": 240}[rango]
fecha_desde = pd.Timestamp(max_fecha) - pd.DateOffset(months=_months)

# Totales — filtros geográficos removidos temporalmente (sin corte por provincia/cuenca).
def _prov_filter() -> str:
    return "1=1"


def _cuenca_filter() -> str:
    return "1=1"


# =============== PÁGINAS ===============
if page == "Resumen ejecutivo":
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

    wti = q("""SELECT valor FROM raw_wb_commodity_prices WHERE commodity = 'crude_oil__wti____bbl_' ORDER BY fecha DESC LIMIT 1""")
    wti_val = wti.iloc[0]["valor"] if len(wti) else None
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
        stat_card("WTI spot",
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

elif page == "Actividad de perforación y fractura":
    st.title("Actividad de perforación y fractura")
    st.caption("Datos Adjunto IV (diario) y listado de pozos operadoras.")

    df = q(f"""
        SELECT fecha, empresa,
               SUM(pozos_fracturados) pozos,
               SUM(etapas_totales) etapas,
               SUM(arena_nacional_tn + COALESCE(arena_importada_tn,0)) arena_tn,
               SUM(agua_inyectada_m3) agua_m3
        FROM mart_fracturas_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
        GROUP BY 1,2 ORDER BY 1
    """)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pozos fracturados (ventana)", f"{int(df['pozos'].sum()):,}")
    c2.metric("Etapas totales", f"{int(df['etapas'].sum()):,}")
    c3.metric("Arena bombeada (tn)", f"{(df['arena_tn'].sum() or 0)/1000:,.0f} k·tn")

    st.subheader("Etapas mensuales por operadora")
    top = df.groupby("empresa")["etapas"].sum().nlargest(10).index.tolist()
    sub = df[df["empresa"].isin(top)]
    fig = px.area(sub, x="fecha", y="etapas", color="empresa")
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Arena bombeada (nacional vs. importada)")
    df_arena = q(f"""
        SELECT fecha,
               SUM(arena_nacional_tn) AS nacional_tn,
               SUM(arena_importada_tn) AS importada_tn
        FROM mart_fracturas_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
        GROUP BY 1 ORDER BY 1
    """)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_arena["fecha"], y=df_arena["nacional_tn"], name="Nacional"))
    fig.add_trace(go.Bar(x=df_arena["fecha"], y=df_arena["importada_tn"], name="Importada"))
    fig.update_layout(barmode="stack", height=360, yaxis_title="Toneladas")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pozos terminados por mes (listado operadoras)")
    perf = q(f"""
        SELECT fecha_terminacion AS fecha, SUM(pozos_terminados) AS pozos
        FROM mart_perforacion_mensual
        WHERE fecha_terminacion >= DATE '{fecha_desde.date()}'
          AND {_prov_filter()}
        GROUP BY 1 ORDER BY 1
    """)
    fig = px.bar(perf, x="fecha", y="pozos")
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Producción por empresa":
    st.title("Producción por empresa operadora")

    df = q(f"""
        SELECT empresa,
               SUM(prod_petroleo_m3) pet_m3,
               SUM(prod_gas_mm3) gas_mm3,
               SUM(pozos_activos) pozos_mes
        FROM mart_produccion_mensual
        WHERE fecha >= DATE '{fecha_desde.date()}'
          AND {_prov_filter()} AND {_cuenca_filter()}
        GROUP BY 1
        ORDER BY pet_m3 DESC NULLS LAST
        LIMIT 20
    """)
    df = df.fillna({"pet_m3": 0, "gas_mm3": 0, "pozos_mes": 0})
    df["pet_km3"] = df["pet_m3"] / 1000
    df["gas_km3m3"] = df["gas_mm3"] / 1000

    st.subheader("Top 20 por petróleo")
    fig = px.bar(df.head(20), x="pet_km3", y="empresa", orientation="h",
                 labels={"pet_km3": "Petróleo (km³)", "empresa": ""},
                 color_discrete_sequence=[COLORS["primary"]])
    fig.update_layout(height=560, yaxis=dict(autorange="reversed"),
                      margin=dict(l=10, r=10, t=20, b=30))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 por gas")
    df_gas = df.sort_values("gas_km3m3", ascending=False).head(20)
    fig = px.bar(df_gas, x="gas_km3m3", y="empresa", orientation="h",
                 labels={"gas_km3m3": "Gas (kMm³)", "empresa": ""},
                 color_discrete_sequence=[COLORS["accent"]])
    fig.update_layout(height=560, yaxis=dict(autorange="reversed"),
                      margin=dict(l=10, r=10, t=20, b=30))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Evolución mensual — empresas seleccionadas")
    top5 = df.head(5)["empresa"].tolist()
    sel = st.multiselect("Empresas", df["empresa"].tolist(), default=top5)
    if sel:
        vals = ",".join([f"'{e}'" for e in sel])
        ts = q(f"""
            SELECT fecha, empresa, SUM(prod_petroleo_m3)/1000 pet_km3, SUM(prod_gas_mm3)/1000 gas_km3m3
            FROM mart_produccion_mensual
            WHERE fecha >= DATE '{fecha_desde.date()}'
              AND empresa IN ({vals})
              AND {_prov_filter()} AND {_cuenca_filter()}
            GROUP BY 1,2 ORDER BY 1
        """)
        tab1, tab2 = st.tabs(["Petróleo", "Gas"])
        with tab1:
            fig = px.line(ts, x="fecha", y="pet_km3", color="empresa", markers=True,
                          labels={"pet_km3": "Petróleo (km³)", "fecha": ""})
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            fig = px.line(ts, x="fecha", y="gas_km3m3", color="empresa", markers=True,
                          labels={"gas_km3m3": "Gas (kMm³)", "fecha": ""})
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

elif page == "Producción por cuenca / provincia":
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

elif page == "Pipeline de proyectos (EIAs)":
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

elif page == "Mapa GIS":
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

elif page == "Trayectorias shale":
    section_header(
        st, "Vaca Muerta • Eficiencia shale",
        "Trayectorias de pozos horizontales",
        "Evolución de los parámetros técnicos que determinan la productividad del shale: "
        "longitud de rama horizontal, profundidad vertical y curva de aprendizaje del sector.",
    )

    df = q("""
        SELECT * FROM mart_trayectorias
        WHERE fecha_terminacion >= '2014-01-01'
          AND rama_horizontal_m > 0
    """)
    df["anio"] = pd.to_datetime(df["fecha_terminacion"]).dt.year

    c1, c2, c3, c4 = st.columns(4)
    ult_12m = df[df["fecha_terminacion"] >= (pd.Timestamp.today() - pd.DateOffset(months=12))]
    c1.metric("Pozos con trayectoria", f"{len(df):,}")
    c2.metric("Terminados último año", f"{len(ult_12m):,}")
    c3.metric("Rama horizontal media (m)", f"{df['rama_horizontal_m'].mean():.0f}")
    c4.metric("Último año — media (m)", f"{ult_12m['rama_horizontal_m'].mean():.0f}" if len(ult_12m) else "—")

    st.subheader("Evolución de la longitud de rama horizontal")
    anual = df.groupby("anio").agg(
        rama_media=("rama_horizontal_m", "mean"),
        rama_p90=("rama_horizontal_m", lambda x: x.quantile(0.9)),
        pozos=("sigla", "count"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=anual["anio"], y=anual["pozos"], name="Pozos",
                         marker_color=COLORS["border"], yaxis="y2", opacity=0.5))
    fig.add_trace(go.Scatter(x=anual["anio"], y=anual["rama_media"], name="Rama media (m)",
                             line=dict(color=COLORS["primary"], width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=anual["anio"], y=anual["rama_p90"], name="Rama P90 (m)",
                             line=dict(color=COLORS["accent"], width=2, dash="dash"), mode="lines+markers"))
    fig.update_layout(
        height=420, hovermode="x unified",
        yaxis=dict(title="Longitud rama (m)"),
        yaxis2=dict(title="Pozos", overlaying="y", side="right", showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distribución de longitudes de rama — últimos 24 meses")
    recent = df[df["fecha_terminacion"] >= (pd.Timestamp.today() - pd.DateOffset(months=24))]
    fig = px.histogram(
        recent, x="rama_horizontal_m", nbins=40,
        color_discrete_sequence=[COLORS["primary"]],
        labels={"rama_horizontal_m": "Longitud rama horizontal (m)"},
    )
    fig.update_layout(height=340, bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Profundidad vertical vs. rama horizontal")
    fig = px.scatter(
        df.sample(min(1500, len(df))),
        x="prof_vertical_m", y="rama_horizontal_m", color="anio",
        labels={"prof_vertical_m": "Profundidad vertical (m)",
                "rama_horizontal_m": "Rama horizontal (m)", "anio": "Año"},
        opacity=0.55,
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Precios de gas":
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

elif page == "Precios internacionales":
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

elif page == "Empleo y salarios":
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

elif page == "Forecast IAP-CEIPA":
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

elif page == "Macroeconomía y precios":
    st.title("Contexto macro — BCRA + INDEC")

    series = q("SELECT DISTINCT clave, descripcion FROM mart_macro ORDER BY 1")
    with st.expander("Variables disponibles en el warehouse"):
        st.table(series)

    sel = st.multiselect(
        "Series a graficar",
        series["clave"].tolist(),
        default=["tc_mayorista", "ipc_mensual", "emae_original"],
    )
    if sel:
        vals = ",".join([f"'{s}'" for s in sel])
        df = q(f"""
            SELECT fecha, clave, valor
            FROM mart_macro
            WHERE clave IN ({vals})
              AND fecha >= DATE '{fecha_desde.date()}'
            ORDER BY fecha
        """)
        for k in sel:
            sub = df[df["clave"] == k]
            if len(sub):
                fig = px.line(sub, x="fecha", y="valor", title=k, markers=False)
                fig.update_layout(height=260, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Precio internacional del crudo (Dec. 488/2020)")
    try:
        df = q("SELECT * FROM raw_precio_internacional_crudo ORDER BY 1 DESC LIMIT 20")
        st.table(df)
    except Exception as e:
        st.warning(f"No disponible: {e}")

elif page == "Catálogo de fuentes":
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
