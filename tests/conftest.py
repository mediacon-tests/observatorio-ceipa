"""Fixtures compartidos para tests del Observatorio CEIPA."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ceipa.duckdb"


@pytest.fixture(scope="session")
def con() -> duckdb.DuckDBPyConnection:
    """Conexión read-only al warehouse. Requiere que exista el DB."""
    if not DB_PATH.exists():
        pytest.skip(f"Warehouse no encontrado en {DB_PATH}. Correr `python -m src.ingest` primero.")
    return duckdb.connect(str(DB_PATH), read_only=True)


@pytest.fixture(scope="session")
def table_names(con) -> list[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]
