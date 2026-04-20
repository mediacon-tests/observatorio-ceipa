"""
Contexto compartido entre páginas del dashboard.

El singleton `ctx` expone:
- con: conexión DuckDB read-only
- q: función de query cacheada
- palette: paleta activa (dict)
- fecha_desde: timestamp del inicio de la ventana temporal elegida
- rango: label de la ventana ("6m", "12m", "24m", "48m", "Todo")
- max_fecha: fecha máxima del warehouse
- _prov_filter / _cuenca_filter: helpers SQL (hoy siempre "1=1")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "ceipa.duckdb"


@dataclass
class Ctx:
    con: duckdb.DuckDBPyConnection
    q: Callable[[str], pd.DataFrame]
    palette: dict
    fecha_desde: pd.Timestamp
    rango: str
    max_fecha: pd.Timestamp
    prov_filter: Callable[[], str]
    cuenca_filter: Callable[[], str]


@st.cache_resource
def _get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=600)
def _cached_q(sql: str) -> pd.DataFrame:
    return _get_con().execute(sql).fetchdf()


def build_ctx(palette: dict) -> Ctx:
    """Construye el contexto para la página actual.
    Los filtros geográficos quedan como `1=1` hasta reintroducirlos."""

    def q(sql: str) -> pd.DataFrame:
        return _cached_q(sql)

    max_fecha = q("SELECT MAX(fecha) f FROM mart_produccion_mensual").iloc[0]["f"]

    rango = st.session_state.get("_window_range", "24m")
    months_map = {"6m": 6, "12m": 12, "24m": 24, "48m": 48, "Todo": 240}
    fecha_desde = pd.Timestamp(max_fecha) - pd.DateOffset(months=months_map[rango])

    return Ctx(
        con=_get_con(),
        q=q,
        palette=palette,
        fecha_desde=fecha_desde,
        rango=rango,
        max_fecha=pd.Timestamp(max_fecha),
        prov_filter=lambda: "1=1",
        cuenca_filter=lambda: "1=1",
    )
