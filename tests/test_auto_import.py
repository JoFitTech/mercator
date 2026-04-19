"""Tests für die Auto-Import-Entscheidungslogik (P0.3 / P0.4)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.services.app_settings_service import RuntimeSettings


def _make_runtime(
    enabled: bool = True,
    interval_minutes: int = 60,
    on_start: bool = False,
) -> RuntimeSettings:
    return RuntimeSettings(
        min_trade_value=50000,
        require_purchase_event=True,
        require_common_stock=True,
        allowed_acquisition_or_disposition=("A",),
        allowed_transaction_types=("P-Purchase",),
        profile_gate_filter_statuses=("NOT_REQUESTED",),
        profile_ttl_days=30,
        lookup_mode="symbol",
        auto_import_enabled=enabled,
        auto_import_interval_minutes=interval_minutes,
        auto_import_on_start=on_start,
    )


def _make_import_service(records: int = 5):
    svc = MagicMock()
    summary = MagicMock()
    summary.upserted_clean_records = records
    svc.run_hourly_import.return_value = summary
    return svc


class TestHandleAutoImport:
    """Überprüft, dass handle_auto_import korrekt auf RuntimeSettings reagiert."""

    def test_disabled_never_runs(self):
        """Wenn auto_import_enabled=False, darf niemals importiert werden."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=False)
        svc = _make_import_service()

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = {}
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_not_called()

    def test_none_runtime_never_runs(self):
        """Wenn kein RuntimeSettings-Objekt übergeben wird, sicherer Default → kein Import."""
        from src.app.auto_import import handle_auto_import

        svc = _make_import_service()

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = {}
            handle_auto_import(svc, runtime=None)

        svc.run_hourly_import.assert_not_called()

    def test_on_start_triggers_first_run_immediately(self):
        """auto_import_on_start=True und noch kein last_run → sofortiger Import."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, on_start=True)
        svc = _make_import_service()

        session = {}
        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = session
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_called_once()
        assert "last_auto_import_run" in session

    def test_on_start_false_does_not_run_on_first_call(self):
        """auto_import_on_start=False und kein last_run → kein sofortiger Import."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, on_start=False)
        svc = _make_import_service()

        session = {}
        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = session
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_not_called()

    def test_interval_due_triggers_import(self):
        """Wenn das Intervall abgelaufen ist, wird importiert."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, interval_minutes=10)
        svc = _make_import_service()

        past = datetime.now() - timedelta(minutes=15)
        session = {"last_auto_import_run": past}

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = session
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_called_once()

    def test_interval_not_due_skips_import(self):
        """Wenn das Intervall noch nicht abgelaufen ist, wird NICHT importiert."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, interval_minutes=60)
        svc = _make_import_service()

        recent = datetime.now() - timedelta(minutes=5)
        session = {"last_auto_import_run": recent}

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = session
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_not_called()

    def test_no_import_service_does_nothing(self):
        """Wenn kein ImportService vorhanden, stille Rückkehr ohne Fehler."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, on_start=True)

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = {}
            handle_auto_import(None, runtime=runtime)  # kein Fehler erwartet

    def test_disabled_flag_blocks_import_even_if_runtime_allows(self):
        """Der explizite disabled-Flag muss Auto-Import deterministisch sperren."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, on_start=True)
        svc = _make_import_service()

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = {}
            handle_auto_import(svc, runtime=runtime, disabled=True)

        svc.run_hourly_import.assert_not_called()

    def test_non_positive_interval_is_clamped(self):
        """Ungültige Intervalle dürfen nicht craschen und werden auf >=1 Minute geklemmt."""
        from src.app.auto_import import handle_auto_import

        runtime = _make_runtime(enabled=True, interval_minutes=0, on_start=False)
        svc = _make_import_service()
        past = datetime.now() - timedelta(minutes=2)
        session = {"last_auto_import_run": past}

        with patch("src.app.auto_import.st") as mock_st:
            mock_st.session_state = session
            handle_auto_import(svc, runtime=runtime)

        svc.run_hourly_import.assert_called_once()
