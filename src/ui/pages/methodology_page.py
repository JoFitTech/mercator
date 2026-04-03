"""Methodikseite mit Datenquelle, Datenfluss und MVP-Grenzen."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Rendert die methodische Einordnung für das Uni-Projekt."""
    st.title("FinanzPort Academic")
    st.markdown("### Methodik & Architektur")
    st.write(
        "Diese Anwendung liest einen öffentlich verfügbaren Datensatz ein, verarbeitet ihn mit Pandas, "
        "speichert Roh- und Zieldaten in MongoDB und MySQL und stellt die Ergebnisse anschließend "
        "in einer interaktiven Streamlit-Oberfläche dar."
    )

    st.markdown("---")
    st.subheader("Architektur-Übersicht")
    st.markdown(
        """
        - **Datenquelle:** Financial Modeling Prep (FMP) API.
        - **Datenfluss:** FMP Feed → Normalisierung → Deduplizierung → Gate-Prüfung → Persistenz → UI.
        - **Zwei-Datenbank-Strategie:**
            - **MongoDB:** Speicherung der semi-strukturierten Rohdaten (`insider_trades_raw`) und Profile (`companies`).
            - **MySQL:** Relationale Speicherung bereinigter und strukturierter Daten für schnelles Reporting und Joins.
        """
    )

    st.markdown("---")
    st.subheader("Verarbeitungsschritte")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Normalisierung & Reinigung**")
        st.caption("Typkonvertierung (Dates, Floats), Feldmapping und Bereinigung technischer Fehler.")
        st.markdown("**2. Deduplizierung**")
        st.caption("Erzeugung eines technischen SHA256-Hashes (`dedupe_key`) über Kernattribute zur Vermeidung von Dubletten.")
    with col2:
        st.markdown("**3. Gate-Prüfung**")
        st.caption("Lokale Evaluierung nach vordefinierten Regeln (z.B. Mindestwert, Transaktionstyp) zur Relevanzprüfung.")
        st.markdown("**4. Profil-Anreicherung**")
        st.caption("Automatisches Nachladen von Unternehmensmetadaten für Datensätze mit `Gate-PASS` (inkl. 7-Tage Caching).")

    st.markdown("---")
    st.subheader("Verwendete FMP-Endpunkte (MVP-Scope)")
    st.code("GET /insider-trading/latest?page={page}&limit={limit}\nGET /profile?symbol={SYMBOL}", language="text")

    st.markdown("---")
    st.subheader("Einschränkungen (MVP-Grenzen)")
    st.info(
        "Dieses Projekt dient akademischen Zwecken. Es enthält kein Echtzeit-Trading, "
        "keine Broker-Anbindung, kein Login-/Rollenmodell und keine Mail-Automation."
    )
