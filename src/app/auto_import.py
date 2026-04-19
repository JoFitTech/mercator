"""Auto-Import-Logik für Mercator (Requirement 5.1)."""

from __future__ import annotations
import streamlit as st
from datetime import datetime, timedelta
from src.services.import_service import ImportService
from src.services.app_settings_service import RuntimeSettings
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


def handle_auto_import(
    import_service: ImportService,
    runtime: RuntimeSettings | None = None,
    disabled: bool = False,
):
    """Prüft, ob ein Auto-Import fällig ist und führt ihn ggf. aus.

    Entscheidungslogik:
    1. Wenn ``runtime.auto_import_enabled`` False ist → kein Import.
    2. Beim allerersten App-Start und ``runtime.auto_import_on_start`` True → sofortiger Import.
    3. Sonst: Import nur wenn seit dem letzten Run ``runtime.auto_import_interval_minutes`` vergangen sind.
    """
    if not import_service or disabled:
        return

    # Ohne RuntimeSettings: Standard-Verhalten deaktiviert (sicher-Default)
    if runtime is None or not runtime.auto_import_enabled:
        return

    interval_minutes = max(1, int(runtime.auto_import_interval_minutes))
    on_start = runtime.auto_import_on_start

    last_run: datetime | None = st.session_state.get("last_auto_import_run")
    now = datetime.now()

    # Beim allerersten App-Start (last_run noch nie gesetzt) und on_start=True sofort importieren
    first_start = last_run is None and on_start
    interval_due = last_run is not None and (now - last_run) > timedelta(minutes=interval_minutes)

    if first_start or interval_due:
        LOGGER.info("Starte Auto-Import (Intervall: %s min, on_start=%s)", interval_minutes, on_start)
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
        st.toast(f"Auto-Import abgeschlossen: {summary.upserted_clean_records} Trades aktualisiert.")
        del st.session_state["last_import_summary"]
