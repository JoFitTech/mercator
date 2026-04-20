"""Zentrales Styling-Modul für Mercator (Requirement 5.1)."""

from __future__ import annotations

import streamlit as st

THEME_COLORS: dict[str, str] = {
    "navy_950": "#000002",
    "navy_900": "#031126",
    "navy_800": "#0F1A26",
    "blue_700": "#2B4D68",
    "blue_600": "#355D7E",
    "blue_500": "#4A7898",
    "blue_300": "#85A9B4",
    "ice_50": "#F4F7F8",
    "ice_100": "#E9EFF1",
    "ice_200": "#D6DFE2",
    "steel_300": "#C1CCD1",
    "steel_500": "#6B777F",
    "text_strong": "#0F1A26",
    "text": "#28323D",
    "text_muted": "#56646E",
    "success": "#2F8F7A",
    "success_bg": "#E7F5F1",
    "danger": "#A54A4A",
    "danger_bg": "#F8EBEB",
    "warning": "#A5823F",
    "warning_bg": "#F9F3E5",
    "info": "#355D7E",
    "info_bg": "#EAF1F6",
}

CHART_PALETTE: dict[str, object] = {
    "positive": THEME_COLORS["success"],
    "negative": THEME_COLORS["danger"],
    "neutral": THEME_COLORS["blue_500"],
    "navy": THEME_COLORS["blue_700"],
    "steel": THEME_COLORS["blue_300"],
    "categorical": [
        THEME_COLORS["blue_500"],
        "#85A9B4",
        "#6E97AB",
        "#9EB9C2",
        "#B7CBD1",
        "#CAD9DE",
    ],
}


