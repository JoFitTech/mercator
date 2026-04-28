"""Prüft, dass Fehlerzustände im Dashboard sichtbar bleiben und nicht still zu Nullwerten verflachen.

Die Datei wird gebraucht, um Fehlersignale aus Service- und Datenquellenpfaden korrekt bis zur UI-Abbildung
abzusichern.
"""

from __future__ import annotations

import pandas as pd

from src.services.dashboard_service import DashboardService


class _FailingTradeRepo:
    def fetch_trades_enriched_with_company(self, limit: int, filters: dict):  # noqa: ANN001
        raise RuntimeError("Connection failed with status 530")


class _DummyCompanyRepo:
    pass


def test_dashboard_payload_surfaces_upstream_errors_instead_of_silent_zero_state() -> None:
    service = DashboardService(
        raw_repo=None,
        company_mongo_repo=None,
        trade_repo=_FailingTradeRepo(),  # type: ignore[arg-type]
        company_repo=_DummyCompanyRepo(),  # type: ignore[arg-type]
    )

    payload = service.build_dashboard_payload(filters={})

    assert "530" in str(payload.get("payload_error_message"))
    assert payload.get("kpi_relevant_trades_count") == 0
    assert isinstance(payload.get("sector_distribution_buy"), pd.DataFrame)
