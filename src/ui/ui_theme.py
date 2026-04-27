"""Zentrales Styling-Modul für Mercator (Requirement 5.1)."""

from __future__ import annotations

import streamlit as st

THEME_COLORS: dict[str, str] = {
    "navy_950": "#0F172A",
    "navy_900": "#0F172A",
    "navy_800": "#1E293B",
    "blue_700": "#1D4ED8",
    "blue_600": "#2563EB",
    "blue_500": "#2563EB",
    "blue_300": "#93C5FD",
    "ice_50": "#F8FAFC",
    "ice_100": "#F1F5F9",
    "ice_200": "#E2E8F0",
    "steel_300": "#CBD5E1",
    "steel_500": "#64748B",
    "text_strong": "#0F172A",
    "text": "#0F172A",
    "text_muted": "#64748B",
    "success": "#15803D",
    "success_bg": "#DCFCE7",
    "danger": "#B91C1C",
    "danger_bg": "#FEE2E2",
    "warning": "#B45309",
    "warning_bg": "#FFEDD5",
    "info": "#0369A1",
    "info_bg": "#E0F2FE",
}

CHART_PALETTE: dict[str, object] = {
    "positive": THEME_COLORS["success"],
    "negative": THEME_COLORS["danger"],
    "neutral": THEME_COLORS["blue_500"],
    "navy": THEME_COLORS["blue_700"],
    "steel": THEME_COLORS["blue_300"],
    "categorical": [
        "#2563EB",
        "#0891B2",
        "#0F766E",
        "#65A30D",
        "#CA8A04",
        "#EA580C",
        "#7C3AED",
        "#475569",
    ],
}


def apply_ui_theme() -> None:
    """Wendet das globale CSS-Theme auf die Streamlit-App an."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --mercator-navy-950: #0F172A;
            --mercator-navy-900: #0F172A;
            --mercator-navy-800: #1E293B;

            --mercator-blue-700: #1D4ED8;
            --mercator-blue-600: #2563EB;
            --mercator-blue-500: #2563EB;
            --mercator-blue-300: #93C5FD;

            --mercator-ice-50: #F8FAFC;
            --mercator-ice-100: #F1F5F9;
            --mercator-ice-200: #E2E8F0;
            --mercator-steel-300: #CBD5E1;
            --mercator-steel-500: #64748B;

            --mercator-text-strong: #0F172A;
            --mercator-text: #0F172A;
            --mercator-text-muted: #64748B;

            --mercator-success: #15803D;
            --mercator-success-bg: #DCFCE7;
            --mercator-danger: #B91C1C;
            --mercator-danger-bg: #FEE2E2;
            --mercator-warning: #B45309;
            --mercator-warning-bg: #FFEDD5;
            --mercator-info: #0369A1;
            --mercator-info-bg: #E0F2FE;

            --mercator-focus-ring: rgba(37, 99, 235, 0.28);
            --mercator-success-ring: rgba(21, 128, 61, 0.24);

            --mercator-border: var(--mercator-steel-300);
            --mercator-border-strong: #94A3B8;
            --mercator-surface: #FFFFFF;
            --mercator-surface-muted: var(--mercator-ice-100);
            --mercator-surface-soft: var(--mercator-ice-50);
            --mercator-radius-sm: 0.55rem;
            --mercator-radius-md: 0.8rem;
            --mercator-radius-lg: 1rem;
            --mercator-shadow-subtle: 0 2px 10px rgba(15, 23, 42, 0.06);
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
            border: 0 !important;
            box-shadow: none !important;
            background: transparent !important;
            object-fit: cover;
        }

        /* Segmented Control / Navigation */
        [data-testid="stSegmentedControl"] {
            background: transparent;
            border: 0;
            border-radius: 0.95rem;
            padding: 0;
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
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.22);
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
            text-decoration-color: rgba(29, 78, 216, 0.35);
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