def apply_ui_theme() -> None:
    """Wendet das globale CSS-Theme auf die Streamlit-App an."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --mercator-navy-950: #000002;
            --mercator-navy-900: #031126;
            --mercator-navy-800: #0F1A26;

            --mercator-blue-700: #2B4D68;
            --mercator-blue-600: #355D7E;
            --mercator-blue-500: #4A7898;
            --mercator-blue-300: #85A9B4;

            --mercator-ice-50: #F4F7F8;
            --mercator-ice-100: #E9EFF1;
            --mercator-ice-200: #D6DFE2;
            --mercator-steel-300: #C1CCD1;
            --mercator-steel-500: #6B777F;

            --mercator-text-strong: #0F1A26;
            --mercator-text: #28323D;
            --mercator-text-muted: #56646E;

            --mercator-success: #2F8F7A;
            --mercator-success-bg: #E7F5F1;
            --mercator-danger: #A54A4A;
            --mercator-danger-bg: #F8EBEB;
            --mercator-warning: #A5823F;
            --mercator-warning-bg: #F9F3E5;
            --mercator-info: #355D7E;
            --mercator-info-bg: #EAF1F6;

            --mercator-focus-ring: rgba(53, 93, 126, 0.32);
            --mercator-success-ring: rgba(47, 143, 122, 0.24);

            --mercator-border: var(--mercator-steel-300);
            --mercator-border-strong: #A8B5BC;
            --mercator-surface: #FFFFFF;
            --mercator-surface-muted: var(--mercator-ice-100);
            --mercator-surface-soft: var(--mercator-ice-50);
            --mercator-radius-sm: 0.55rem;
            --mercator-radius-md: 0.8rem;
            --mercator-radius-lg: 1rem;
            --mercator-shadow-subtle: 0 2px 10px rgba(3, 17, 38, 0.06);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--mercator-text);
            background: var(--mercator-surface-soft);
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: var(--mercator-ice-50);
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        /* Typografie */
        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            color: var(--mercator-text-strong) !important;
        }

        p, li, label, [data-testid="stCaptionContainer"] {
            color: var(--mercator-text);
        }

        .text-muted { color: var(--mercator-text-muted); }
        .text-success { color: var(--mercator-success); }
        .text-danger { color: var(--mercator-danger); }
        .text-warning { color: var(--mercator-warning); }

        /* App-Chrome */
        [data-testid="stSidebar"] {
            background-color: var(--mercator-ice-100);
            border-right: 1px solid var(--mercator-border);
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] {
            background: var(--mercator-surface);
            border: 1px solid var(--mercator-border);
            border-radius: var(--mercator-radius-md);
            margin-bottom: 0.75rem;
            overflow: hidden;
            box-shadow: none;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"]:hover {
            border-color: var(--mercator-blue-300) !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"] summary:focus-visible {
            outline: 2px solid var(--mercator-blue-600) !important;
            outline-offset: 2px !important;
            box-shadow: 0 0 0 3px var(--mercator-focus-ring) !important;
        }

        [data-testid="stSidebar"] h3 {
            color: var(--mercator-navy-900) !important;
            letter-spacing: 0.01em !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.mercator-topbar-eyebrow) {
            background: linear-gradient(180deg, #FFFFFF 0%, var(--mercator-ice-50) 100%);
            border: 1px solid var(--mercator-border) !important;
            border-radius: var(--mercator-radius-lg);
            box-shadow: var(--mercator-shadow-subtle);
        }

        .mercator-topbar-eyebrow {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--mercator-text-muted);
            margin-bottom: 0.2rem;
        }

        .mercator-topbar-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--mercator-navy-900);
            line-height: 1.2;
        }

        .mercator-topbar-brand {
            min-height: 52px;
            justify-content: center;
        }

        .mercator-topbar-logo {
            border: 1px solid var(--mercator-border);
            box-shadow: 0 2px 8px rgba(3, 17, 38, 0.14);
            background: #FFFFFF;
            object-fit: cover;
        }

        /* Segmented Control / Navigation */
        [data-testid="stSegmentedControl"] {
            background: #FFFFFF;
            border: 1px solid var(--mercator-border);
            border-radius: 0.95rem;
            padding: 0.22rem;
        }

        [data-testid="stSegmentedControl"] [role="radiogroup"] { gap: 0.35rem; }
        [data-testid="stSegmentedControl"] [role="radio"] {
            border-radius: 0.72rem;
            color: var(--mercator-text);
            border: 1px solid transparent;
            padding: 0.3rem 0.95rem !important;
            font-weight: 600;
            transition: all 0.18s ease;
        }

        [data-testid="stSegmentedControl"] [role="radio"]:hover {
            background: var(--mercator-ice-100) !important;
            border-color: var(--mercator-blue-300) !important;
        }

        [data-testid="stSegmentedControl"] [aria-checked="true"] {
            background: var(--mercator-blue-600) !important;
            color: #FFFFFF !important;
            border-color: var(--mercator-blue-700) !important;
            box-shadow: 0 2px 8px rgba(53, 93, 126, 0.22);
        }

        /* Streamlit Tabs: aktive/hover Farben erzwingen (kein Default-Rot) */
        [data-baseweb="tab-list"] {
            border-bottom-color: var(--mercator-border) !important;
        }

        [data-baseweb="tab"] {
            color: var(--mercator-text) !important;
            border-color: transparent !important;
        }

        [data-baseweb="tab"]:hover {
            color: var(--mercator-blue-700) !important;
            background: var(--mercator-ice-100) !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            color: var(--mercator-blue-700) !important;
            border-bottom-color: var(--mercator-blue-600) !important;
        }

        /* Karten / Container / Tabellenhülle */
        [data-testid="stMetric"] {
            background-color: var(--mercator-surface);
            border: 1px solid var(--mercator-border);
            padding: 1rem;
            border-radius: var(--mercator-radius-md);
            box-shadow: none;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        [data-testid="stMetric"]:hover {
            border-color: var(--mercator-steel-500);
            box-shadow: var(--mercator-shadow-subtle);
        }

        [data-testid="stMetricLabel"] {
            color: var(--mercator-text-muted) !important;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--mercator-text-strong) !important;
            letter-spacing: -0.015em;
        }

        [data-testid="stMetricDelta"] svg {
            stroke: var(--mercator-text-muted) !important;
        }

        .stDataFrame {
            border: 1px solid var(--mercator-border);
            border-radius: var(--mercator-radius-md);
            overflow: hidden;
            background: var(--mercator-surface);
        }

        /* Buttons */
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="baseButton-secondary"] {
            border-radius: var(--mercator-radius-sm);
            border: 1px solid var(--mercator-border-strong);
            background: var(--mercator-surface);
            color: var(--mercator-text-strong);
            font-weight: 600;
            transition: all 0.2s ease;
        }

        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="baseButton-secondary"]:hover {
            border-color: var(--mercator-blue-300);
            color: var(--mercator-navy-900);
            background: #FFFFFF;
        }

        [data-testid="baseButton-primary"] {
            background: var(--mercator-blue-600) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--mercator-blue-700) !important;
        }

        [data-testid="baseButton-primary"]:hover {
            background: var(--mercator-blue-700) !important;
            border-color: var(--mercator-navy-800) !important;
        }

        /* Inputs / Selects / Date */
        [data-baseweb="input"] input,
        [data-baseweb="base-input"] input,
        [data-baseweb="select"] > div,
        [data-testid="stDateInputField"] {
            background: #FFFFFF !important;
            border: 1px solid var(--mercator-border) !important;
            color: var(--mercator-text-strong) !important;
            border-radius: var(--mercator-radius-sm) !important;
        }

        [data-baseweb="input"] input:hover,
        [data-baseweb="base-input"] input:hover,
        [data-baseweb="select"] > div:hover,
        [data-testid="stDateInputField"]:hover {
            border-color: var(--mercator-steel-500) !important;
        }

        /* Alerts / Statusflächen */
        [data-testid="stAlert"] {
            border-radius: var(--mercator-radius-md);
            border: 1px solid var(--mercator-border);
        }

        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
            color: var(--mercator-text-strong);
        }

        /* Links */
        a {
            color: var(--mercator-blue-700);
            text-decoration-color: rgba(43, 77, 104, 0.35);
        }

        a:hover {
            color: var(--mercator-navy-800);
        }

        /* Badge Basisklasse */
        .mercator-badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 999px;
            text-transform: uppercase;
            letter-spacing: 0.025em;
            border: 1px solid var(--mercator-border);
            background: var(--mercator-ice-100);
            color: var(--mercator-navy-900);
        }

        /* Fokus sichtbar + konsistent */
        button:focus-visible,
        [role="button"]:focus-visible,
        [role="radio"]:focus-visible,
        a:focus-visible,
        input:focus-visible,
        select:focus-visible,
        textarea:focus-visible {
            outline: 3px solid var(--mercator-blue-600) !important;
            outline-offset: 2px !important;
            box-shadow: 0 0 0 3px var(--mercator-focus-ring) !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_state_box(message: str, type: str = "info") -> None:
    """Rendert eine Status-Box in der UI."""
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
