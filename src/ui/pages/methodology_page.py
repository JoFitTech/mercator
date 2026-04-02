"""Methodikseite mit Datenquelle, Datenfluss und MVP-Grenzen."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Rendert die methodische Einordnung für das Uni-Projekt."""
    st.title("Methodik")
    st.write(
        "Diese Anwendung liest einen öffentlich verfügbaren Datensatz ein, verarbeitet ihn mit Pandas, speichert Roh- und Zieldaten in MongoDB und MySQL und stellt die Ergebnisse anschließend in einer interaktiven Streamlit-Oberfläche dar."
    )
    st.markdown(
        """
- **Datenquelle:** Financial Modeling Prep (nur zwei MVP-Endpunkte).
- **Datenfluss:** FMP Feed → Normalisierung/Gate → MongoDB (roh) + MySQL (bereinigt) → Streamlit.
- **Zwei Datenbanken:** MongoDB für unveränderte/semi-strukturierte Rohdaten, MySQL für auswertbare Tabellen.
- **MongoDB-Nutzung:** `insider_trades_raw` und `companies` als Roh-/Profilspeicher.
- **MySQL-Nutzung:** `insider_trades` und `companies` für Dashboard, Explorer und Detailansicht.
- **Verwendete FMP-Endpunkte:**
  - `GET /insider-trading/latest?page={page}&limit={limit}`
  - `GET /profile?symbol={SYMBOL}`
- **MVP-Grenzen:** kein Trading, keine Broker-Anbindung, kein Login-/Rollenmodell, keine weiteren FMP-Endpunkte.
        """
    )
