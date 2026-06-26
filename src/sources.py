"""
Catálogo de fuentes de datos abiertos para el Observatorio CEIPA.

Cada entrada es una fuente verificada (2026-04).
Los pipelines de ingest.py leen este catálogo.
"""

from dataclasses import dataclass


@dataclass
class Source:
    key: str
    title: str
    organism: str
    url: str
    fmt: str
    frequency: str
    notes: str = ""
    refresh: bool = False  # True = re-descargar SIEMPRE (fuentes que cambian seguido)


ENERGIA_SOURCES = [
    Source(
        key="produccion_pozos_capitulo_iv",
        title="Maestro de pozos - Capítulo IV",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/cb5c0f04-7835-45cd-b982-3e25ca7d7751/download/capitulo-iv-pozos.csv",
        fmt="csv",
        frequency="mensual",
        notes="Maestro de pozos declarados (1 fila por pozo).",
    ),
    Source(
        key="produccion_no_convencional",
        title="Producción mensual por pozo — No Convencional (shale/tight)",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv",
        fmt="csv",
        frequency="mensual",
        notes="Núcleo del Observatorio: producción por pozo/empresa/mes (Vaca Muerta).",
    ),
    Source(
        key="listado_pozos_operadoras",
        title="Listado de pozos cargados por empresas operadoras",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/cbfa4d79-ffb3-4096-bab5-eb0dde9a8385/download/listado-de-pozos-cargados-por-empresas-operadoras.csv",
        fmt="csv",
        frequency="mensual",
        notes="Maestro de pozos con fechas de inicio/fin de perforación y terminación.",
    ),
    Source(
        key="fracturas_adjunto_iv",
        title="Datos de fractura de pozos (Adjunto IV)",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv",
        fmt="csv",
        frequency="diario",
        notes="Etapas de fractura, arena, agua. Proxy directo de actividad de servicios especiales.",
    ),
    Source(
        key="concesiones_explotacion",
        title="Producción de hidrocarburos — Concesiones de Explotación",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/81cfad0a-4162-4f85-ad71-837f5a5fae57/resource/b6af0c0e-e463-4cb7-b458-373aafc0ac08/download/produccin-hidrocarburos-concesiones-de-explotacin.csv",
        fmt="csv",
        frequency="anual",
        notes="Concesiones activas con empresa concesionaria.",
    ),
    Source(
        key="yacimientos",
        title="Producción hidrocarburos — Yacimientos",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/7378520e-4d10-48a9-92e9-7e20e69a8277/resource/6130ac5d-e78e-4aef-9925-030db6434c56/download/produccin-hidrocarburos-yacimientos.csv",
        fmt="csv",
        frequency="anual",
        notes="Límites de yacimientos (geojson).",
    ),
    Source(
        key="registro_empresas_upstream",
        title="Registro de empresas petroleras del upstream",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/2b227214-829d-4ef5-9f3e-c9bb49fa2f4c/resource/dec5cd65-8ac7-4f76-933c-aa6ae498fd3e/download/registro-de-empresas-petroleras-del-upstream-inscripciones-anuales.csv",
        fmt="csv",
        frequency="anual",
        notes="Padrón oficial de empresas registradas.",
    ),
    Source(
        key="produccion_gas_1950",
        title="Producción Gas Natural desde 1950",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/5210866d-2caf-43fd-95d8-085dc18f39cc/resource/0622e111-dbfd-45e9-bf94-bdce83b978c0/download/producciongasnaturaldesde-1950.csv",
        fmt="csv",
        frequency="anual",
        notes="Serie histórica larga.",
    ),
    Source(
        key="produccion_petroleo_1950",
        title="Producción de Petróleo desde 1950",
        organism="Secretaría de Energía",
        url="http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/informacion_estadistica/serie-produccion-petroleo-total-pais-desde-1950.csv",
        fmt="csv",
        frequency="anual",
        notes="Serie histórica larga.",
    ),
    Source(
        key="precio_internacional_crudo",
        title="Precio Internacional del Petróleo Crudo (Decreto 488/2020)",
        organism="Secretaría de Energía",
        url="http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/pi/precio_internacional.xlsx",
        fmt="xlsx_pi",
        frequency="mensual",
        notes="Precio referencia usado para regalías. Excel con encabezado irregular.",
        refresh=True,
    ),
    # === Tanda 1 nuevas fuentes (2026-04) ===
    Source(
        key="trayectorias_pozos_vm",
        title="Trayectorias de pozos — Vaca Muerta",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/f5c0b5a5-b402-44d7-8fe0-f9e4fcb78b8d/resource/94741ac7-4f46-4efe-b112-d3f82a4ef7c5/download/trayectoria-de-pozos-vaca-muerta.csv",
        fmt="csv",
        frequency="mensual",
        notes="Profundidad vertical, longitud de rama horizontal, geometría 3D. Clave para análisis de eficiencia shale.",
    ),
    Source(
        key="permisos_exploracion",
        title="Exploración hidrocarburos — Permisos de exploración",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/66044d22-6657-47d1-b0bb-ecc7c1d37a44/resource/c33b6176-6025-41ee-b174-d4d7653735c3/download/exploracin-hidrocarburos-permisos-de-exploracin.csv",
        fmt="csv",
        frequency="mensual",
        notes="Áreas con permiso de exploración activo, operadora, consorcio. Leading indicator de desarrollo futuro.",
    ),
    Source(
        key="sismicas_3d",
        title="Exploración hidrocarburos — Sísmicas 3D",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/11540156-6454-47c8-9748-c8f8705f62c0/resource/dae27747-fb0b-49a2-9be0-712bfc0f6266/download/exploracin-hidrocarburos-ssmicas-3d.csv",
        fmt="csv",
        frequency="mensual",
        notes="Proyectos 3D registrados. Precede perforación en 12-24 meses.",
    ),
    Source(
        key="sismicas_2d",
        title="Exploración hidrocarburos — Líneas sísmicas 2D",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/071b7a3e-0a34-426c-a605-d24e7bdef9a3/resource/fb01c3ae-dc61-4845-885a-457ea9c5f796/download/exploracin-hidrocarburos-lineas-ssmicas-2d.csv",
        fmt="csv",
        frequency="mensual",
        notes="Líneas sísmicas 2D registradas.",
    ),
    Source(
        key="precios_gas_natural",
        title="Precios de gas natural (Res. 1/2018)",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/5ddbdfbb-b6f9-4bc1-9e71-0055e86cf552/resource/d87ca6ab-2979-474b-994a-e4ba259bb217/download/precios-de-gas-natural-res-1-2018.csv",
        fmt="csv",
        frequency="mensual",
        notes="Precio por cuenca, contrato y destino (distribuidora, GNC, usina, industria, export, PPP).",
    ),
    Source(
        key="regalias_crudo",
        title="Regalías — Petróleo crudo",
        organism="Secretaría de Energía",
        url="http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/informacion_estadistica/regalias/Regalias_CRUDO.zip",
        fmt="zip",
        frequency="mensual",
        notes="Regalías pagadas por empresa/provincia/mes — proxy de valor generado.",
    ),
    Source(
        key="regalias_gas",
        title="Regalías — Gas natural",
        organism="Secretaría de Energía",
        url="http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/informacion_estadistica/regalias/Regalias_GAS.zip",
        fmt="zip",
        frequency="mensual",
        notes="Regalías gas natural.",
    ),
    Source(
        key="reservas_2024",
        title="Reservas de petróleo y gas al 31-12-2024",
        organism="Secretaría de Energía",
        url="http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/informacion_estadistica/reservas/reservas_al_31-12-2024.zip",
        fmt="zip",
        frequency="anual",
        notes="Reservas comprobadas/probables por yacimiento/empresa — vida útil estructural.",
    ),
    Source(
        key="canon_2026",
        title="Canon hidrocarburífero 2026",
        organism="Secretaría de Energía",
        url="https://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/mercado_hidrocarburos/canon/canon_hidrocarburifero_2026.xlsx",
        fmt="xlsx",
        frequency="anual",
        notes="Canon por área — costo fijo operadoras.",
    ),
    Source(
        key="wb_commodity_prices",
        title="World Bank Pink Sheet — precios commodities",
        organism="World Bank",
        url="https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
        fmt="xlsx_wb",
        frequency="mensual",
        notes="Precios mensuales: crude Brent/WTI/Dubai, gas natural US/EU/LNG. Sin API key.",
        refresh=True,
    ),
    Source(
        key="wti_spot_diario",
        title="WTI spot diario (Cushing, EIA vía FRED)",
        organism="EIA / FRED",
        url="https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO",
        fmt="csv_fred",
        frequency="diaria",
        notes="Precio spot diario WTI Cushing. Sin API key. Spot real (a diferencia del promedio mensual rezagado del WB).",
        refresh=True,
    ),
    Source(
        key="estudios_ambientales",
        title="Listado de Estudios Ambientales (upstream)",
        organism="Secretaría de Energía",
        url="http://datos.energia.gob.ar/dataset/d961b791-19b5-4ada-a64c-66cba740f532/resource/7b8583fe-8994-4efa-9fbf-79c4a3f2f467/download/listado-de-estudios-ambientales.csv",
        fmt="csv",
        frequency="mensual",
        notes="EIAs presentados — leading indicator de actividad futura.",
    ),
]


