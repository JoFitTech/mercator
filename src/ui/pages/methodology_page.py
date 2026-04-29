"""Methodikseite mit Datenquelle, Datenfluss und MVP-Grenzen."""

from __future__ import annotations

import streamlit as st


def render_methodology_page() -> None:
    """Rendert eine präsentationsfähige Methodik- und Architekturübersicht."""
    st.title("Methodik & Architektur")
    st.caption("Technische Dokumentation der Pipeline, Datenmodelle und Verarbeitungsregeln.")

    st.markdown("### 1) Ziel")
    st.write(
        "Mercator analysiert öffentliche Insider-Trade-Daten aus der FMP API. "
        "Ziel ist nicht die Anzeige jedes Trades, sondern die nachvollziehbare Priorisierung relevanter Insider-Signale."
    )

    st.markdown("### 2) Datenquelle")
    st.markdown(
        """
        - **API1:** `latest insider trades`
        - **API2:** `company profile`
        - **API3:** `historical price and volume`
        - Keine Fake-Daten im finalen Demo-Flow
        - API-Calls erfolgen im Importpfad, nicht bei normaler Tabellenfilterung
        """
    )

    st.markdown("### 3) Pipeline")
    st.graphviz_chart(
        """
        digraph G {
            rankdir=LR;
            API1 [label="API1\nlatest insider trades"];
            RAW [label="MongoDB\nRaw Storage"];
            VAL [label="Validation"];
            GATE [label="Pre-Gates"];
            ACC [label="3-Tage\nAkkumulation"];
            API2 [label="API2\nProfile"];
            API3 [label="API3\nHistorical EOD (500d)"];
            SCORE [label="Finales\nScoring"];
            CLEAN [label="MySQL\nClean Storage"];
            UI [label="Streamlit UI"];

            API1 -> RAW -> VAL -> GATE -> ACC -> API2 -> API3 -> SCORE -> CLEAN -> UI;
        }
        """
    )

    st.markdown("### 4) Raw / Clean Trennung")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            **MongoDB = Raw Store**
            - Speichert rohe API-Payloads (`insider_trades_raw`, `companies`)
            - Audit- und Reimport-Basis
            - Nachweis für die zweite Datenbank im Uni-Setup
            """
        )
    with c2:
        st.markdown(
            """
            **MySQL = Clean Store**
            - Speichert bereinigte, normalisierte und analysierbare Tabellen
            - Grundlage für Dashboard, Trades und Unternehmen
            - Keine Rohrekonstruktion als fachlicher Ersatz für Mongo Raw
            """
        )

    st.markdown("### 5) Validation")
    st.markdown(
        """
        - `price <= 0` -> invalid (`PRICE_INVALID`)
        - `qty <= 0` -> Drop/Reject
        - fehlendes Symbol -> Drop/Reject
        - fehlende Filing-/Transaction-Daten -> invalid
        """
    )

    st.markdown("### 6) Gates & Transaction Codes")
    st.markdown(
        """
        - `formType == 4`
        - `trade_value >= 100000`
        - Instrument nur Aktie/ETF im finalen Modell
        - Filing-Freshness: >45 Tage Reject, >21 Tage maximal Watchlist
        - Transaction-Code-Klassen:
          - `P` = CORE_BUY
          - `S` = CORE_SELL
          - `I/L` = SECONDARY_SIGNAL
          - `J/V` = MANUAL_REVIEW
          - `A/M/F/G` (und weitere Excludes) = EXCLUDE_FROM_CORE
        """
    )

    st.markdown("### 7) Scoring")
    st.markdown(
        """
        - Finaler Score erst nach API3-Enrichment
        - Eingaben u. a.: Trade-Value, Filing-Age, Code-Klasse, Direction,
          Akkumulation, Market-Cap/Sector/Industry, Trend/Liquidität/Momentum
        - Ergebnis als Klassen A, B, C, D, E
        """
    )

    st.markdown("### 8) Einschränkungen")
    st.markdown(
        """
        - Kein Investment-Rat
        - FMP API-Limits (Budget/Rate-Limits)
        - Datenqualität ist quellenabhängig
        - Raw Store muss nach Import befüllt sein
        - Tunnel/Public Share nur lokal für explizite Test-/Review-Zwecke
        """
    )
