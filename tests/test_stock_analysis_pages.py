from __future__ import annotations

import pandas as pd

from src.models.features import FeatureSummary, FundamentalFeatures, TechnicalFeatures
from src.ui.components.status_badges import data_quality_status_view
from src.ui.components import tables as table_components
from src.ui.pages.admin_page import STOCK_ANALYSIS_ADMIN_BOUNDARY_TEXT
from src.ui.pages.dashboard_page import _preference_ranking_rows
from src.ui.pages.methodology_page import MANUAL_TRADING_BOUNDARY_TEXT
from src.ui.pages.model_evaluation_page import (
    _backtest_rows,
    _format_metric_value,
    _metric_definition_rows,
    _model_run_rows,
    _prediction_rows,
)
from src.ui.pages.stock_detail_page import (
    STOCK_DETAIL_SECTIONS,
    _feature_summary_rows,
    _format_feature_value,
    _price_summary_rows,
)
from src.ui.pages.watchlist_page import _normalize_watchlist_df


def test_watchlist_page_normalizes_visible_status_text_columns() -> None:
    df = _normalize_watchlist_df([
        {
            "symbol": "aapl",
            "display_name": None,
            "notes": None,
            "priority": 5,
            "active": True,
            "profile_status_text": "Daten fuer Profil fehlen. Grund: Noch nicht importiert.",
            "price_status_text": "Daten fuer Kursdaten fehlen. Grund: Noch nicht importiert.",
            "financial_status_text": "Daten fuer Finanzdaten fehlen. Grund: Noch nicht importiert.",
            "prediction_status_text": "Daten fuer Prognosen fehlen. Grund: Noch nicht berechnet.",
            "preference_status_text": "Daten fuer Preference Score fehlen. Grund: Noch nicht berechnet.",
        }
    ])

    row = df.iloc[0].to_dict()
    assert row["symbol"] == "AAPL"
    assert row["display_name"] == "—"
    assert row["notes"] == "—"
    assert row["resolution_status"] == "UNRESOLVED"
    assert "Profil" in row["profile_status_text"]
    assert "Kursdaten" in row["price_status_text"]
    assert "Finanzdaten" in row["financial_status_text"]
    assert "Prognosen" in row["prediction_status_text"]
    assert "Preference Score" in row["preference_status_text"]


def test_watchlist_page_keeps_reload_safe_missing_columns_visible() -> None:
    df = _normalize_watchlist_df([
        {
            "symbol": "msft",
            "priority": 1,
            "active": False,
            "resolution_status": "resolved",
        }
    ])

    row = df.iloc[0].to_dict()
    assert row["symbol"] == "MSFT"
    assert row["resolution_status"] == "RESOLVED"
    assert row["profile_status_text"] == "—"
    assert row["price_status_text"] == "—"
    assert row["financial_status_text"] == "—"
    assert row["prediction_status_text"] == "—"
    assert row["preference_status_text"] == "—"
    assert row["data_quality_summary"] == "—"


