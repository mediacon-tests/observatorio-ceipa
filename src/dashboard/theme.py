"""
Theme CEIPA — Editorial (fondo blanco unificado).

Principios:
- Fondo blanco en toda la app (main y sidebar iguales).
- Sidebar sin fondo oscuro, logo tipográfico minimal.
- Charts sin card ni border: fluyen con la página.
- Tipografía editorial: Fraunces serif + Inter Tight + JetBrains Mono.
- Un solo color de acento (burgundy #A8322D) usado con disciplina.
"""

from __future__ import annotations

from typing import Iterable

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


PALETTE = {
    "bg":           "#FFFFFF",
    "surface":      "#FFFFFF",
    "surface_2":    "#F7F5F0",   # para hover y tabla header sutil
    "border":       "#E4DFD5",
    "border_soft":  "#EFECE5",
    "rule":         "#1A1A1A",
    "text":         "#111111",
    "text_muted":   "#5E564A",
    "text_soft":    "#8F8878",
    "primary":      "#A8322D",
    "primary_soft": "rgba(168, 50, 45, 0.07)",
    "accent":       "#0B2545",
    "success":      "#1F6B3A",
    "danger":       "#7F1D1D",
    "gridline":     "#EFECE5",
    "shadow":       "rgba(14, 14, 14, 0.04)",
}

# Compat keys para código legacy que hacía COLORS["sidebar_bg"] etc.
PALETTE.update({
    "sidebar_bg": PALETTE["bg"],
    "sidebar_text": PALETTE["text"],
    "sidebar_muted": PALETTE["text_muted"],
    "sidebar_accent": PALETTE["primary"],
})


def _css(c: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, .stApp {{
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
    color: {c['text']};
    background: {c['bg']} !important;
}}
.stApp {{ background: {c['bg']} !important; }}

.block-container {{
    padding-top: 1.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 1280px;
}}

/* Titulares SERIF */
h1 {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.028em !important;
    color: {c['text']} !important;
    font-size: 2.6rem !important;
    line-height: 1.02 !important;
    margin: 0.3rem 0 0.3rem 0 !important;
}}
h2 {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
    color: {c['text']} !important;
    font-size: 1.4rem !important;
    line-height: 1.15 !important;
    margin: 1.8rem 0 0.55rem 0 !important;
}}
h3 {{
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: {c['text']} !important;
}}
p, div, label, span {{ color: {c['text']}; }}

/* ============ SIDEBAR: blanco, minimal, tipografía editorial ============ */
section[data-testid="stSidebar"] {{
    background: {c['bg']} !important;
    border-right: 1px solid {c['border']};
}}
section[data-testid="stSidebar"] > div {{
    padding-top: 0.5rem;
}}
section[data-testid="stSidebar"] * {{ color: {c['text']} !important; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif !important;
    color: {c['text']} !important;
}}

/* Labels de sidebar: small caps letterspaced */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p strong {{
    color: {c['text_muted']} !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.16em;
}}

