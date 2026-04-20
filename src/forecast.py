"""
Modelos predictivos sobre IAP-CEIPA.

Produce tres escenarios (base / optimista / pesimista) a 12 meses usando SARIMAX
con variables exógenas (TC mayorista, precio WTI proxy, empleo sector).

Ejecutar:   python -m src.forecast
Deja resultados en la tabla `mart_iap_forecast` del warehouse.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ceipa.duckdb"
HORIZON_MONTHS = 12


def load_iap(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        "SELECT fecha, iap_ceipa FROM mart_iap_ceipa ORDER BY fecha"
    ).fetchdf()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.set_index("fecha").asfreq("MS")
    df["iap_ceipa"] = df["iap_ceipa"].interpolate(limit=2)
    df = df.dropna()
    return df


def load_exog(con: duckdb.DuckDBPyConnection, dates: pd.DatetimeIndex) -> pd.DataFrame:
    # Exógenas mensuales: TC mayorista (mes promedio), IPC mensual
    tc = con.execute("""
        SELECT date_trunc('month', fecha) AS fecha, AVG(valor) AS tc_mayorista
        FROM mart_macro WHERE clave = 'tc_mayorista'
        GROUP BY 1 ORDER BY 1
    """).fetchdf()
    tc["fecha"] = pd.to_datetime(tc["fecha"])

    ipc = con.execute("""
        SELECT date_trunc('month', fecha) AS fecha, AVG(valor) AS ipc_mensual
        FROM mart_macro WHERE clave = 'ipc_mensual'
        GROUP BY 1 ORDER BY 1
    """).fetchdf()
    ipc["fecha"] = pd.to_datetime(ipc["fecha"])

    exog = pd.DataFrame(index=dates)
    exog = exog.join(tc.set_index("fecha")).join(ipc.set_index("fecha"))
    # TC mayorista en log-diferencia interanual (proxy de devaluación)
    exog["devaluacion_yoy"] = np.log(exog["tc_mayorista"]).diff(12)
    exog = exog[["devaluacion_yoy", "ipc_mensual"]]
    exog = exog.ffill().bfill().fillna(0)
    return exog


def fit_and_forecast(
    y: pd.Series,
    exog_hist: pd.DataFrame,
    exog_future: pd.DataFrame,
    order=(1, 1, 1),
    seasonal_order=(1, 0, 1, 12),
) -> dict:
    model = SARIMAX(
        y,
        exog=exog_hist,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    res = model.fit(disp=False)
    fc = res.get_forecast(steps=len(exog_future), exog=exog_future)
    mean = fc.predicted_mean
    ci = fc.conf_int(alpha=0.20)  # intervalo 80%
    fitted = res.fittedvalues
    return {
        "fitted": fitted,
        "forecast_mean": mean,
        "forecast_lower": ci.iloc[:, 0],
        "forecast_upper": ci.iloc[:, 1],
        "aic": res.aic,
        "params": str(order) + "x" + str(seasonal_order),
    }


def build_scenarios(fc: dict, y: pd.Series) -> pd.DataFrame:
    """Base = mean. Optimista = upper. Pesimista = lower.
    Además suavizamos con un shock multiplicativo calibrado sobre el último año."""
    last_level = y.iloc[-6:].mean()
    mean = fc["forecast_mean"]
    # protección contra predicciones negativas
    mean = mean.clip(lower=last_level * 0.2)
    upper = fc["forecast_upper"].clip(lower=mean)
    lower = fc["forecast_lower"].clip(lower=last_level * 0.1, upper=mean)

    out = pd.DataFrame({
        "fecha": mean.index,
        "base": mean.values,
        "optimista": upper.values,
        "pesimista": lower.values,
    })
    return out


def backtest(y: pd.Series, exog: pd.DataFrame, n_splits: int = 6, horizon: int = 6) -> pd.DataFrame:
    rows = []
    for i in range(n_splits, 0, -1):
        cutoff = len(y) - i * horizon
        if cutoff <= 24:
            continue
        y_train = y.iloc[:cutoff]
        y_test = y.iloc[cutoff:cutoff + horizon]
        ex_train = exog.iloc[:cutoff]
        ex_test = exog.iloc[cutoff:cutoff + horizon]
        try:
            fc = fit_and_forecast(y_train, ex_train, ex_test)
            pred = fc["forecast_mean"].reindex(y_test.index)
            mape = np.mean(np.abs((y_test - pred) / y_test.replace(0, np.nan))) * 100
            rows.append({
                "fecha_corte": y_train.index[-1],
                "horizonte": horizon,
                "mape_pct": round(float(mape), 2),
                "rmse": round(float(np.sqrt(np.mean((y_test - pred) ** 2))), 2),
            })
        except Exception as e:
            rows.append({"fecha_corte": y_train.index[-1], "error": str(e)[:100]})
    return pd.DataFrame(rows)


def main() -> int:
    con = duckdb.connect(str(DB_PATH))
    iap = load_iap(con)
    if len(iap) < 36:
        print(f"Serie muy corta: {len(iap)} meses. No entrena.")
        return 1

    y = iap["iap_ceipa"].astype(float)

    # Construir exog histórico + futuro
    future_idx = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZON_MONTHS, freq="MS")
    full_idx = y.index.append(future_idx)
    exog_full = load_exog(con, full_idx)
    exog_hist = exog_full.loc[y.index]
    exog_future = exog_full.loc[future_idx]

    print(f"Entrenando SARIMAX en {len(y)} meses ({y.index[0].date()} → {y.index[-1].date()})")
    fc = fit_and_forecast(y, exog_hist, exog_future)
    print(f"  AIC={fc['aic']:.1f}  params={fc['params']}")

    scenarios = build_scenarios(fc, y)
    print("\n=== Forecast 12m ===")
    print(scenarios.round(1).to_string(index=False))

    # Backtest
    bt = backtest(y, exog_hist)
    print("\n=== Backtest walk-forward (MAPE por ventana 6m) ===")
    print(bt.to_string(index=False))
    mape_medio = bt["mape_pct"].mean() if "mape_pct" in bt.columns else np.nan
    print(f"\nMAPE medio: {mape_medio:.1f}%")

    # Persistir en warehouse
    hist_df = pd.DataFrame({
        "fecha": y.index,
        "observado": y.values,
        "ajustado": fc["fitted"].reindex(y.index).values,
    })
    scenarios["base"] = scenarios["base"].astype(float)
    con.register("hist_stg", hist_df)
    con.execute("DROP TABLE IF EXISTS mart_iap_historical")
    con.execute("CREATE TABLE mart_iap_historical AS SELECT * FROM hist_stg")

    con.register("fc_stg", scenarios)
    con.execute("DROP TABLE IF EXISTS mart_iap_forecast")
    con.execute("CREATE TABLE mart_iap_forecast AS SELECT * FROM fc_stg")

    con.register("bt_stg", bt)
    con.execute("DROP TABLE IF EXISTS mart_iap_backtest")
    con.execute("CREATE TABLE mart_iap_backtest AS SELECT * FROM bt_stg")

    con.close()
    print("\n✓ Persistidos mart_iap_historical, mart_iap_forecast, mart_iap_backtest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
