"""Model evaluation page helpers for prediction quality readouts."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.ui.components.page_scaffold import render_page_header
from src.ui.components.status_badges import render_data_quality_status


def _metric_definition_rows() -> list[dict[str, str]]:
    return [
        {"metric": "Accuracy", "definition": "Anteil korrekter Richtungsprognosen in der Evaluationsstichprobe."},
        {"metric": "Precision", "definition": "Anteil korrekter positiver Prognosen an allen positiv prognostizierten Fällen."},
        {"metric": "Recall", "definition": "Anteil erkannter positiver Fälle an allen tatsächlich positiven Fällen."},
        {"metric": "MAE", "definition": "Mittlere absolute Abweichung zwischen prognostizierter und beobachteter Rendite."},
    ]


def _format_metric_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _model_run_rows(model_runs: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for run in model_runs:
        rows.append(
            {
                "model_run_id": str(run.get("model_run_id") or "-"),
                "model_name": str(run.get("model_name") or "-"),
                "model_type": str(run.get("model_type") or "-"),
                "model_version": str(run.get("model_version") or "-"),
                "horizon_days": str(run.get("horizon_days") or "-"),
                "target_type": str(run.get("target_type") or "-"),
                "status": str(run.get("status") or "UNKNOWN"),
                "quality": _format_metric_value(_quality_from_summary(run.get("quality_summary_json"))),
                "completed_at": str(run.get("training_completed_at") or "-"),
                "training_window": f"{run.get('training_window_start') or '-'} bis {run.get('training_window_end') or '-'}",
            }
        )
    return rows


def _backtest_rows(backtests: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in backtests:
        rows.append(
            {
                "model_run_id": str(result.get("model_run_id") or "-"),
                "horizon_days": str(result.get("horizon_days") or "-"),
                "sample_size": str(result.get("sample_size") if result.get("sample_size") is not None else "-"),
                "evaluation_window": f"{result.get('evaluation_start') or '-'} bis {result.get('evaluation_end') or '-'}",
                "accuracy": _format_metric_value(result.get("accuracy")),
                "precision": _format_metric_value(result.get("precision_score")),
                "recall": _format_metric_value(result.get("recall_score")),
                "mae": _format_metric_value(result.get("mean_absolute_error")),
                "caveats": str(result.get("caveats_text") or "-"),
            }
        )
    return rows


def _prediction_rows(predictions: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for prediction in predictions:
        rows.append(
            {
                "symbol": str(prediction.get("symbol") or "-"),
                "model_run_id": str(prediction.get("model_run_id") or "-"),
                "as_of": str(prediction.get("prediction_as_of") or "-"),
                "horizon_days": str(prediction.get("horizon_days") or "-"),
                "direction": str(prediction.get("direction") or "-"),
                "expected_return": _format_metric_value(prediction.get("expected_return")),
                "confidence": _format_metric_value(prediction.get("confidence")),
                "uncertainty": _format_metric_value(prediction.get("uncertainty")),
                "model_quality": _format_metric_value(prediction.get("model_quality_score")),
                "input_refreshed_at": str(prediction.get("input_refreshed_at") or "-"),
            }
        )
    return rows


def _quality_from_summary(summary: Any) -> float | None:
    if isinstance(summary, dict):
        value = summary.get("quality_score")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _safe_list(callback) -> tuple[list[dict[str, Any]], Exception | None]:  # noqa: ANN001
    try:
        return list(callback() or []), None
    except Exception as exc:  # noqa: BLE001 - keep remaining evaluation sections visible
        return [], exc


def render_model_evaluation_page(
    prediction_repository: Any | None = None,
    backtest_repository: Any | None = None,
) -> None:
    """Rendert Modellqualitaet, Frische und Backtest-Caveats."""

    render_page_header(
        "Modellbewertung",
        "Historische Modellqualität, Prognoseunsicherheit und Datenfrische transparent vergleichen.",
    )
    st.subheader("Metrikdefinitionen")
    st.dataframe(_metric_definition_rows(), hide_index=True, use_container_width=True)
    st.caption("Datenfrische bezeichnet den Stand der Eingabedaten beziehungsweise den Abschluss des Modelllaufs.")

    if prediction_repository is None:
        render_data_quality_status(
            "MISSING",
            data_category="model_run",
            reason="Prediction-Repository ist nicht verfügbar",
        )
        return

    model_runs, model_error = _safe_list(lambda: prediction_repository.list_model_runs(limit=50))
    st.subheader("Modellläufe")
    if model_error is not None:
        render_data_quality_status("FAILED", data_category="model_run", reason=str(model_error))
    elif not model_runs:
        render_data_quality_status("MISSING", data_category="model_run", reason="Noch keine Modellläufe vorhanden")
    else:
        render_data_quality_status(
            "READY",
            data_category="model_run",
            reason=f"{len(model_runs)} Modellläufe geladen",
            source_refreshed_at=model_runs[0].get("training_completed_at"),
        )
        st.dataframe(_model_run_rows(model_runs), hide_index=True, use_container_width=True)

    predictions, prediction_error = _safe_list(lambda: prediction_repository.list_predictions(limit=100))
    st.subheader("Prognosen")
    if prediction_error is not None:
        render_data_quality_status("FAILED", data_category="prediction", reason=str(prediction_error))
    elif predictions:
        render_data_quality_status(
            "READY",
            data_category="prediction",
            reason=f"{len(predictions)} Prognosen geladen",
            source_refreshed_at=predictions[0].get("input_refreshed_at"),
        )
        st.dataframe(_prediction_rows(predictions), hide_index=True, use_container_width=True)
    else:
        render_data_quality_status("MISSING", data_category="prediction", reason="Noch keine Prognosen vorhanden")

    st.subheader("Backtests")
    if backtest_repository is None:
        render_data_quality_status("MISSING", data_category="backtest", reason="Backtest-Repository ist nicht verfügbar")
        return

    backtests, backtest_error = _safe_list(lambda: backtest_repository.list_results(limit=50))
    if backtest_error is not None:
        render_data_quality_status("FAILED", data_category="backtest", reason=str(backtest_error))
    elif backtests:
        render_data_quality_status(
            "READY",
            data_category="backtest",
            reason=f"{len(backtests)} Backtests geladen",
            source_refreshed_at=backtests[0].get("created_at"),
        )
        st.dataframe(_backtest_rows(backtests), hide_index=True, use_container_width=True)
    else:
        render_data_quality_status("MISSING", data_category="backtest", reason="Noch keine Backtest-Ergebnisse vorhanden")
