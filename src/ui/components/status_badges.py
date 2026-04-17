"""Zentralisierte Status-Badges für Mercator (Spec: Status nie nur über Farbe)."""

from __future__ import annotations

import streamlit as st

def status_badge(label: str, status_type: str = "INFO", help: str | None = None) -> None:
    """Rendert ein hochwertiges Badge (Apple-inspired)."""
    
    colors = {
        "PASS": {"bg": "#E8F5E9", "text": "#2E7D32", "border": "#A5D6A7"},
        "SUCCESS": {"bg": "#E8F5E9", "text": "#2E7D32", "border": "#A5D6A7"},
        "PENDING": {"bg": "#FFF8E1", "text": "#F9A825", "border": "#FFE082"},
        "WARNING": {"bg": "#FFF8E1", "text": "#F9A825", "border": "#FFE082"},
        "FAIL": {"bg": "#FFEBEE", "text": "#C62828", "border": "#EF9A9A"},
        "ERROR": {"bg": "#FFEBEE", "text": "#C62828", "border": "#EF9A9A"},
        "INFO": {"bg": "#E3F2FD", "text": "#1565C0", "border": "#90CAF9"},
        "NEUTRAL": {"bg": "#F5F5F5", "text": "#616161", "border": "#E0E0E0"},
    }
    
    config = colors.get(status_type.upper(), colors["INFO"])
    
    st.markdown(
        f'<span class="mercator-badge" style="'
        f'background-color: {config["bg"]}; '
        f'color: {config["text"]}; '
        f'border: 1px solid {config["border"]}; '
        f'padding: 2px 10px; border-radius: 6px; font-weight: 600; font-size: 0.7rem; '
        f'letter-spacing: 0.03em; margin-right: 4px;'
        f'">{label}</span>',
        unsafe_allow_html=True
    )

def score_class_badge(score_class: str) -> None:
    """Spezialisiertes Badge für die Score-Klasse (A, B, C, D, F)."""
    class_map = {
        "A": "PASS",
        "B": "PASS",
        "C": "HOLD",
        "D": "WARNING",
        "F": "FAIL"
    }
    status_type = class_map.get(score_class.upper(), "INFO")
    status_badge(f"CLASS {score_class.upper()}", status_type=status_type)

def gate_badge(status: str) -> None:
    """Badge für den Gate-Status."""
    status_badge(status, status_type=status)

def validation_badge(status: str) -> None:
    """Badge für den Validierungsstatus."""
    status_badge(status, status_type=status)


def trade_republic_universe_badge(status: str) -> None:
    """Badge für Trade-Republic-Universumsstatus."""
    normalized = (status or "UNKNOWN").upper()
    label_map = {
        "IN_UNIVERSE": "Im Universum",
        "NOT_IN_UNIVERSE": "Nicht im Universum",
        "UNKNOWN": "Unbekannt",
    }
    style_map = {
        "IN_UNIVERSE": "SUCCESS",
        "NOT_IN_UNIVERSE": "WARNING",
        "UNKNOWN": "INFO",
    }
    status_badge(label_map.get(normalized, "Unbekannt"), style_map.get(normalized, "INFO"))