# BCRA API v4 — /Monetarias/{id}?desde&hasta&limit
BCRA_API_BASE = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias"
BCRA_VARIABLES = {
    1:  ("reservas_internacionales", "Reservas internacionales BCRA (USD)"),
    4:  ("tc_minorista", "Tipo de cambio minorista (promedio vendedor)"),
    5:  ("tc_mayorista", "Tipo de cambio mayorista de referencia"),
    7:  ("tasa_badlar", "Tasa BADLAR bancos privados"),
    27: ("ipc_mensual", "IPC variación mensual"),
    28: ("ipc_interanual", "IPC variación interanual"),
    15: ("base_monetaria", "Base monetaria"),
}


# datos.gob.ar / Series de Tiempo API — IDs verificados
SERIES_SSPM = {
    # Precios y actividad
    "ipc_nivel_general":        "148.3_INIVELNAL_DICI_M_26",
    "emae_original":            "143.3_NO_PR_2004_A_21",
    # Empleo registrado sector privado (trimestral, 1996-)
    "empleo_mineria_petroleo":  "155.1_MRIA_PELEO_C_0_0_16",
    "empleo_mineria_petroleo_desest": "155.2_MRIA_PELEO_S_0_0_16",
    "empleo_construccion":      "155.1_CTRUCCIION_C_0_0_12",
    "empleo_industria":         "155.1_ISTRIARIA_C_0_0_9",
    "empleo_total_privado":     "155.1_TLTAL_C_0_0_5",
    "empleo_minas_canteras":    "156.1_EOTACIORAS_0_0_26",
    # Índices salariales
    "salarios_total":           "149.1_TL_REGIADO_OCTU_0_16",
    "salarios_privado":         "149.1_SOR_PRIADO_OCTU_0_25",
    "salarios_publico":         "149.1_SOR_PUBICO_OCTU_0_14",
    "remuneracion_media_real":  "310.1_REMUNERACIDOS_0_M_32",
}
SERIES_API = "https://apis.datos.gob.ar/series/api/series/"


# CIIU relevantes para empleo petrolero
EMPLEO_CIIU_RELEVANTES = ["0610", "0620", "0910"]


ALL_SOURCES = {s.key: s for s in ENERGIA_SOURCES}
