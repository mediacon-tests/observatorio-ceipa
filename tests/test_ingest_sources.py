"""Smoke test de conectividad con las APIs estables.

Las URLs CKAN de datos.energia.gob.ar no soportan HEAD confiablemente
(devuelven 504 en HEAD pero GET funciona bien). No las probamos acá —
la validación real es correr `python -m src.ingest` periódicamente.

Marca: slow (usa la red). Correr con:
    pytest -m 'not slow'   → skip
    pytest                 → incluye
"""

from __future__ import annotations

import pytest
import requests
import urllib3

from src.sources import BCRA_API_BASE, SERIES_API, SERIES_SSPM

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

pytestmark = pytest.mark.slow


def test_bcra_api_alive():
    r = requests.get(
        f"{BCRA_API_BASE}/1?desde=2026-01-01&hasta=2026-01-10&limit=5",
        timeout=20, verify=False,
    )
    assert r.status_code == 200, f"BCRA API devolvió {r.status_code}"
    data = r.json().get("results", [])
    assert len(data) > 0, "BCRA API devolvió resultados vacíos"


def test_indec_series_api_alive():
    sid = SERIES_SSPM["ipc_nivel_general"]
    r = requests.get(
        f"{SERIES_API}?ids={sid}&format=json&limit=3",
        timeout=20, verify=False,
    )
    assert r.status_code == 200, f"INDEC Series API devolvió {r.status_code}"


def test_world_bank_pink_sheet_alive():
    """Descarga parcial del Pink Sheet para confirmar URL vigente."""
    url = ("https://thedocs.worldbank.org/en/doc/"
           "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
           "CMO-Historical-Data-Monthly.xlsx")
    r = requests.get(url, timeout=30, verify=False,
                     headers={"Range": "bytes=0-4096"}, stream=True)
    assert r.status_code in (200, 206), f"WB devolvió {r.status_code}"


def test_datos_energia_ckan_alive():
    """CKAN responde a una búsqueda acotada. El endpoint es lento; reintenta."""
    url = "https://datos.energia.gob.ar/api/3/action/package_search?q=produccion&rows=1"
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60, verify=False)
            if r.status_code == 200:
                data = r.json()
                assert data.get("success") is True
                return
            last_err = f"HTTP {r.status_code}"
        except requests.exceptions.Timeout:
            last_err = "timeout"
            continue
    pytest.skip(f"CKAN server lento/caído tras 3 intentos ({last_err}); "
                "no invalidamos pipeline — ingest real tolera reintentos")