/* Radio (menú de secciones) — bullets minimalistas estilo índice */
section[data-testid="stSidebar"] [role="radiogroup"] {{
    gap: 0 !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
    color: {c['text']} !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.92rem !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.2rem 0.45rem 0.75rem !important;
    border-left: 2px solid transparent !important;
    border-radius: 0 !important;
    transition: all 0.12s ease;
    cursor: pointer;
    margin: 0 !important;
    border-bottom: 1px solid {c['border_soft']};
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:last-child {{
    border-bottom: none;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    border-left-color: {c['text_soft']} !important;
    background: {c['surface_2']} !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {{
    border-left-color: {c['primary']} !important;
    color: {c['primary']} !important;
    font-weight: 600 !important;
}}
/* Minimizar los circulitos por defecto del radio para estética más editorial */
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{
    transform: scale(0.7);
    opacity: 0.55;
}}

/* Inputs/selects sidebar */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {{
    background: {c['bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 2px !important;
    color: {c['text']} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background-color: {c['primary']} !important;
    color: #FFFFFF !important;
    border-radius: 2px !important;
    font-size: 0.72rem !important;
}}

/* Slider */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{
    background: {c['primary']} !important;
    border-color: {c['primary']} !important;
}}

/* Captions */
[data-testid="stCaptionContainer"], .stCaption, small {{
    color: {c['text_muted']} !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-style: normal;
    line-height: 1.5;
}}

/* ============ PLOTLY: sin card, transparente, flow ============ */
[data-testid="stPlotlyChart"] {{
    background: transparent !important;
    border-radius: 0;
    box-shadow: none !important;
    border: none !important;
    padding: 0;
    margin-bottom: 0.5rem;
    overflow: hidden !important;
}}
[data-testid="stPlotlyChart"] > div, [data-testid="stPlotlyChart"] iframe,
.js-plotly-plot, .plot-container {{
    overflow: hidden !important;
    background: transparent !important;
}}
.main-svg {{ overflow: visible !important; background: transparent !important; }}

/* Pydeck — leve borde, no card */
[data-testid="stDeckGlJsonChart"] {{
    border-radius: 2px;
    overflow: hidden;
    border: 1px solid {c['border']};
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border-radius: 0;
    overflow: hidden;
    border-top: 2px solid {c['rule']};
    border-bottom: 1px solid {c['border']};
    background: transparent;
}}
[data-testid="stDataFrame"] > div {{ overflow: hidden !important; border-radius: 0; background: transparent; }}

/* Tables editoriales */
div[data-testid="stTable"] table {{
    width: 100%;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.86rem;
    background: transparent;
    border-radius: 0;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    border-top: 2px solid {c['rule']};
    box-shadow: none;
}}
div[data-testid="stTable"] thead th {{
    background: transparent !important;
    color: {c['text']} !important;
    font-weight: 600 !important;
    font-size: 0.66rem !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 0.7rem 0.85rem !important;
    border: none !important;
    border-bottom: 1px solid {c['rule']} !important;
    text-align: left !important;
}}
div[data-testid="stTable"] tbody td {{
    padding: 0.55rem 0.85rem !important;
    border-top: none !important;
    border-bottom: 1px solid {c['border_soft']} !important;
    border-left: none !important;
    border-right: none !important;
    color: {c['text']} !important;
    background: transparent !important;
    font-variant-numeric: tabular-nums;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
}}
div[data-testid="stTable"] tbody td:first-child {{
    font-family: 'IBM Plex Sans', sans-serif;
}}
div[data-testid="stTable"] tbody tr:hover td {{ background: {c['primary_soft']} !important; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 1.8rem;
    border-bottom: 1px solid {c['rule']};
}}
.stTabs [data-baseweb="tab"] {{
    height: 38px;
    padding: 0 0;
    background: transparent;
    border-radius: 0;
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {c['text_muted']};
}}
.stTabs [aria-selected="true"] {{
    background: transparent !important;
    color: {c['primary']} !important;
    border-bottom: 2px solid {c['primary']} !important;
}}

/* Expander */
.streamlit-expanderHeader {{
    background: transparent;
    border: none;
    border-top: 1px solid {c['border']};
    border-radius: 0;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 600;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {c['text']} !important;
    padding-left: 0 !important;
}}

/* Alerts */
[data-testid="stAlert"] {{
    border-radius: 0 !important;
    border: none !important;
    border-left: 3px solid {c['primary']} !important;
    background: {c['primary_soft']} !important;
    color: {c['text']} !important;
    box-shadow: none !important;
    font-family: 'IBM Plex Sans', sans-serif;
}}

/* Multiselect tags en main */
.stMultiSelect [data-baseweb="tag"] {{
    background-color: {c['text']} !important;
    color: #FFFFFF !important;
    border-radius: 2px !important;
    font-weight: 500;
    font-size: 0.75rem;
}}

/* Overflow global */
section.main > div.block-container {{ overflow-x: hidden; }}

/* Ocultar chrome nativo de Streamlit (botón Deploy, menú, footer "Made with") */
[data-testid="stDeployButton"],
[data-testid="stToolbar"],
.stDeployButton,
button[kind="headerNoPadding"],
footer {{
    display: none !important;
    visibility: hidden !important;
}}
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 0 !important;
}}
#MainMenu {{ display: none !important; }}

/* st.metric — editorial */
[data-testid="stMetric"] {{
    background: transparent;
    padding: 0.9rem 0 0.6rem 0;
    border-radius: 0;
    border-top: 1px solid {c['border']};
    box-shadow: none;
}}
[data-testid="stMetricLabel"] {{
    color: {c['text_muted']} !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.62rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15em !important;
}}
[data-testid="stMetricValue"] {{
    color: {c['text']} !important;
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif !important;
    font-weight: 600 !important;
    font-size: 2rem !important;
    letter-spacing: -0.02em !important;
    font-variant-numeric: tabular-nums;
}}
[data-testid="stMetricDelta"] {{
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.78rem !important;
}}

hr {{ border: none !important; border-top: 1px solid {c['border']} !important; margin: 1.8rem 0 !important; }}

::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-thumb {{ background: {c['border']}; border-radius: 0; }}
::-webkit-scrollbar-thumb:hover {{ background: {c['text_soft']}; }}


/* =========== Componentes CEIPA =========== */

/* Logo wordmark minimal para sidebar */
.ceipa-logo {{
    padding: 0.25rem 0 1rem 0;
    border-bottom: 1px solid {c['border']};
    margin-bottom: 1.1rem;
}}
.ceipa-logo .name {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
    font-size: 1.45rem;
    line-height: 1;
    letter-spacing: -0.02em;
    color: {c['text']};
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
}}
.ceipa-logo .name::before {{
    content: "";
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {c['primary']};
    display: inline-block;
    transform: translateY(-2px);
}}
.ceipa-logo .tagline {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.64rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {c['text_muted']};
    margin-top: 0.45rem;
    padding-left: 1.1rem;
}}

