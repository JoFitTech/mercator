"""Methodikseite mit Datenquelle, Datenfluss und MVP-Grenzen."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Rendert die methodische Einordnung für das Uni-Projekt."""
    st.title("Methodik & Architektur")
    st.caption("Technische Dokumentation der Pipeline, Datenmodelle und Verarbeitungsregeln.")

    st.markdown("---")
    
    with st.container(border=True):
        st.subheader("Übersicht")
        st.write(
            "Mercator ist eine analytische Plattform zur Identifikation relevanter Insidertrades. "
            "Die Anwendung folgt einer strikten 7-Stufen-Pipeline von der Rohdatenerfassung bis zur visuellen Analyse."
        )

    st.markdown("### 1. Datenpipeline")
    cols = st.columns(4)
    with cols[0]:
        st.markdown("**Ingestion**")
        st.caption("FMP API Feed")
    with cols[1]:
        st.markdown("**Validation**")
        st.caption("Type & Integrity")
    with cols[2]:
        st.markdown("**Enrichment**")
        st.caption("Company Profiles")
    with cols[3]:
        st.markdown("**Persistence**")
        st.caption("Mongo & MySQL")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Speicherstrategie")
        st.markdown(
            """
            - **Raw Layer (MongoDB):** Unveränderte JSON-Antworten der API. Dient als Audit-Log und Quelle für Re-Imports.
            - **Clean Layer (MySQL):** Strukturiert, normalisiert und indiziert. Basis für alle UI-Abfragen und Aggregationen.
            """
        )
    with col2:
        st.subheader("Verarbeitungsregeln")
        st.markdown(
            """
            - **Deduplizierung:** Hash-basierter Abgleich über Ticker, Insider, Datum und Menge.
            - **Gate-Prüfung:** Automatisches Aussortieren von Rauschen (z.B. Kleinstbeträge < 100k, automatische Zuteilungen).
            """
        )

    st.markdown("---")
    st.subheader("Scoring-Modell")
    st.write("Jeder Trade wird anhand von Marktvolatilität, Insider-Historie und Trade-Volumen bewertet (Klassen A-F).")
    
    st.markdown("### Technische Endpunkte")
    st.code(
        "GET /insider-trading/latest\n"
        "GET /profile-cik?cik={CIK}\n"
        "GET /profile?symbol={SYMBOL}",
        language="text",
    )

    st.markdown("---")
    st.info(
        "🎓 Projekt im Rahmen des Moduls Datenbanken 2. Fokus auf hybride Datenhaltung und Performance."
    )
