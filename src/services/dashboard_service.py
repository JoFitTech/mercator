"""Service zur Aufbereitung von KPI- und Chartdaten für Streamlit."""

from __future__ import annotations

import pandas as pd

from src.services.analysis_service import AnalysisService


class DashboardService:
    """Bereitet Anzeigeobjekte für Dashboard-Komponenten vor."""

    def __init__(self, analysis_service: AnalysisService) -> None:
        self.analysis_service = analysis_service

    def build_dashboard_payload(self, trades_df: pd.DataFrame) -> dict:
        """Liefert ein minimales Payload mit KPIs und tabellarischen Daten."""
        analysis = self.analysis_service.build_basic_metrics(trades_df)
        return {
            "kpis": analysis.metrics,
            "row_count": analysis.dataframe_rows,
            "note": analysis.note,
        }
