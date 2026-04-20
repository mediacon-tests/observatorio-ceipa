"""Páginas del dashboard CEIPA."""

from src.dashboard.sections import (
    resumen,
    actividad,
    produccion_empresa,
    produccion_cuenca,
    pipeline_eias,
    mapa_gis,
    trayectorias,
    precios_gas,
    precios_intl,
    empleo,
    forecast_page,
    macro,
    catalogo,
)

# Mapa orden + label → módulo
PAGES = [
    ("Resumen ejecutivo", resumen),
    ("Actividad de perforación y fractura", actividad),
    ("Producción por empresa", produccion_empresa),
    ("Producción por cuenca / provincia", produccion_cuenca),
    ("Pipeline de proyectos (EIAs)", pipeline_eias),
    ("Mapa GIS", mapa_gis),
    ("Trayectorias shale", trayectorias),
    ("Precios de gas", precios_gas),
    ("Precios internacionales", precios_intl),
    ("Empleo y salarios", empleo),
    ("Forecast IAP-CEIPA", forecast_page),
    ("Macroeconomía y precios", macro),
    ("Catálogo de fuentes", catalogo),
]
