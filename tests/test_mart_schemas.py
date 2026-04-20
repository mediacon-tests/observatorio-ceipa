"""Validación de schemas de marts con Pandera.

Los marts deben respetar contratos de columnas y tipos. Si Sec. Energía
cambia un schema upstream, estos tests fallan y alertan antes de que
se rompan las visualizaciones.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema


MART_PRODUCCION = DataFrameSchema({
    "anio":                Column(None, Check.in_range(2000, 2030)),
    "mes":                 Column(None, Check.in_range(1, 12)),
    "fecha":               Column(pa.DateTime, nullable=False),
    "empresa":             Column(str, nullable=False),
    "cuenca":              Column(str, nullable=False),
    "provincia":           Column(str, nullable=False),
    "yacimiento":          Column(str, nullable=False),
    "tipo_pozo":           Column(str, nullable=True),
    "tipo_recurso":        Column(str, nullable=True),
    "prod_petroleo_m3":    Column(float, Check.ge(0), nullable=True),
    "prod_gas_mm3":        Column(float, Check.ge(0), nullable=True),
    "prod_agua_m3":        Column(float, nullable=True),
    "iny_agua_m3":         Column(float, nullable=True),
    "pozos_activos":       Column(None, Check.ge(0)),
})


MART_IAP = DataFrameSchema({
    "fecha":       Column(pa.DateTime, nullable=False),
    "pozos_frac":  Column(float, Check.ge(0), nullable=True),
    "etapas":      Column(float, Check.ge(0), nullable=True),
    "arena_tn":    Column(float, Check.ge(0), nullable=True),
    "iap_ceipa":   Column(float, [Check.ge(0), Check.le(2000)]),
})


MART_POZOS_GEO = DataFrameSchema({
    "idpozo":    Column(None, nullable=True),
    "sigla":     Column(str, nullable=True),
    "yacimiento":Column(str, nullable=True),
    "cuenca":    Column(str, nullable=True),
    "provincia": Column(str, nullable=True),
    "lon":       Column(float, Check.in_range(-76, -52)),
    "lat":       Column(float, Check.in_range(-56, -20)),
    "pet_12m":   Column(float, Check.ge(0), nullable=True),
    "gas_12m":   Column(float, Check.ge(0), nullable=True),
})


MART_FRACTURAS = DataFrameSchema({
    "anio":             Column(None, Check.in_range(2000, 2030)),
    "mes":              Column(None, Check.in_range(1, 12)),
    "fecha":            Column(pa.DateTime, nullable=False),
    "empresa":          Column(str, nullable=True),
    "cuenca":           Column(str, nullable=True),
    "pozos_fracturados":Column(None, Check.ge(0)),
    "etapas_totales":   Column(None, Check.ge(0), nullable=True),
})


MART_PRECIOS_GAS = DataFrameSchema({
    "fecha":         Column(pa.DateTime, nullable=False),
    "cuenca":        Column(str, nullable=False),
    "contrato":      Column(str, nullable=True),
    "p_industria":   Column(float, Check.in_range(0, 50), nullable=True),
    "p_distribuidora": Column(float, Check.in_range(0, 50), nullable=True),
    "p_export":      Column(float, Check.in_range(0, 50), nullable=True),
})


def _fetch(con, sql: str):
    import pandas as pd
    df = con.execute(sql).fetchdf()
    # Normalizar fechas a datetime64 (pandera espera pa.DateTime)
    for c in df.columns:
        if "fecha" in c and df[c].dtype == object:
            df[c] = pd.to_datetime(df[c])
    return df


def test_mart_produccion_schema(con):
    df = _fetch(con, "SELECT * FROM mart_produccion_mensual LIMIT 5000")
    MART_PRODUCCION.validate(df, lazy=True)


def test_mart_iap_schema(con):
    df = _fetch(con, "SELECT * FROM mart_iap_ceipa")
    MART_IAP.validate(df, lazy=True)


def test_mart_pozos_geo_schema(con):
    df = _fetch(con, "SELECT * FROM mart_pozos_geo LIMIT 10000")
    MART_POZOS_GEO.validate(df, lazy=True)


def test_mart_fracturas_schema(con):
    df = _fetch(con, "SELECT * FROM mart_fracturas_mensual LIMIT 2000")
    MART_FRACTURAS.validate(df, lazy=True)


def test_mart_precios_gas_schema(con):
    df = _fetch(con, "SELECT * FROM mart_precios_gas LIMIT 2000")
    MART_PRECIOS_GAS.validate(df, lazy=True)
