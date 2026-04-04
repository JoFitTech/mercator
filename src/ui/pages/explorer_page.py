"""Explorer-Seite mit interaktiven Filtern auf bereinigte Trades."""

from __future__ import annotations

import streamlit as st

from src.services.analysis_service import AnalysisService


def render_explorer_page(service: AnalysisService) -> None:
    """Rendert Filter und Tabelle für bereinigte MySQL-Daten."""
    st.title("Mercator")
    st.markdown("### Datenexplorer")
    st.caption("Interaktive Filter- und Tabellenansicht für bereinigte Finanzdaten.")

    advanced_mode = st.session_state.get("advanced_mode", False)

    with st.expander("Filter-Optionen", expanded=True):
        c1, c2, c3 = st.columns(3)
        symbol = c1.text_input("Börsensymbol", placeholder="z.B. AAPL")
        transaction_type = c2.text_input("Transaktionstyp", placeholder="z.B. P-Purchase")
        gate_status = c3.selectbox("Gate-Status", ["Alle", "PASS", "PENDING", "FAIL"])

        if advanced_mode:
            c4, c5 = st.columns(2)
            sector = c4.text_input("Sektor", placeholder="z.B. Technology")
            country = c5.text_input("Land", placeholder="z.B. US")
        else:
            sector = ""
            country = ""

    filters = {
        "symbol": symbol.strip().upper() or None,
        "transaction_type": transaction_type.strip() or None,
        "gate_status": None if gate_status == "Alle" else gate_status,
        "sector": sector.strip() or None,
        "country": country.strip() or None,
    }

    data = service.get_filtered_trades(filters=filters, limit=500)
    
    if data.empty:
        st.info("Es sind aktuell keine verarbeiteten Daten verfügbar, die den Filtern entsprechen.")
        return

    st.markdown("---")
    
    # Fachliche Spaltenreihenfolge
    core_cols = [
        "symbol_at_trade", "company_key", "transaction_date", "reporting_name", "transaction_type",
        "qty", "price", "trade_value_estimated", "gate_status"
    ]
    
    company_cols = ["company_name", "sector", "country"]
    
    technical_cols = [
        "gate_reason", "filing_date", "reporting_cik", "company_cik", 
        "type_of_owner", "acquisition_or_disposition", "direct_or_indirect", 
        "form_type", "security_name", "source_url", "dedupe_key", "fetched_at"
    ]

    # Dynamische Spaltenauswahl
    display_cols = core_cols + company_cols
    if advanced_mode:
        display_cols = display_cols + technical_cols

    # Nur existierende Spalten nehmen
    final_cols = [c for c in display_cols if c in data.columns]
    
    # UI-Anzeige
    st.subheader(f"Ergebnisse ({len(data)} Datensätze)")
    
    # Download Button oben rechts (simuliert durch Spalten)
    col_text, col_btn = st.columns([0.8, 0.2])
    with col_btn:
        st.download_button(
            label="Export CSV",
            data=data.to_csv(index=False).encode("utf-8"),
            file_name="mercator_export.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.dataframe(
        data[final_cols].style.format({
            "price": "{:,.2f}",
            "qty": "{:,.0f}",
            "trade_value_estimated": "{:,.2f}"
        }, na_rep="-"),
        use_container_width=True,
        hide_index=True
    )