def test_watchlist_status_table_uses_explicit_text_columns(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_dataframe(data, **kwargs):  # noqa: ANN001
        captured["columns"] = list(data.columns)
        captured["column_config"] = kwargs.get("column_config")
        return None

    monkeypatch.setattr(table_components.st, "dataframe", _fake_dataframe)
    table_components.render_watchlist_status_table(pd.DataFrame([{"symbol": "AAPL"}]))

    assert captured["columns"] == [
        "symbol",
        "display_name",
        "priority",
        "active",
        "resolution_status",
        "profile_status_text",
        "price_status_text",
        "financial_status_text",
        "prediction_status_text",
        "preference_status_text",
        "data_quality_summary",
    ]
    column_config = captured["column_config"]
    assert "Profil" in str(column_config["profile_status_text"])
    assert "Kurse" in str(column_config["price_status_text"])
    assert "Finanzdaten" in str(column_config["financial_status_text"])
    assert "Prognose" in str(column_config["prediction_status_text"])
    assert "Preference" in str(column_config["preference_status_text"])


def test_stock_detail_page_formats_feature_values() -> None:
    assert _format_feature_value(None) == "-"
    assert _format_feature_value(0.123456) == "0.1235"
    assert _format_feature_value("READY") == "READY"


def test_stock_detail_page_builds_feature_summary_rows() -> None:
    summary = FeatureSummary(
        symbol="AAPL",
        as_of=pd.Timestamp("2026-07-08").date(),
        technical=TechnicalFeatures(
            symbol="AAPL",
            feature_date=pd.Timestamp("2026-07-08").date(),
            sma_20=200.12346,
            feature_status="READY",
        ),
        fundamental=FundamentalFeatures(
            symbol="AAPL",
            feature_period=pd.Timestamp("2025-12-31").date(),
            revenue_growth=0.12,
            feature_status="INCOMPLETE",
            unavailable_reason="Missing valuation_ratio.",
        ),
        status="INCOMPLETE",
    )

    rows = _feature_summary_rows(summary)

    assert {"group": "Technical", "feature": "sma_20", "value": "200.1235"} in rows
    assert {"group": "Fundamental", "feature": "revenue_growth", "value": "0.1200"} in rows
    assert {"group": "Fundamental", "feature": "unavailable_reason", "value": "Missing valuation_ratio."} in rows


def test_stock_detail_page_exposes_all_analysis_sections_and_price_freshness() -> None:
    assert STOCK_DETAIL_SECTIONS == (
        "Unternehmensprofil",
        "Kursübersicht",
        "Features",
        "Prognosen",
        "Preference Score",
        "Datenqualität",
    )
    rows = _price_summary_rows(
        [
            {
                "price_date": "2026-07-10",
                "close_price": 212.25,
                "volume": 123456,
                "provider": "FMP",
                "source_refreshed_at": "2026-07-10T22:00:00Z",
                "quality_status": "STALE",
            }
        ]
    )
    combined = " ".join(str(value) for value in rows[0].values())
    assert "2026-07-10" in combined
    assert "STALE" in combined
    assert "2026-07-10T22:00:00Z" in combined


def test_model_evaluation_page_formats_model_and_backtest_rows() -> None:
    assert _format_metric_value(None) == "-"
    assert _format_metric_value(0.81234) == "0.8123"

    model_rows = _model_run_rows([
        {
            "model_run_id": "run-1",
            "model_name": "baseline",
            "model_type": "BASELINE",
            "horizon_days": 20,
            "target_type": "expected_return",
            "status": "READY",
            "quality_summary_json": {"quality_score": 0.75},
            "training_completed_at": "2026-07-10T12:00:00Z",
        }
    ])
    assert model_rows[0]["quality"] == "0.7500"
    assert model_rows[0]["status"] == "READY"

    prediction_rows = _prediction_rows([
        {
            "symbol": "AAPL",
            "model_run_id": "run-1",
            "prediction_as_of": "2026-07-09",
            "horizon_days": 20,
            "direction": "POSITIVE",
            "expected_return": 0.04,
            "confidence": 0.70,
            "uncertainty": 0.15,
            "model_quality_score": 0.75,
            "input_refreshed_at": "2026-07-09T12:00:00Z",
        }
    ])
    assert prediction_rows[0]["confidence"] == "0.7000"
    assert prediction_rows[0]["uncertainty"] == "0.1500"
    assert prediction_rows[0]["model_quality"] == "0.7500"

    backtest_rows = _backtest_rows([
        {
            "model_run_id": "run-1",
            "horizon_days": 20,
            "sample_size": 12,
            "accuracy": 0.66,
            "precision_score": 0.70,
            "recall_score": 0.60,
            "mean_absolute_error": 0.025,
            "caveats_text": "Small sample.",
        }
    ])
    assert backtest_rows[0]["accuracy"] == "0.6600"
    assert backtest_rows[0]["caveats"] == "Small sample."

    definitions = _metric_definition_rows()
    definition_text = " ".join(row["definition"] for row in definitions).lower()
    assert {row["metric"] for row in definitions} >= {"Accuracy", "Precision", "Recall", "MAE"}
    assert "stichprobe" in definition_text


def test_data_quality_component_maps_every_required_text_state() -> None:
    expected = {
        "READY": "Bereit",
        "MISSING": "Fehlt",
        "STALE": "Veraltet",
        "INCOMPLETE": "Unvollstaendig",
        "LOW_QUALITY": "Niedrige Qualitaet",
        "FAILED": "Fehlgeschlagen",
        "UNKNOWN": "Unbekannt",
    }
    for status, label in expected.items():
        view = data_quality_status_view(status, data_category="prediction", reason="Testgrund")
        assert view["status"] == status
        assert view["label"] == label
        assert label.split()[0] in view["text"]
        assert "Testgrund" in view["text"]


def test_methodology_and_admin_state_manual_trading_boundary() -> None:
    combined = f"{MANUAL_TRADING_BOUNDARY_TEXT} {STOCK_ANALYSIS_ADMIN_BOUNDARY_TEXT}".lower()
    assert "keine broker-anbindung" in combined
    assert "keine order" in combined
    assert "manuell" in combined
    assert "außerhalb" in combined


def test_dashboard_page_formats_preference_ranking_without_execution_language() -> None:
    rows = _preference_ranking_rows([
        {
            "rank_position": 1,
            "symbol": "AAPL",
            "preference_score": 82.456,
            "fundamental_component": 80,
            "technical_component": 75,
            "risk_component": 70,
            "prediction_component": 90,
            "confidence": 0.74,
            "uncertainty": 0.12,
            "explanation_positive": "Preference supported by solid fundamentals.",
            "explanation_negative": "No major deprioritizing component is visible.",
            "data_quality_summary": "All required scoring inputs are available.",
        }
    ])

    assert rows[0]["rank"] == "1"
    assert rows[0]["preference_score"] == "82.46"
    assert rows[0]["confidence"] == "0.74"
    combined_text = " ".join(rows[0].values()).lower()
    assert "preference supported" in combined_text
    assert not any(term in combined_text for term in ("buy recommendation", "order", "execution", "trade decision"))
