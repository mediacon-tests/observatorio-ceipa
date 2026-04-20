"""Smoke test del módulo de forecast."""

from __future__ import annotations

import pandas as pd
import pytest


def test_forecast_tables_exist(table_names):
    for t in ["mart_iap_historical", "mart_iap_forecast", "mart_iap_backtest"]:
        assert t in table_names, f"Tabla de forecast faltante: {t}"


def test_forecast_tiene_12_meses(con):
    df = con.execute("SELECT * FROM mart_iap_forecast ORDER BY fecha").fetchdf()
    assert len(df) == 12, f"Forecast debería tener 12 meses, tiene {len(df)}"


def test_forecast_tiene_3_escenarios(con):
    df = con.execute("SELECT * FROM mart_iap_forecast LIMIT 1").fetchdf()
    for col in ["base", "optimista", "pesimista"]:
        assert col in df.columns, f"Falta columna {col} en forecast"


def test_forecast_escenarios_ordenados(con):
    """pesimista ≤ base ≤ optimista para cada mes."""
    df = con.execute("SELECT * FROM mart_iap_forecast").fetchdf()
    assert (df["pesimista"] <= df["base"]).all(), "pesimista > base en alguna fila"
    assert (df["base"] <= df["optimista"]).all(), "base > optimista en alguna fila"


def test_backtest_tiene_metricas(con):
    df = con.execute("SELECT * FROM mart_iap_backtest").fetchdf()
    if "mape_pct" in df.columns:
        assert df["mape_pct"].notna().any(), "Backtest sin MAPE reportado"
        assert df["mape_pct"].between(0, 500).all(), "MAPE fuera de rango razonable"
