"""Basistests für AnalysisService."""

import pandas as pd

from src.services.analysis_service import AnalysisService


def test_analysis_service_handles_empty_dataframe_without_crash() -> None:
    """Bei fehlenden Daten soll ein valides Ergebnisobjekt entstehen."""
    service = AnalysisService()
    result = service.build_basic_metrics(pd.DataFrame())
    assert result.metrics["rows"] == 0
    assert result.metrics["unique_ticker"] == 0
