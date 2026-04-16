"""Zentralisierte Status-Badges für Mercator (Spec: Status nie nur über Farbe)."""

from __future__ import annotations

import streamlit as st

def status_badge(label: str, status_type: str = "INFO", help: str | None = None) -> None:
    """Rendert ein farbiges Badge mit Text."""
    
    # Farben basierend auf Mercator-Semantik
    colors = {
        "PASS": {"bg": "rgba(40, 167, 69, 0.1)", "border": "rgba(40, 167, 69, 0.3)", "text": "#28a745"},
        "SUCCESS": {"bg": "rgba(40, 167, 69, 0.1)", "border": "rgba(40, 167, 69, 0.3)", "text": "#28a745"},
        "HOLD": {"bg": "rgba(255, 193, 7, 0.1)", "border": "rgba(255, 193, 7, 0.3)", "text": "#ffc107"},
        "PENDING": {"bg": "rgba(255, 193, 7, 0.1)", "border": "rgba(255, 193, 7, 0.3)", "text": "#ffc107"},
        "WARNING": {"bg": "rgba(255, 193, 7, 0.1)", "border": "rgba(255, 193, 7, 0.3)", "text": "#ffc107"},
        "FAIL": {"bg": "rgba(220, 53, 69, 0.1)", "border": "rgba(220, 53, 69, 0.3)", "text": "#dc3545"},
        "ERROR": {"bg": "rgba(220, 53, 69, 0.1)", "border": "rgba(220, 53, 69, 0.3)", "text": "#dc3545"},
        "INVALID": {"bg": "rgba(220, 53, 69, 0.1)", "border": "rgba(220, 53, 69, 0.3)", "text": "#dc3545"},
        "INFO": {"bg": "rgba(23, 162, 184, 0.1)", "border": "rgba(23, 162, 184, 0.3)", "text": "#17a2b8"},
        "VALID": {"bg": "rgba(40, 167, 69, 0.1)", "border": "rgba(40, 167, 69, 0.3)", "text": "#28a745"},
    }
    
    config = colors.get(status_type.upper(), colors["INFO"])
    
    badge_html = (
        f'<span title="{help or ""}" style="'
        f'background-color: {config["bg"]}; '
        f'border: 1px solid {config["border"]}; '
        f'color: {config["text"]}; '
        f'padding: 2px 8px; '
        f'border-radius: 4px; '
        f'font-size: 0.75rem; '
        f'font-weight: 600; '
        f'text-transform: uppercase; '
        f'letter-spacing: 0.05em; '
        f'display: inline-block;'
        f'">{label}</span>'
    )
    
    st.markdown(badge_html, unsafe_allow_html=True)

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
