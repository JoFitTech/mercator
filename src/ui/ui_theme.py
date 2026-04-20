"""Zentrales Styling-Modul für Mercator (Requirement 5.1)."""

from __future__ import annotations

import streamlit as st

THEME_COLORS: dict[str, str] = {
    "navy_950": "#071425",
    "navy_900": "#0B1F3A",
    "navy_800": "#123153",
    "blue_700": "#0D63D6",
    "blue_600": "#147BFF",
    "blue_500": "#2C98FF",
    "blue_300": "#8FD0FF",
    "ice_50": "#F7FAFD",
    "ice_100": "#EEF3F8",
    "ice_200": "#E3EAF2",
    "steel_300": "#C9D4E2",
    "steel_500": "#8FA2B8",
    "text_strong": "#0F2037",
    "text": "#1A2E49",
    "text_muted": "#5D728C",
    "success": "#61D96B",
    "success_bg": "#EAF9ED",
    "danger": "#D94E4E",
    "danger_bg": "#FCECEC",
    "warning": "#D9A441",
    "warning_bg": "#FFF6E5",
    "info": "#147BFF",
    "info_bg": "#EAF4FF",
}

CHART_PALETTE: dict[str, object] = {
    "positive": THEME_COLORS["success"],
    "negative": THEME_COLORS["danger"],
    "neutral": THEME_COLORS["blue_600"],
    "navy": THEME_COLORS["navy_800"],
    "steel": THEME_COLORS["steel_500"],
    "categorical": [
        THEME_COLORS["blue_600"],
        THEME_COLORS["navy_800"],
        THEME_COLORS["blue_500"],
        THEME_COLORS["steel_500"],
        "#4B6380",
        "#6A86A7",
    ],
}


def apply_ui_theme() -> None:
    """Wendet das globale CSS-Theme auf die Streamlit-App an."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --mercator-navy-950: #071425;
            --mercator-navy-900: #0B1F3A;
            --mercator-navy-800: #123153;

            --mercator-blue-700: #0D63D6;
            --mercator-blue-600: #147BFF;
            --mercator-blue-500: #2C98FF;
            --mercator-blue-300: #8FD0FF;

            --mercator-ice-50: #F7FAFD;
            --mercator-ice-100: #EEF3F8;
            --mercator-ice-200: #E3EAF2;
            --mercator-steel-300: #C9D4E2;
            --mercator-steel-500: #8FA2B8;

            --mercator-text-strong: #0F2037;
            --mercator-text: #1A2E49;
            --mercator-text-muted: #5D728C;

            --mercator-success: #61D96B;
            --mercator-success-bg: #EAF9ED;
            --mercator-danger: #D94E4E;
            --mercator-danger-bg: #FCECEC;
            --mercator-warning: #D9A441;
            --mercator-warning-bg: #FFF6E5;
            --mercator-info: #147BFF;
            --mercator-info-bg: #EAF4FF;

            --mercator-focus-ring: rgba(20, 123, 255, 0.30);
            --mercator-success-ring: rgba(97, 217, 107, 0.22);

            --mercator-border: var(--mercator-steel-300);
            --mercator-border-strong: #B3C2D4;
            --mercator-surface: #FFFFFF;
            --mercator-surface-muted: var(--mercator-ice-100);
            --mercator-surface-soft: var(--mercator-ice-50);
            --mercator-radius-sm: 0.55rem;
            --mercator-radius-md: 0.8rem;
            --mercator-radius-lg: 1rem;
            --mercator-shadow-subtle: 0 2px 8px rgba(7, 20, 37, 0.04);
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

        /* Segmented Control / Navigation */
        [data-testid="stSegmentedControl"] {
            background: var(--mercator-ice-100);
            border: 1px solid var(--mercator-border);
            border-radius: 0.92rem;
            padding: 0.3rem;
        }

        [data-testid="stSegmentedControl"] [role="radiogroup"] { gap: 0.35rem; }
        [data-testid="stSegmentedControl"] [role="radio"] {
            border-radius: 0.7rem;
            color: var(--mercator-text);
            border: 1px solid transparent;
        }

        [data-testid="stSegmentedControl"] [aria-checked="true"] {
            background: var(--mercator-blue-600) !important;
            color: #FFFFFF !important;
            border-color: var(--mercator-blue-700) !important;
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
            text-decoration-color: rgba(13, 99, 214, 0.35);
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