/* Eyebrow */
.ceipa-eyebrow {{
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-weight: 700;
    font-size: 0.68rem;
    color: {c['primary']};
    margin: 0 0 0.55rem 0;
    display: block;
    font-family: 'IBM Plex Sans', sans-serif;
}}

.ceipa-section-title {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
    font-size: 1.8rem;
    line-height: 1.08;
    letter-spacing: -0.02em;
    color: {c['text']};
    margin: 0 0 0.4rem 0;
}}

.ceipa-section-subtitle {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {c['text_muted']};
    font-size: 0.95rem;
    font-weight: 400;
    line-height: 1.5;
    max-width: 820px;
    margin: 0 0 1rem 0;
}}

/* Hero masthead */
.ceipa-hero {{
    padding: 0.4rem 0 1.3rem 0;
    border-top: 3px double {c['rule']};
    border-bottom: 1px solid {c['border']};
    margin-bottom: 1.5rem;
}}
.ceipa-hero-masthead {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {c['text_muted']};
    padding: 0.5rem 0;
    border-bottom: 1px solid {c['border_soft']};
    margin-bottom: 1rem;
}}
.ceipa-hero-masthead .edition {{
    color: {c['primary']};
    font-weight: 700;
    letter-spacing: 0.18em;
}}
.ceipa-hero h1 {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif !important;
    font-weight: 700 !important;
    font-size: 3rem !important;
    line-height: 0.98 !important;
    letter-spacing: -0.035em !important;
    color: {c['text']} !important;
    margin: 0.15rem 0 0.55rem 0 !important;
}}
.ceipa-hero .deck {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif;
    font-style: normal;
    font-weight: 400;
    font-size: 1.12rem;
    line-height: 1.38;
    color: {c['text_muted']};
    max-width: 780px;
    margin: 0 0 0.55rem 0;
}}
.ceipa-hero .byline {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.76rem;
    color: {c['text_soft']};
    padding-top: 0.5rem;
    border-top: 1px solid {c['border_soft']};
    margin-top: 0.7rem;
}}
.ceipa-hero .byline strong {{ color: {c['text']}; font-weight: 600; }}

