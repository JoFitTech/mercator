"""Auto-Import-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import time
import streamlit as st
from datetime import datetime, timedelta
from src.services.import_service import ImportService
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)

def handle_auto_import(import_service: ImportService, interval_minutes: int = 60):
    """Prüft, ob ein Auto-Import fällig ist und führt ihn ggf. aus."""
    if not import_service:
        return

    # Letzten Import-Zeitpunkt prüfen
    last_run = st.session_state.get("last_auto_import_run")
    now = datetime.now()
    
    if last_run is None or (now - last_run) > timedelta(minutes=interval_minutes):
        LOGGER.info("Starte Auto-Import (Intervall: %s min)", interval_minutes)
        try:
            summary = import_service.run_hourly_import()
            st.session_state["last_auto_import_run"] = now
            st.session_state["last_import_summary"] = summary
            LOGGER.info("Auto-Import erfolgreich: %s Records", summary.upserted_clean_records)
        except Exception as e:
            LOGGER.error("Auto-Import fehlgeschlagen: %s", e)

def render_import_status_toast():
    """Zeigt eine kurze Benachrichtigung über den letzten Import-Status."""
    if "last_import_summary" in st.session_state:
        summary = st.session_state["last_import_summary"]
        st.toast(f"✅ Auto-Import abgeschlossen: {summary.upserted_clean_records} Trades aktualisiert.")
        del st.session_state["last_import_summary"]
