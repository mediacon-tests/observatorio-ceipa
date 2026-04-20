"""
Ingesta de fuentes abiertas para el Observatorio CEIPA.

Ejecutar:   python -m src.ingest
"""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import requests
import urllib3

from src.sources import (
    ALL_SOURCES,
    BCRA_API_BASE,
    BCRA_VARIABLES,
    SERIES_API,
    SERIES_SSPM,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
DB_PATH = DATA / "ceipa.duckdb"
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def download(url: str, dest: Path, timeout: int = 300) -> Path:
    r = requests.get(url, timeout=timeout, verify=False)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def register(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> None:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    con.register("_stg", df)
    con.execute(f'DROP TABLE IF EXISTS {name}')
    con.execute(f'CREATE TABLE {name} AS SELECT * FROM _stg')
    con.unregister("_stg")


def _read_wb_commodities(path: Path) -> pd.DataFrame:
    """World Bank Pink Sheet — hoja 'Monthly Prices'. Header en fila 4."""
    raw = pd.read_excel(path, sheet_name="Monthly Prices", header=[4, 5])
    raw.columns = [
        "_".join([str(a) for a in c if str(a) != "nan" and not str(a).startswith("Unnamed")]).strip("_")
        for c in raw.columns
    ]
    first_col = raw.columns[0]
    raw = raw.rename(columns={first_col: "periodo"})
    raw = raw[raw["periodo"].notna()]
    raw["periodo"] = raw["periodo"].astype(str).str.strip()
    raw = raw[raw["periodo"].str.match(r"\d{4}M\d{2}")]
    raw["fecha"] = pd.to_datetime(raw["periodo"].str.replace("M", "-") + "-01", errors="coerce")
    value_cols = [c for c in raw.columns if c not in ("periodo", "fecha")]
    long = raw.melt(id_vars=["fecha", "periodo"], value_vars=value_cols,
                   var_name="commodity", value_name="valor")
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    long = long.dropna(subset=["valor", "fecha"])
    long["commodity"] = long["commodity"].str.lower().str.replace(r"[^a-z0-9_]", "_", regex=True)
    return long


def _read_precio_pi(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_row = None
    for i in range(min(6, len(raw))):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if any("u$s" in c or "barril" in c for c in row):
            header_row = i
            break
    if header_row is None:
        header_row = 2
    df = pd.read_excel(path, header=header_row)
    df = df.dropna(how="all")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    return df


def ingest_energia(con: duckdb.DuckDBPyConnection) -> None:
    for key, src in ALL_SOURCES.items():
        ext = "xlsx" if src.fmt.startswith("xlsx") else src.fmt
        dest = RAW / f"{key}.{ext}"
        try:
            if not dest.exists() or dest.stat().st_size < 1024:
                log(f"GET {key}")
                download(src.url, dest)
            if src.fmt == "csv":
                df = pd.read_csv(dest, low_memory=False)
            elif src.fmt == "xlsx":
                df = pd.read_excel(dest)
            elif src.fmt == "xlsx_pi":
                df = _read_precio_pi(dest)
            elif src.fmt == "xlsx_wb":
                df = _read_wb_commodities(dest)
            elif src.fmt == "zip":
                with zipfile.ZipFile(dest) as z:
                    inner = [n for n in z.namelist() if n.lower().endswith((".csv", ".xlsx", ".xls"))]
                    if not inner:
                        log(f"  {key}: zip vacío de datos tabulares; saltando")
                        continue
                    frames = []
                    for name in inner[:10]:
                        with z.open(name) as f:
                            try:
                                if name.lower().endswith(".csv"):
                                    sub = pd.read_csv(f, low_memory=False)
                                else:
                                    sub = pd.read_excel(f)
                                sub["_source_file"] = name
                                frames.append(sub)
                            except Exception as e:
                                log(f"    [{name}] skip: {e}")
                    if not frames:
                        continue
                    # Unificar columnas por union
                    cols = set()
                    for f in frames:
                        cols.update(f.columns)
                    df = pd.concat([f.reindex(columns=list(cols)) for f in frames], ignore_index=True)
            else:
                continue
            register(con, f"raw_{key}", df)
            log(f"  {key}: {len(df):,} filas, {len(df.columns)} cols")
        except Exception as e:
            log(f"  ERROR {key}: {e}")


def ingest_bcra(con: duckdb.DuckDBPyConnection) -> None:
    frames = []
    for var_id, (clave, desc) in BCRA_VARIABLES.items():
        try:
            url = f"{BCRA_API_BASE}/{var_id}?desde=2018-01-01&hasta=2030-01-01&limit=3000"
            r = requests.get(url, timeout=60, verify=False)
            if r.status_code != 200:
                log(f"  BCRA {clave}: HTTP {r.status_code}")
                continue
            results = r.json().get("results", [])
            rows = []
            for res in results:
                for d in res.get("detalle", []):
                    rows.append({"fecha": d["fecha"], "valor": d["valor"]})
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df["id_variable"] = var_id
            df["clave"] = clave
            df["descripcion"] = desc
            frames.append(df)
            log(f"  BCRA {clave}: {len(df)} obs")
        except Exception as e:
            log(f"  ERROR BCRA {clave}: {e}")
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        register(con, "raw_bcra", all_df)
        log(f"  raw_bcra: {len(all_df):,} filas")


def ingest_indec(con: duckdb.DuckDBPyConnection) -> None:
    frames = []
    for clave, sid in SERIES_SSPM.items():
        try:
            url = f"{SERIES_API}?ids={sid}&format=csv&limit=1000"
            r = requests.get(url, timeout=60, verify=False)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            value_col = [c for c in df.columns if c != "indice_tiempo"][0]
            df = df.rename(columns={value_col: "valor", "indice_tiempo": "fecha"})
            df["clave"] = clave
            df["serie_id"] = sid
            frames.append(df[["fecha", "valor", "clave", "serie_id"]])
            log(f"  INDEC {clave}: {len(df)} obs")
        except Exception as e:
            log(f"  ERROR INDEC {clave}: {e}")
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        register(con, "raw_indec", all_df)
        log(f"  raw_indec: {len(all_df):,} filas")


def build_marts(con: duckdb.DuckDBPyConnection) -> None:
    # Mart: producción mensual por empresa/cuenca/provincia (base: no convencional)
    con.execute("""
    CREATE OR REPLACE VIEW mart_produccion_mensual AS
    SELECT
      CAST(anio AS INT)                                AS anio,
      CAST(mes AS INT)                                 AS mes,
      make_date(CAST(anio AS INT), CAST(mes AS INT), 1) AS fecha,
      UPPER(TRIM(COALESCE(empresa, 'SIN_DATO')))       AS empresa,
      UPPER(TRIM(COALESCE(cuenca, 'SIN_DATO')))        AS cuenca,
      UPPER(TRIM(COALESCE(provincia, 'SIN_DATO')))     AS provincia,
      UPPER(TRIM(COALESCE(areayacimiento, 'SIN_DATO'))) AS yacimiento,
      UPPER(TRIM(COALESCE(tipopozo, 'SIN_DATO')))      AS tipo_pozo,
      UPPER(TRIM(COALESCE(sub_tipo_recurso, tipo_de_recurso, 'NC'))) AS tipo_recurso,
      SUM(TRY_CAST(prod_pet AS DOUBLE))                AS prod_petroleo_m3,
      SUM(TRY_CAST(prod_gas AS DOUBLE))                AS prod_gas_mm3,
      SUM(TRY_CAST(prod_agua AS DOUBLE))               AS prod_agua_m3,
      SUM(TRY_CAST(iny_agua AS DOUBLE))                AS iny_agua_m3,
      COUNT(DISTINCT sigla)                            AS pozos_activos
    FROM raw_produccion_no_convencional
    WHERE anio IS NOT NULL AND mes IS NOT NULL
    GROUP BY 1,2,3,4,5,6,7,8,9
    """)

    # Mart: fracturas por mes (actividad de servicios de estimulación)
    con.execute("""
    CREATE OR REPLACE VIEW mart_fracturas_mensual AS
    SELECT
      CAST(anio_ff AS INT)                             AS anio,
      CAST(mes_ff AS INT)                              AS mes,
      make_date(CAST(anio_ff AS INT), CAST(mes_ff AS INT), 1) AS fecha,
      UPPER(TRIM(COALESCE(empresa_informante, 'SIN_DATO'))) AS empresa,
      UPPER(TRIM(COALESCE(cuenca, 'SIN_DATO')))        AS cuenca,
      UPPER(TRIM(COALESCE(tipo_reservorio, 'SIN_DATO'))) AS tipo_reservorio,
      COUNT(*)                                         AS pozos_fracturados,
      SUM(TRY_CAST(cantidad_fracturas AS INTEGER))     AS etapas_totales,
      SUM(TRY_CAST(longitud_rama_horizontal_m AS DOUBLE)) AS rama_horizontal_m,
      SUM(TRY_CAST(arena_bombeada_nacional_tn AS DOUBLE)) AS arena_nacional_tn,
      SUM(TRY_CAST(arena_bombeada_importada_tn AS DOUBLE)) AS arena_importada_tn,
      SUM(TRY_CAST(agua_inyectada_m3 AS DOUBLE))       AS agua_inyectada_m3
    FROM raw_fracturas_adjunto_iv
    WHERE anio_ff IS NOT NULL AND mes_ff IS NOT NULL
    GROUP BY 1,2,3,4,5,6
    """)

    # Mart: pozos perforados por mes (empresa operadora)
    con.execute("""
    CREATE OR REPLACE VIEW mart_perforacion_mensual AS
    SELECT
      date_trunc('month', TRY_CAST(adjiv_fecha_fin_term AS DATE)) AS fecha_terminacion,
      UPPER(TRIM(COALESCE(areayacimiento, 'SIN_DATO'))) AS yacimiento,
      UPPER(TRIM(COALESCE(cuenca, 'SIN_DATO')))        AS cuenca,
      UPPER(TRIM(COALESCE(provincia, 'SIN_DATO')))     AS provincia,
      UPPER(TRIM(COALESCE(clasificacion, 'SIN_DATO'))) AS clasificacion,
      COUNT(DISTINCT sigla)                            AS pozos_terminados
    FROM raw_listado_pozos_operadoras
    WHERE adjiv_fecha_fin_term IS NOT NULL
    GROUP BY 1,2,3,4,5
    """)

    # Mart: series macroeconómicas (BCRA + INDEC unificado)
    con.execute("""
    CREATE OR REPLACE VIEW mart_macro AS
    SELECT CAST(fecha AS DATE) AS fecha,
           clave,
           descripcion,
           CAST(valor AS DOUBLE) AS valor,
           'BCRA' AS fuente
    FROM raw_bcra
    UNION ALL
    SELECT CAST(fecha AS DATE) AS fecha,
           clave,
           clave AS descripcion,
           CAST(valor AS DOUBLE) AS valor,
           'INDEC' AS fuente
    FROM raw_indec
    """)

    # Mart: Índice de Actividad Proveedora CEIPA (IAP-CEIPA) simplificado
    # v0: combina pozos terminados + etapas de fractura + pozos fracturados en cuencas operativas
    con.execute("""
    CREATE OR REPLACE VIEW mart_iap_ceipa AS
    WITH base AS (
      SELECT
        fecha,
        SUM(pozos_fracturados)  AS pozos_frac,
        SUM(etapas_totales)     AS etapas,
        SUM(arena_nacional_tn + COALESCE(arena_importada_tn, 0)) AS arena_tn
      FROM mart_fracturas_mensual
      WHERE fecha >= '2017-01-01'
      GROUP BY 1
    ),
    base_ref AS (
      SELECT AVG(pozos_frac) AS pf_ref, AVG(etapas) AS ep_ref, AVG(arena_tn) AS ar_ref
      FROM base
      WHERE fecha BETWEEN '2017-01-01' AND '2019-12-31'
    )
    SELECT
      b.fecha,
      b.pozos_frac,
      b.etapas,
      b.arena_tn,
      100.0 * (
        0.4 * b.pozos_frac / NULLIF(r.pf_ref, 0) +
        0.35 * b.etapas    / NULLIF(r.ep_ref, 0) +
        0.25 * b.arena_tn  / NULLIF(r.ar_ref, 0)
      ) AS iap_ceipa
    FROM base b CROSS JOIN base_ref r
    ORDER BY b.fecha
    """)

    # Mart geoespacial: pozos con última producción conocida
    con.execute("""
    CREATE OR REPLACE VIEW mart_pozos_geo AS
    WITH prod_ult AS (
        SELECT idpozo,
               MAX(make_date(CAST(anio AS INT), CAST(mes AS INT), 1)) AS fecha_ult,
               SUM(CASE WHEN make_date(CAST(anio AS INT), CAST(mes AS INT), 1)
                             >= (CURRENT_DATE - INTERVAL 12 MONTH)
                        THEN TRY_CAST(prod_pet AS DOUBLE) END) AS pet_12m,
               SUM(CASE WHEN make_date(CAST(anio AS INT), CAST(mes AS INT), 1)
                             >= (CURRENT_DATE - INTERVAL 12 MONTH)
                        THEN TRY_CAST(prod_gas AS DOUBLE) END) AS gas_12m
        FROM raw_produccion_no_convencional
        WHERE anio IS NOT NULL AND mes IS NOT NULL
        GROUP BY idpozo
    )
    SELECT
        p.idpozo,
        p.sigla,
        UPPER(TRIM(COALESCE(p.areayacimiento, 'SIN_DATO'))) AS yacimiento,
        UPPER(TRIM(COALESCE(p.cuenca, 'SIN_DATO')))         AS cuenca,
        UPPER(TRIM(COALESCE(p.provincia, 'SIN_DATO')))      AS provincia,
        UPPER(TRIM(COALESCE(p.areapermisoconcesion, 'SIN_DATO'))) AS concesion,
        UPPER(TRIM(COALESCE(p.tipo_reservorio, 'SIN_DATO'))) AS tipo_reservorio,
        UPPER(TRIM(COALESCE(p.clasificacion, 'SIN_DATO')))  AS clasificacion,
        TRY_CAST(p.coordenadax AS DOUBLE)                   AS lon,
        TRY_CAST(p.coordenaday AS DOUBLE)                   AS lat,
        TRY_CAST(p.adjiv_fecha_inicio AS DATE)              AS perf_inicio,
        TRY_CAST(p.adjiv_fecha_fin AS DATE)                 AS perf_fin,
        TRY_CAST(p.adjiv_fecha_fin_term AS DATE)            AS fecha_terminacion,
        u.fecha_ult,
        COALESCE(u.pet_12m, 0)                              AS pet_12m,
        COALESCE(u.gas_12m, 0)                              AS gas_12m
    FROM raw_listado_pozos_operadoras p
    LEFT JOIN prod_ult u USING (idpozo)
    WHERE p.coordenadax IS NOT NULL AND p.coordenaday IS NOT NULL
      AND TRY_CAST(p.coordenadax AS DOUBLE) BETWEEN -76 AND -52
      AND TRY_CAST(p.coordenaday AS DOUBLE) BETWEEN -56 AND -20
    """)

    # Mart geoespacial: fracturas con coords del pozo (para hexbin)
    con.execute("""
    CREATE OR REPLACE VIEW mart_fracturas_geo AS
    SELECT
        f.id_base_fractura_adjiv,
        f.sigla,
        f.idpozo,
        UPPER(TRIM(COALESCE(f.empresa_informante, 'SIN_DATO'))) AS empresa,
        UPPER(TRIM(COALESCE(f.cuenca, 'SIN_DATO')))             AS cuenca,
        TRY_CAST(f.fecha_fin_fractura AS DATE)                  AS fecha_fin_fractura,
        TRY_CAST(f.cantidad_fracturas AS INTEGER)               AS etapas,
        TRY_CAST(f.arena_bombeada_nacional_tn AS DOUBLE)
          + COALESCE(TRY_CAST(f.arena_bombeada_importada_tn AS DOUBLE), 0) AS arena_tn,
        p.lon, p.lat
    FROM raw_fracturas_adjunto_iv f
    INNER JOIN mart_pozos_geo p USING (idpozo)
    WHERE f.fecha_fin_fractura IS NOT NULL
    """)

    # Mart: trayectorias de pozos Vaca Muerta
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_trayectorias AS
        SELECT
            sigla,
            CAST(idpo AS BIGINT) AS idpozo,
            TRY_CAST(profundidad_final_total_mt AS DOUBLE) AS prof_total_m,
            TRY_CAST(profundidad_vertical_mt AS DOUBLE) AS prof_vertical_m,
            TRY_CAST(largo_rama_horizontal_mt AS DOUBLE) AS rama_horizontal_m,
            TRY_CAST(termfin AS DATE) AS fecha_terminacion,
            date_trunc('month', TRY_CAST(termfin AS DATE)) AS mes_terminacion,
            CASE WHEN tipopozo = '4' THEN 'HORIZONTAL'
                 WHEN tipopozo = '3' THEN 'DIRECCIONAL'
                 WHEN tipopozo = '1' THEN 'VERTICAL'
                 ELSE 'OTRO' END AS tipo_pozo
        FROM raw_trayectorias_pozos_vm
        WHERE termfin IS NOT NULL
        """)
    except Exception as e:
        log(f"  mart_trayectorias: {e}")

    # Mart: sísmicas 3D (geo)
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_sismicas_3d AS
        SELECT
            proyect AS proyecto,
            UPPER(TRIM(COALESCE(empresa_informante, 'SIN_DATO'))) AS empresa,
            geojson,
            TRY_CAST(alta_planos_base AS DATE) AS alta,
            TRY_CAST(modificacion_planos_base AS DATE) AS ultima_modif
        FROM raw_sismicas_3d
        WHERE geojson IS NOT NULL
        """)
    except Exception as e:
        log(f"  mart_sismicas_3d: {e}")

    # Mart: permisos de exploración
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_permisos_exploracion AS
        SELECT
            nombre_de_area AS area,
            codigo_de_sesco AS codigo,
            UPPER(TRIM(COALESCE(empresa_operadora_sesco, 'SIN_DATO'))) AS operadora,
            UPPER(TRIM(COALESCE(empresa_informante, 'SIN_DATO'))) AS informante,
            participacion_en_consorcio AS consorcio,
            geojson,
            TRY_CAST(alta_planos_base AS DATE) AS alta
        FROM raw_permisos_exploracion
        WHERE nombre_de_area IS NOT NULL
        """)
    except Exception as e:
        log(f"  mart_permisos: {e}")

    # Mart: precios gas natural por cuenca y segmento
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_precios_gas AS
        SELECT
            make_date(CAST(anio AS INT), CAST(mes AS INT), 1) AS fecha,
            UPPER(TRIM(cuenca)) AS cuenca,
            UPPER(TRIM(contrato)) AS contrato,
            TRY_CAST(precio_distribuidora AS DOUBLE) AS p_distribuidora,
            TRY_CAST(precio_gnc AS DOUBLE) AS p_gnc,
            TRY_CAST(precio_usina AS DOUBLE) AS p_usina,
            TRY_CAST(precio_industria AS DOUBLE) AS p_industria,
            TRY_CAST(precio_ppp AS DOUBLE) AS p_ppp,
            TRY_CAST(precio_expo AS DOUBLE) AS p_export
        FROM raw_precios_gas_natural
        WHERE anio IS NOT NULL
        """)
    except Exception as e:
        log(f"  mart_precios_gas: {e}")

    # Mart: regalías unificadas (crudo + gas)
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_regalias AS
        SELECT 'CRUDO' AS recurso, * FROM raw_regalias_crudo
        """)
        con.execute("""
        CREATE OR REPLACE VIEW mart_regalias_gas AS
        SELECT 'GAS' AS recurso, * FROM raw_regalias_gas
        """)
    except Exception as e:
        log(f"  mart_regalias: {e}")

    # Mart: precios internacionales (WB pink sheet) - filtrar crude/gas
    try:
        con.execute("""
        CREATE OR REPLACE VIEW mart_wb_commodities AS
        SELECT fecha, commodity, valor
        FROM raw_wb_commodity_prices
        WHERE commodity ILIKE '%crude%'
           OR commodity ILIKE '%natural_gas%'
           OR commodity ILIKE '%lng%'
        """)
    except Exception as e:
        log(f"  mart_wb: {e}")

    log("  marts creados: mart_produccion_mensual, mart_fracturas_mensual, mart_perforacion_mensual, mart_macro, mart_iap_ceipa, mart_pozos_geo, mart_fracturas_geo, mart_trayectorias, mart_sismicas_3d, mart_permisos_exploracion, mart_precios_gas, mart_regalias*, mart_wb_commodities")


def summary(con: duckdb.DuckDBPyConnection) -> None:
    tables = con.execute(
        "SELECT table_name, table_type FROM information_schema.tables WHERE table_schema='main' ORDER BY 1"
    ).fetchall()
    print("\n=== Warehouse ceipa.duckdb ===")
    for name, kind in tables:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  [{kind:11}] {name:42} {n:>12,} filas")
        except Exception as e:
            print(f"  [{kind:11}] {name:42} err: {e}")


def main() -> int:
    con = duckdb.connect(str(DB_PATH))
    log("== Ingesta Sec. Energía ==")
    ingest_energia(con)
    log("== Ingesta BCRA ==")
    ingest_bcra(con)
    log("== Ingesta INDEC (Series SSPM) ==")
    ingest_indec(con)
    log("== Marts ==")
    try:
        build_marts(con)
    except Exception as e:
        log(f"  ERROR marts: {e}")
    summary(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
