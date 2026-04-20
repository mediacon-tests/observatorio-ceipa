"""
Utilidades de export — CSV por página y PDF del reporte mensual.

CSV: botones `st.download_button` con datos ya en memoria.
PDF: renderiza un snapshot HTML del resumen ejecutivo y lo convierte con Playwright.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]


def csv_button(df: pd.DataFrame, filename: str, label: str = "Descargar CSV") -> None:
    """Download button para un DataFrame."""
    if df is None or len(df) == 0:
        return
    buf = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"↓ {label}",
        data=buf,
        file_name=filename,
        mime="text/csv",
        help="Descarga los datos de esta sección en CSV (UTF-8).",
        use_container_width=False,
    )


def multi_csv_buttons(datasets: dict[str, pd.DataFrame], prefix: str = "ceipa") -> None:
    """Varios download buttons en línea (un CSV por dataset)."""
    today = datetime.now().strftime("%Y-%m-%d")
    cols = st.columns(len(datasets))
    for i, (name, df) in enumerate(datasets.items()):
        with cols[i]:
            if df is not None and len(df):
                buf = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"↓ {name} ({len(df):,} filas)",
                    data=buf,
                    file_name=f"{prefix}_{name}_{today}.csv",
                    mime="text/csv",
                )


def generate_monthly_report_pdf(url: str = "http://localhost:8501/") -> bytes | None:
    """Renderiza el Resumen ejecutivo a PDF usando Playwright Chromium headless.
    Requiere que el dashboard esté corriendo en `url`.
    Retorna los bytes del PDF o None si falla."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(
                viewport={"width": 1400, "height": 1800},
                device_scale_factor=1.5,
            )
            page = ctx.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(3500)
            # Asegurarse de estar en Resumen (debe ser la página inicial)
            try:
                page.get_by_text("Resumen ejecutivo", exact=True).first.click(timeout=3000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2500)
            except Exception:
                pass
            # Ocultar sidebar para PDF limpio
            page.add_style_tag(content="""
                section[data-testid="stSidebar"] { display: none !important; }
                .main { margin-left: 0 !important; }
                .block-container { max-width: 100% !important; padding: 2rem !important; }
            """)
            page.wait_for_timeout(1200)
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "15mm", "right": "12mm",
                        "bottom": "15mm", "left": "12mm"},
            )
            browser.close()
            return pdf_bytes
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None


def pdf_report_button(url: str = "http://localhost:8501/") -> None:
    """Botón 'Descargar reporte mensual'. Genera el PDF on-demand."""
    today = datetime.now().strftime("%Y-%m-%d")
    if st.button("↓ Generar reporte mensual (PDF)", use_container_width=False):
        with st.spinner("Generando reporte..."):
            pdf = generate_monthly_report_pdf(url)
        if pdf:
            st.download_button(
                label=f"↓ Reporte CEIPA {today}.pdf",
                data=pdf,
                file_name=f"reporte_ceipa_{today}.pdf",
                mime="application/pdf",
                use_container_width=False,
            )
        else:
            st.warning("No se pudo generar el PDF. Verifica que el dashboard esté corriendo.")
