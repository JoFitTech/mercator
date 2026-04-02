"""Methodikseite zur Erklärung von Datenfluss und Architektur."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Rendert die Methodikbeschreibung für Demo und Uni-Präsentation."""
    st.title("Methodik und Datenfluss")
    st.write(
        "Diese Anwendung liest einen öffentlich verfügbaren Datensatz ein, verarbeitet ihn mit Pandas, speichert Roh- und Zieldaten in MongoDB und MySQL und stellt die Ergebnisse anschließend in einer interaktiven Streamlit-Oberfläche dar."
    )
    st.info("Die aktuelle Struktur ist bewusst als wartbares Grundgerüst für die weitere Umsetzung des Uni-Projekts angelegt.")
