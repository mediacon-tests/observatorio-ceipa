# Observatorio CEIPA — MVP

Sistema de inteligencia de datos sectorial para la **Cámara Empresarial de la Industria Petrolera y Afines del Neuquén (CEIPA)**, construido íntegramente sobre **fuentes públicas argentinas**.

## Qué incluye este MVP

- Pipeline reproducible de ingesta (`src/ingest.py`) para ~12 fuentes oficiales.
- Warehouse analítico en **DuckDB** con vistas de negocio (`mart_*`) y modelo predictivo.
- Dashboard **Streamlit** con 9 páginas:
  1. Resumen ejecutivo con el Índice de Actividad Proveedora CEIPA (IAP-CEIPA).
  2. Actividad de perforación y fractura.
  3. Producción por empresa.
  4. Producción por cuenca y provincia.
  5. Pipeline de proyectos (Estudios de Impacto Ambiental).
  6. **Empleo y salarios** — series SSPM 1996-2026 (Minería y Petróleo, Construcción, Industria, índices salariales).
  7. **Forecast IAP-CEIPA** — SARIMAX(1,1,1)(1,0,1,12) a 12 meses con 3 escenarios y backtest walk-forward.
  8. Macroeconomía (BCRA + INDEC).
  9. Catálogo de fuentes.

## Fuentes integradas

| Organismo | Dataset | Filas actuales |
|---|---|---|
| Sec. Energía | Producción mensual por pozo no convencional | 396.237 |
| Sec. Energía | Maestro de pozos (Capítulo IV) | 85.380 |
| Sec. Energía | Listado de pozos operadoras | 84.242 |
| Sec. Energía | Datos de fractura (Adjunto IV) | 4.666 |
| Sec. Energía | Estudios ambientales | 12.441 |
| Sec. Energía | Concesiones / Yacimientos / Registro empresas | +1.000 |
| Sec. Energía | Precio internacional crudo (Dec. 488/2020), series 1950 | +200 |
| EIA (vía FRED) | WTI spot **diario** (Cushing, `DCOILWTICO`) | 10.186 obs |
| World Bank | Pink Sheet — precios mensuales commodities (Brent/WTI/gas) | 50.031 obs |
| BCRA | Reservas, TC mayorista/minorista, BADLAR, base monetaria, IPC | 10.238 obs |
| INDEC | IPC nivel general, EMAE | 377 obs |

> **Precios de crudo — tres series distintas, no confundir:**
> - **WTI spot diario** (EIA/FRED): precio de mercado en tiempo real con ~días de rezago. Es el que muestra la tarjeta "WTI spot" del resumen.
> - **Pink Sheet WB**: promedio *mensual* con rezago de ~1 mes. Útil para series largas y comparación con otros commodities.
> - **Precio internacional Dec. 488/2020** (Sec. Energía): precio de *referencia* para el cálculo de regalías, no es spot de mercado.

### Refresco de datos

Las fuentes que cambian seguido (`wb_commodity_prices`, `precio_internacional_crudo`, `wti_spot_diario`) están marcadas con `refresh=True` en `src/sources.py` y se **re-descargan en cada corrida** de `python -m src.ingest`. El resto (producción, pozos, etc.) se cachea en `raw/` y solo se baja si falta.

## Quickstart

```bash
cd ceipa_data
python3 -m venv .venv
source .venv/bin/activate
pip install pandas duckdb requests streamlit plotly openpyxl pyarrow

# 1. Descargar datos + construir warehouse
python -m src.ingest

# 2. Entrenar modelo predictivo IAP-CEIPA (SARIMAX + backtest)
python -m src.forecast

# 3. Levantar dashboard
streamlit run src/dashboard/app.py
```

Abrir http://localhost:8501.

## Arquitectura

```
raw/                   CSVs/XLSX descargados (capa bronce)
data/ceipa.duckdb      warehouse analítico
src/
  sources.py           catálogo declarativo de fuentes
  ingest.py            pipeline de ingesta + construcción de marts
  dashboard/app.py     frontend Streamlit
```

### Marts principales

- `mart_produccion_mensual` — producción por empresa/cuenca/provincia/mes.
- `mart_fracturas_mensual` — actividad de estimulación (pozos, etapas, arena, agua).
- `mart_perforacion_mensual` — pozos terminados por mes.
- `mart_macro` — series BCRA + INDEC unificadas.
- `mart_iap_ceipa` — Índice de Actividad Proveedora CEIPA (base 100 = 2017-2019).

## Metodología del IAP-CEIPA

Ponderación:
- 40% pozos fracturados
- 35% etapas de fractura
- 25% arena bombeada (nacional + importada)

Base 100 = promedio mensual 2017-2019. Se publica mensualmente con rezago de ~45 días.

## Roadmap siguiente

- Ingesta de empleo registrado OEDE (CIIU 0610/0620/0910).
- SIPA — remuneraciones promedio por rama.
- Rig count SESCO (OCR de PDFs).
- Parser de CCT 644/12 Petroleros Privados (Boletín Oficial).
- Regalías petroleras provinciales (Neuquén).
- Comercio exterior (tubulares, arena).
- Capa de carga privada por empresa con benchmarking anónimo (N≥5).
- Modelos predictivos (SARIMAX + XGBoost) sobre IAP-CEIPA.
- Simulador de impacto paritario.
