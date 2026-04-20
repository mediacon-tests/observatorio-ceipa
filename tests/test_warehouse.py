"""Smoke tests del warehouse: existencia de tablas y volúmenes mínimos."""

from __future__ import annotations

import pytest


EXPECTED_TABLES = [
    # raw
    "raw_produccion_no_convencional",
    "raw_listado_pozos_operadoras",
    "raw_fracturas_adjunto_iv",
    "raw_bcra",
    "raw_indec",
    "raw_precios_gas_natural",
    "raw_trayectorias_pozos_vm",
    "raw_wb_commodity_prices",
    # marts
    "mart_produccion_mensual",
    "mart_fracturas_mensual",
    "mart_perforacion_mensual",
    "mart_macro",
    "mart_iap_ceipa",
    "mart_pozos_geo",
    "mart_fracturas_geo",
    "mart_trayectorias",
    "mart_sismicas_3d",
    "mart_permisos_exploracion",
    "mart_precios_gas",
]

MINIMUM_ROWS = {
    "raw_produccion_no_convencional": 100_000,
    "raw_listado_pozos_operadoras":   50_000,
    "raw_fracturas_adjunto_iv":       1_000,
    "raw_bcra":                       5_000,
    "raw_wb_commodity_prices":        10_000,
    "mart_produccion_mensual":        10_000,
    "mart_fracturas_mensual":         500,
    "mart_iap_ceipa":                 50,
    "mart_pozos_geo":                 50_000,
    "mart_trayectorias":              500,
}


def test_all_expected_tables_exist(table_names):
    missing = set(EXPECTED_TABLES) - set(table_names)
    assert not missing, f"Tablas faltantes en warehouse: {missing}"


@pytest.mark.parametrize("table,min_rows", MINIMUM_ROWS.items())
def test_table_has_minimum_rows(con, table, min_rows):
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    assert n >= min_rows, f"{table} tiene {n} filas, esperábamos ≥ {min_rows}"


def test_produccion_fechas_razonables(con):
    r = con.execute(
        "SELECT MIN(fecha), MAX(fecha) FROM mart_produccion_mensual"
    ).fetchone()
    min_f, max_f = r
    assert str(min_f) >= "2006-01-01", f"min fecha muy vieja: {min_f}"
    assert str(max_f) >= "2025-01-01", f"max fecha muy vieja: {max_f}"


def test_iap_no_tiene_nulls(con):
    nulls = con.execute(
        "SELECT COUNT(*) FROM mart_iap_ceipa WHERE iap_ceipa IS NULL"
    ).fetchone()[0]
    assert nulls == 0, f"IAP-CEIPA tiene {nulls} filas con NULL"


def test_ypf_domina_la_produccion(con):
    """Sanity check: YPF debería ser el mayor productor de petróleo del último año."""
    r = con.execute("""
        SELECT empresa, SUM(prod_petroleo_m3) pet
        FROM mart_produccion_mensual
        WHERE fecha >= (SELECT MAX(fecha) - INTERVAL 12 MONTH FROM mart_produccion_mensual)
        GROUP BY 1 ORDER BY pet DESC NULLS LAST LIMIT 1
    """).fetchone()
    top_empresa = (r[0] or "").upper()
    assert "YPF" in top_empresa, f"Esperábamos YPF como #1, obtuvimos {top_empresa}"


def test_pozos_geo_dentro_de_argentina(con):
    """Coords de pozos deben estar en BBox de Argentina."""
    r = con.execute("""
        SELECT MIN(lon), MAX(lon), MIN(lat), MAX(lat) FROM mart_pozos_geo
    """).fetchone()
    min_lon, max_lon, min_lat, max_lat = r
    assert -76 <= min_lon <= -52, f"lon mín fuera de AR: {min_lon}"
    assert -76 <= max_lon <= -52, f"lon máx fuera de AR: {max_lon}"
    assert -56 <= min_lat <= -20, f"lat mín fuera de AR: {min_lat}"
    assert -56 <= max_lat <= -20, f"lat máx fuera de AR: {max_lat}"
