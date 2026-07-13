"""Complete stock-analysis detail page with fault-isolated data sections."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

import streamlit as st

from src.models.features import FeatureSummary
from src.ui.components.page_scaffold import render_page_header
from src.ui.components.status_badges import render_data_quality_status


STOCK_DETAIL_SECTIONS = (
    "Unternehmensprofil",
    "Kursübersicht",
    "Features",
    "Prognosen",
    "Preference Score",
    "Datenqualität",
)


def _format_feature_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _feature_summary_rows(summary: FeatureSummary) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group_name, feature in (("Technical", summary.technical), ("Fundamental", summary.fundamental)):
        if feature is None:
            continue
        payload = asdict(feature) if is_dataclass(feature) else dict(feature)
        for key, value in payload.items():
            if key in {"symbol", "feature_date", "feature_period", "input_refreshed_at"}:
                continue
            rows.append({"group": group_name, "feature": key, "value": _format_feature_value(value)})
    return rows


def _record_feature_rows(group: str, record: dict[str, Any] | None) -> list[dict[str, str]]:
    if not record:
        return []
    return [
        {"group": group, "feature": str(key), "value": _format_feature_value(value)}
        for key, value in record.items()
        if key not in {"symbol", "created_at", "updated_at"}
    ]


def _price_summary_rows(prices: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not prices:
        return []
    latest = prices[0]
    return [
        {
            "Handelstag": str(latest.get("price_date") or "-"),
            "Schlusskurs": _format_feature_value(latest.get("adjusted_close") or latest.get("close_price")),
            "Volumen": _format_feature_value(latest.get("volume")),
            "Provider": str(latest.get("provider") or "-"),
            "Status": str(latest.get("quality_status") or "UNKNOWN"),
            "Datenfrische": str(latest.get("source_refreshed_at") or "-"),
            "Historie": f"{len(prices)} Handelstage geladen",
        }
    ]


def _render_status(statuses: dict[str, Any], key: str, category: str) -> None:
    status = statuses.get(key) or {}
    render_data_quality_status(
        str(status.get("status") or "UNKNOWN"),
        data_category=category,
        message=status.get("message"),
        source_refreshed_at=status.get("source_refreshed_at"),
    )


def _render_profile(profile: dict[str, Any] | None) -> None:
    if not profile:
        st.info("Unternehmensprofil fehlt. Das Symbol bleibt für spätere Importe sichtbar.")
        return
    fields = {
        "Symbol": profile.get("current_symbol") or profile.get("symbol"),
        "Unternehmen": profile.get("company_name") or profile.get("name"),
        "Sektor": profile.get("sector"),
        "Branche": profile.get("industry"),
        "Land": profile.get("country"),
        "Börse": profile.get("exchange") or profile.get("exchange_short_name"),
        "Marktkapitalisierung": profile.get("market_cap"),
    }
    st.dataframe(
        [{"Merkmal": label, "Wert": _format_feature_value(value)} for label, value in fields.items()],
        hide_index=True,
        use_container_width=True,
    )


def _render_prediction_rows(predictions: list[dict[str, Any]]) -> None:
    if not predictions:
        st.info("Prognosen fehlen oder wurden noch nicht berechnet.")
        return
    rows = []
    for prediction in predictions:
        rows.append(
            {
                "Modelllauf": prediction.get("model_run_id") or "-",
                "Stand": prediction.get("prediction_as_of") or "-",
                "Horizont": prediction.get("horizon_days") or "-",
                "Richtung": prediction.get("direction") or "-",
                "Erwartete Rendite": _format_feature_value(prediction.get("expected_return")),
                "Konfidenz": _format_feature_value(prediction.get("confidence")),
                "Unsicherheit": _format_feature_value(prediction.get("uncertainty")),
                "Modellqualität": _format_feature_value(prediction.get("model_quality_score")),
                "Datenfrische": prediction.get("input_refreshed_at") or "-",
            }
        )
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_preference(preference: dict[str, Any] | None) -> None:
    if not preference:
        st.info("Preference Score fehlt oder wurde noch nicht berechnet.")
        return
    fields = [
        ("Preference Score", preference.get("preference_score")),
        ("Rang", preference.get("rank_position")),
        ("Fundamental", preference.get("fundamental_component")),
        ("Technisch", preference.get("technical_component")),
        ("Risiko", preference.get("risk_component")),
        ("Prognose", preference.get("prediction_component")),
        ("Konfidenz", preference.get("confidence")),
        ("Unsicherheit", preference.get("uncertainty")),
    ]
    st.dataframe(
        [{"Komponente": label, "Wert": _format_feature_value(value)} for label, value in fields],
        hide_index=True,
        use_container_width=True,
    )
    st.markdown(f"**Positive Faktoren:** {preference.get('explanation_positive') or 'Keine Erklärung verfügbar.'}")
    st.markdown(f"**Depriorisierende Faktoren:** {preference.get('explanation_negative') or 'Keine Erklärung verfügbar.'}")
    st.caption(str(preference.get("data_quality_summary") or "Datenqualitätsstatus unbekannt."))


def _empty_stock_detail(symbol: str) -> dict[str, Any]:
    categories = {
        "profile": "Unternehmensprofil fehlt, weil MySQL nicht verfügbar ist.",
        "prices": "Kursdaten fehlen, weil MySQL nicht verfügbar ist.",
        "technical_features": "Technische Features fehlen, weil MySQL nicht verfügbar ist.",
        "fundamental_features": "Fundamentale Features fehlen, weil MySQL nicht verfügbar ist.",
        "predictions": "Prognosen fehlen, weil MySQL nicht verfügbar ist.",
        "preference": "Preference Score fehlt, weil MySQL nicht verfügbar ist.",
    }
    return {
        "symbol": symbol,
        "profile": None,
        "prices": [],
        "technical_features": None,
        "fundamental_features": None,
        "predictions": [],
        "preference_score": None,
        "quality_issues": [],
        "statuses": {
            key: {"status": "MISSING", "message": message, "source_refreshed_at": None}
            for key, message in categories.items()
        },
        "quality_read_error": "MySQL nicht verfügbar.",
    }


def render_stock_detail_page(
    feature_summary: FeatureSummary | None = None,
    feature_service: Any | None = None,
    symbol: str | None = None,
    analysis_service: Any | None = None,
) -> None:
    """Render the complete detail read model while preserving the feature-only adapter."""

    normalized_symbol = str(symbol or "").strip().upper()
    if normalized_symbol:
        detail = (
            analysis_service.get_stock_detail(normalized_symbol)
            if analysis_service is not None
            else _empty_stock_detail(normalized_symbol)
        )
        statuses = detail.get("statuses") or {}
        render_page_header(
            f"Aktienanalyse: {normalized_symbol}",
            "Profil, Kurse, Features, Prognosen und Preference Score mit sichtbarer Datenqualität.",
        )

        st.subheader(STOCK_DETAIL_SECTIONS[0])
        _render_status(statuses, "profile", "company_profile")
        _render_profile(detail.get("profile"))

        st.subheader(STOCK_DETAIL_SECTIONS[1])
        _render_status(statuses, "prices", "historical_price")
        price_rows = _price_summary_rows(detail.get("prices") or [])
        if price_rows:
            st.dataframe(price_rows, hide_index=True, use_container_width=True)
        else:
            st.info("Historische Kursdaten fehlen.")

        st.subheader(STOCK_DETAIL_SECTIONS[2])
        _render_status(statuses, "technical_features", "technical_features")
        _render_status(statuses, "fundamental_features", "fundamental_features")
        feature_rows = _record_feature_rows("Technisch", detail.get("technical_features"))
        feature_rows += _record_feature_rows("Fundamental", detail.get("fundamental_features"))
        if feature_rows:
            st.dataframe(feature_rows, hide_index=True, use_container_width=True)
        else:
            st.info("Berechnete Features fehlen.")

        st.subheader(STOCK_DETAIL_SECTIONS[3])
        _render_status(statuses, "predictions", "prediction")
        _render_prediction_rows(detail.get("predictions") or [])

        st.subheader(STOCK_DETAIL_SECTIONS[4])
        _render_status(statuses, "preference", "preference_score")
        _render_preference(detail.get("preference_score"))

        st.subheader(STOCK_DETAIL_SECTIONS[5])
        st.caption(
            "Mögliche Textzustände: bereit, fehlt, veraltet, unvollständig, niedrige Qualität, fehlgeschlagen oder unbekannt."
        )
        issues = detail.get("quality_issues") or []
        if issues:
            st.dataframe(issues, hide_index=True, use_container_width=True)
        else:
            st.success("Keine offenen Datenqualitätsprobleme erfasst.")
        if detail.get("quality_read_error"):
            st.warning("Datenqualitätsprobleme konnten nicht vollständig geladen werden.")
        return

    st.header("Stock Detail")
    summary = feature_summary
    if summary is None and feature_service is not None and normalized_symbol:
        summary = feature_service.calculate_for_symbol(normalized_symbol)

    if summary is None:
        st.info("Kein Symbol ausgewaehlt.")
        return

    st.subheader(summary.symbol)
    st.metric("Feature-Status", summary.status)
    if summary.unavailable_reason:
        st.warning(summary.unavailable_reason)

    rows = _feature_summary_rows(summary)
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("Keine berechneten Features verfuegbar.")
