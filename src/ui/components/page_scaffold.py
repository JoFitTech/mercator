"""Konsistente Seitenkopf- und State-Komponenten für Mercator."""

from __future__ import annotations

import streamlit as st


def render_page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_empty_state(message: str) -> None:
    st.info(message)


def render_warning_state(message: str) -> None:
    st.warning(message)


def render_error_state(message: str) -> None:
    st.error(message)