/* Chips editoriales */
.ceipa-chip {{
    display: inline-block;
    padding: 0.1rem 0;
    margin-right: 1.1rem;
    color: {c['text_muted']};
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    background: transparent;
}}
.ceipa-chip.accent {{ color: {c['primary']}; }}
.ceipa-chip.slate  {{ color: {c['text_soft']}; }}

/* Bento como grid editorial sin cards */
.bento {{
    display: grid;
    gap: 0;
    margin-bottom: 1.5rem;
    border-top: 2px solid {c['rule']};
    border-bottom: 1px solid {c['border']};
}}
.bento-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.bento-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.bento-hero {{ grid-template-columns: 1.6fr 1fr 1fr 1fr; }}

.bento-card {{
    background: transparent;
    border-right: 1px solid {c['border']};
    padding: 1.05rem 1.2rem 0.9rem 1.2rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 110px;
}}
.bento-card:last-child {{ border-right: none; }}
.bento-card.accent {{ background: {c['primary_soft']}; }}
.bento-card-label {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 700;
    color: {c['text_muted']};
    margin: 0 0 0.5rem 0;
}}
.bento-card-value {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif;
    font-size: 2rem;
    font-weight: 600;
    letter-spacing: -0.025em;
    color: {c['text']};
    line-height: 1.0;
    margin: 0 0 0.3rem 0;
    font-variant-numeric: tabular-nums;
}}
.bento-card.hero .bento-card-value {{ font-size: 2.7rem; font-weight: 700; }}
.bento-card-unit {{
    font-family: 'IBM Plex Sans Condensed', 'Helvetica Neue', Arial, sans-serif;
    font-style: normal;
    font-size: 0.88rem;
    color: {c['text_muted']};
    font-weight: 400;
    margin-left: 0.3rem;
}}
.bento-card-delta {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.74rem;
    font-weight: 600;
    color: {c['text_muted']};
}}
.bento-card-delta.up   {{ color: {c['success']}; }}
.bento-card-delta.down {{ color: {c['danger']}; }}
.bento-card-spark {{ margin-top: 0.5rem; height: 30px; }}
</style>
"""


def _plotly_template(c: dict) -> str:
    template = go.layout.Template()
    template.layout = dict(
        font=dict(family="Inter Tight, sans-serif", color=c["text"], size=11.5),
        title=dict(font=dict(size=13, color=c["text"], family="Fraunces, serif"),
                   x=0.0, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(size=10, color=c["text_muted"],
                          family="JetBrains Mono, monospace"),
            linecolor=c["border"], showline=True,
            ticks="outside", ticklen=4, tickcolor=c["border"],
        ),
        yaxis=dict(
            showgrid=True, gridcolor=c["gridline"], zeroline=False,
            tickfont=dict(size=10, color=c["text_muted"],
                          family="JetBrains Mono, monospace"),
            linecolor="rgba(0,0,0,0)", showline=False,
            ticks="", ticklen=0,
        ),
        colorway=[
            c["primary"], c["accent"], c["text"], c["success"],
            c["danger"], c["text_soft"], c["text_muted"],
            "#6B4E2E", "#2F4858",
        ],
        legend=dict(
            font=dict(size=10, color=c["text_muted"],
                      family="Inter Tight, sans-serif"),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
        ),
        margin=dict(l=4, r=4, t=28, b=24),
        hoverlabel=dict(
            bgcolor=c["surface"], bordercolor=c["rule"],
            font=dict(family="JetBrains Mono, monospace", size=11, color=c["text"]),
        ),
    )
    pio.templates["ceipa"] = template
    pio.templates.default = "ceipa"
    return "ceipa"


# ============ API pública ============

def apply(st_module) -> dict:
    _plotly_template(PALETTE)
    st_module.markdown(_css(PALETTE), unsafe_allow_html=True)
    return PALETTE


def logo(st_module) -> None:
    """Logo tipográfico minimal — se renderiza al tope del sidebar."""
    st_module.sidebar.markdown(
        """
