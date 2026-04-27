"""Zentralisierte Status-Badges fuer Mercator (Status nie nur ueber Farbe)."""

from __future__ import annotations

import streamlit as st


def status_to_label(status: str) -> str:
    normalized = str(status or "").strip().upper()
    labels = {
        "PASS": "PASS",
        "PRE_GATE_FAIL": "PRE GATE FAIL",
        "INVALID": "INVALID",
        "PRICE_INVALID": "PRICE INVALID",
        "ACTIONABLE_BUY": "ACTIONABLE BUY",
        "BUY_CANDIDATE": "BUY CANDIDATE",
        "WATCHLIST": "WATCHLIST",
        "SELL_WARNING": "SELL WARNING",
    }
    return labels.get(normalized, normalized or "UNBEKANNT")


def status_to_semantic_color(status: str) -> str:
    normalized = str(status or "").strip().upper()
    if normalized in {"PASS", "ACTIONABLE_BUY", "BUY_CANDIDATE"}:
        return "success"
    if normalized in {"WATCHLIST", "PENDING", "MANUAL_REVIEW"}:
        return "warning"
    if normalized in {"INVALID", "PRICE_INVALID", "PRE_GATE_FAIL", "FAIL", "ERROR", "SELL_WARNING"}:
        return "error"
    return "info"


def render_status_badge(status: str, kind: str = "generic") -> None:
    _ = kind  # fuer kuenftige badge-Varianten reserviert
    label = status_to_label(status)
    semantic = status_to_semantic_color(status)
    status_badge(label, status_type=semantic)


def status_badge(label: str, status_type: str = "INFO", help: str | None = None) -> None:
    """Rendert ein Badge im Mercator-Statusschema."""

    colors = {
        "PASS": {"bg": "var(--mercator-success-bg)", "text": "var(--mercator-success)", "border": "var(--mercator-success)"},
        "SUCCESS": {"bg": "var(--mercator-success-bg)", "text": "var(--mercator-success)", "border": "var(--mercator-success)"},
        "PENDING": {"bg": "var(--mercator-warning-bg)", "text": "var(--mercator-warning)", "border": "var(--mercator-warning)"},
        "WARNING": {"bg": "var(--mercator-warning-bg)", "text": "var(--mercator-warning)", "border": "var(--mercator-warning)"},
        "FAIL": {"bg": "var(--mercator-danger-bg)", "text": "var(--mercator-danger)", "border": "var(--mercator-danger)"},
        "ERROR": {"bg": "var(--mercator-danger-bg)", "text": "var(--mercator-danger)", "border": "var(--mercator-danger)"},
        "INFO": {"bg": "var(--mercator-info-bg)", "text": "var(--mercator-blue-700)", "border": "var(--mercator-blue-300)"},
        "NEUTRAL": {"bg": "var(--mercator-ice-100)", "text": "var(--mercator-text-muted)", "border": "var(--mercator-border)"},
    }

    normalized_type = str(status_type or "INFO").upper()
    alias_map = {"SUCCESS": "PASS", "WARNING": "PENDING", "ERROR": "FAIL"}
    config = colors.get(alias_map.get(normalized_type, normalized_type), colors["INFO"])
    title_attr = f' title="{help}"' if help else ""

    st.markdown(
        f'<span class="mercator-badge"{title_attr} style="'
        f'background-color: {config["bg"]}; '
        f'color: {config["text"]}; '
        f'border: 1px solid {config["border"]}; '
        f'padding: 2px 10px; border-radius: 6px; font-weight: 600; font-size: 0.7rem; '
        f'letter-spacing: 0.03em; margin-right: 4px; text-transform: uppercase;'
        f'">{label}</span>',
        unsafe_allow_html=True,
    )


def score_class_badge(score_class: str) -> None:
    """Spezialisiertes Badge für die Score-Klasse (A, B, C, D, F)."""
    class_map = {
        "A": "PASS",
        "B": "PASS",
        "C": "PENDING",
        "D": "WARNING",
        "F": "FAIL",
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
