"""Service für analytische Auswertungen auf bereinigten Daten."""

from __future__ import annotations

import pandas as pd

from src.models.analysis_result import AnalysisResult


class AnalysisService:
    """Erstellt robuste Kennzahlen und vorbereitete Ausgabetabellen."""

    def build_basic_metrics(self, trades_df: pd.DataFrame) -> AnalysisResult:
        """Erzeugt einfache Metriken für Dashboard und Präsentation."""
        if trades_df.empty:
            return AnalysisResult(
                title="Basisanalyse",
                metrics={"rows": 0, "unique_ticker": 0},
                dataframe_rows=0,
                note="Keine Daten verfügbar.",
            )

        metrics = {
            "rows": int(len(trades_df.index)),
            "unique_ticker": int(trades_df.get("ticker", pd.Series(dtype=str)).nunique()),
        }
        return AnalysisResult(
            title="Basisanalyse",
            metrics=metrics,
            dataframe_rows=int(len(trades_df.index)),
            note="Kennzahlen wurden aus bereinigten Datensätzen aggregiert.",
        )