<div class="ceipa-logo">
  <div class="name">CEIPA</div>
  <div class="tagline">Observatorio · Inteligencia sectorial</div>
</div>
""",
        unsafe_allow_html=True,
    )


def theme_toggle(st_module) -> None:
    """Stub — mantenido por compatibilidad. El tema es único ahora."""
    return


def hero(st_module, eyebrow: str, title: str, subtitle: str, chips: list[str] | None = None,
         byline: str = "") -> None:
    import pandas as pd
    today = pd.Timestamp.today().strftime("%A, %d de %B de %Y").capitalize()
    chips_html = ""
    if chips:
        chips_html = " ".join([f'<span class="ceipa-chip">{c}</span>' for c in chips])
    byline_html = f'<div class="byline">{byline}</div>' if byline else ""
    st_module.markdown(
        f"""
<div class="ceipa-hero">
  <div class="ceipa-hero-masthead">
    <span>Observatorio CEIPA · Cámara Empresarial Industria Petrolera y Afines del Neuquén</span>
    <span class="edition">{today}</span>
  </div>
  <div style="margin-top:0.2rem;margin-bottom:0.3rem;">{chips_html}</div>
  <h1>{title}</h1>
  <div class="deck">{subtitle}</div>
  {byline_html}
</div>
""",
        unsafe_allow_html=True,
    )


def section_header(st_module, eyebrow: str, title: str, subtitle: str = "") -> None:
    sub_html = f'<div class="ceipa-section-subtitle">{subtitle}</div>' if subtitle else ""
    st_module.markdown(
        f"""
<div style="margin: 0.6rem 0 1.1rem 0;">
  <span class="ceipa-eyebrow">{eyebrow}</span>
  <div class="ceipa-section-title">{title}</div>
  {sub_html}
</div>
""",
        unsafe_allow_html=True,
    )


def chip(text: str, variant: str = "") -> str:
    cls = f"ceipa-chip {variant}".strip()
    return f'<span class="{cls}">{text}</span>'


def _spark_svg(values: Iterable[float], color: str, width: int = 160, height: int = 30) -> str:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    n = len(vals)
    pad = 2
    points = []
    for i, v in enumerate(vals):
        x = pad + (i / (n - 1)) * (width - 2 * pad)
        y = height - pad - ((v - mn) / rng) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")
    path = "M " + " L ".join(points)
    return f"""
<svg viewBox="0 0 {width} {height}" width="100%" height="100%" preserveAspectRatio="none">
  <path d="{path}" stroke="{color}" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


def stat_card(
    label: str, value: str, delta: str | None = None, delta_up: bool | None = None,
    unit: str = "", spark: Iterable[float] | None = None, variant: str = "",
    palette: dict | None = None,
) -> str:
    p = palette or PALETTE
    delta_html = ""
    if delta:
        cls = ""
        if delta_up is True:  cls = "up"
        if delta_up is False: cls = "down"
        arrow = "▲" if delta_up else ("▼" if delta_up is False else "→")
        delta_html = f'<div class="bento-card-delta {cls}">{arrow} {delta}</div>'
    spark_html = ""
    if spark:
        spark_html = f'<div class="bento-card-spark">{_spark_svg(spark, p["primary"])}</div>'
    unit_html = f'<span class="bento-card-unit">{unit}</span>' if unit else ""
    extra_cls = f" {variant}" if variant else ""
    return f"""
<div class="bento-card{extra_cls}">
  <div>
    <div class="bento-card-label">{label}</div>
    <div class="bento-card-value">{value}{unit_html}</div>
    {delta_html}
  </div>
  {spark_html}
</div>
"""


def bento_grid(st_module, cards_html: list[str], variant: str = "4") -> None:
    cls = f"bento bento-{variant}"
    st_module.markdown(f'<div class="{cls}">{"".join(cards_html)}</div>',
                       unsafe_allow_html=True)
