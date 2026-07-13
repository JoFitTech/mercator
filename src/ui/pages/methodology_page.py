"""Methodikseite mit Datenquelle, Datenfluss und MVP-Grenzen."""

from __future__ import annotations

import streamlit as st


MANUAL_TRADING_BOUNDARY_TEXT = (
    "Mercator hat keine Broker-Anbindung, platziert keine Order und führt kein Live-Trading aus. "
    "Alle endgültigen Anlage- und Handelsentscheidungen werden manuell außerhalb von Mercator getroffen."
)


def render_methodology_page() -> None:
    """Explain the stock-analysis pipeline and its explicit system boundary."""

    st.title("Methodik & Architektur der Aktienanalyse")
    st.caption("Nachvollziehbare Pipeline von Rohdaten bis zur transparenten Preference-Rangfolge.")

    st.markdown("### 1) Watchlist und Datenimport")
    st.markdown(
        """
        - Die manuelle Watchlist bestimmt die analysierten Symbole.
        - Profil-, Kurs-, Finanz- und Bewertungsantworten werden zuerst unverändert in MongoDB gespeichert.
        - Normalisierte Analysedaten, Features, Prognosen und Scores liegen anschließend in MySQL.
        - Fehlende, partielle, veraltete oder fehlgeschlagene Daten bleiben als sichtbarer Text erhalten.
        """
    )

    st.markdown("### 2) Features")
    st.markdown(
        """
        - Technische Features umfassen Momentum, gleitende Durchschnitte, Volatilität, Drawdown und Volumentrend.
        - Fundamentale Features umfassen Wachstum, Margen, Bewertung, Verschuldung und Marktkapitalisierung.
        - Nicht berechenbare Features zeigen den konkreten Grund und die Frische ihrer Eingangsdaten.
        """
    )

    st.markdown("### 3) Prognosemodelle und Backtests")
    st.markdown(
        """
        - Baseline- und Advanced-Modelle verwenden explizite Horizonte, Zieltypen und Modellversionen.
        - Jede Prognose zeigt Konfidenz, Unsicherheit, historische Modellqualität und Datenfrische.
        - Backtests nennen Evaluationszeitraum, Stichprobengröße, Accuracy, Precision, Recall, MAE und Caveats.
        - Historische Qualität ist keine Garantie für zukünftige Ergebnisse.
        """
    )

    st.markdown("### 4) Preference Scoring")
    st.markdown(
        """
        - Der Preference Score kombiniert Fundamental-, Technik-, Risiko-, Prognose- und Konfidenzkomponenten.
        - Rang, Komponenten, positive Faktoren, depriorisierende Faktoren und Datenqualitätswarnungen sind sichtbar.
        - Der Score ist transparente Entscheidungshilfe und keine versteckte Empfehlung.
        """
    )

    st.markdown("### 5) Systemgrenze")
    st.warning(MANUAL_TRADING_BOUNDARY_TEXT)
    st.markdown(
        "Provider-Limits, Rate Limits, Datenlücken und Modellunsicherheit können Ergebnisse einschränken. "
        "Diese Einschränkungen werden auf den betroffenen Seiten als Text ausgewiesen."
    )

    with st.expander("Legacy: Insider-Trade-Analyse", expanded=False):
        st.markdown(
            "Die frühere Insider-Trade-Pipeline bleibt während der Brownfield-Migration verfügbar. "
            "Sie ist kein Brokerzugang und wird nicht für automatische Transaktionen verwendet."
        )
