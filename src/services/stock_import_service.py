"""Watchlist-getriebener Stock-Data-Import."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.db.mongo_repository import RawProviderResponseMongoRepository
from src.db.repositories.data_quality_repository import DataQualityRepository
from src.db.repositories.fundamental_metrics_repository import FundamentalMetricsRepository
from src.db.repositories.import_run_repository import ImportRunRepository
from src.db.repositories.stock_price_repository import StockPriceRepository
from src.models.stock import ImportRunSummary, RawProviderResponse
from src.models.watchlist import DataQualityIssue
from src.preprocessing.data_quality_evaluator import QUALITY_FAILED, QUALITY_MISSING, build_data_quality_message
from src.preprocessing.normalization import (
    normalize_company_profile_payload,
    normalize_fundamental_metric_payload,
    normalize_historical_price_payload,
)


class StockImportService:
    """Orchestriert Rohspeicherung und Clean-Normalisierung fuer ein Watchlist-Symbol."""

    INCOME_METRICS = {
        "revenue": "revenue",
        "revenueGrowth": "revenue_growth",
        "netIncome": "net_income",
    }
    KEY_METRICS = {
        "marketCap": "market_cap",
        "peRatio": "pe_ratio",
        "debtToEquity": "debt_to_equity",
    }
    RATIO_METRICS = {
        "grossProfitMargin": "gross_margin",
        "netProfitMargin": "net_margin",
        "debtEquityRatio": "debt_to_equity_ratio",
    }

    def __init__(
        self,
        *,
        fmp_client: Any,
        raw_repository: RawProviderResponseMongoRepository,
        company_repository: Any,
        price_repository: StockPriceRepository,
        metrics_repository: FundamentalMetricsRepository,
        import_run_repository: ImportRunRepository,
        data_quality_repository: DataQualityRepository,
    ) -> None:
        self.fmp_client = fmp_client
        self.raw_repository = raw_repository
        self.company_repository = company_repository
        self.price_repository = price_repository
        self.metrics_repository = metrics_repository
        self.import_run_repository = import_run_repository
        self.data_quality_repository = data_quality_repository

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return str(symbol or "").strip().upper()

    @staticmethod
    def _request_hash(provider: str, category: str, symbol: str, params: dict[str, Any]) -> str:
        encoded = json.dumps(
            {"provider": provider, "category": category, "symbol": symbol, "params": params},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _write_raw(
        self,
        *,
        category: str,
        symbol: str,
        params: dict[str, Any],
        payload: Any,
        fetched_at: datetime,
        status: str = "SUCCESS",
        error_message: str | None = None,
    ) -> str:
        response = RawProviderResponse(
            provider="FMP",
            category=category,
            request_hash=self._request_hash("FMP", category, symbol, params),
            status=status,
            fetched_at=fetched_at,
            symbol=symbol,
            request_params=params,
            payload={"data": payload},
            error_message=error_message,
        )
        return self.raw_repository.upsert_response(response)

    def _create_issue(self, symbol: str, category: str, status: str, reason: str, detected_at: datetime) -> None:
        self.data_quality_repository.create_issue(
            DataQualityIssue(
                symbol=symbol,
                data_category=category,
                severity="ERROR" if status == QUALITY_FAILED else "WARNING",
                status="OPEN",
                message=build_data_quality_message(status, data_category=category, reason=reason),
                detected_at=detected_at,
            )
        )

    def import_symbol(self, symbol: str, *, date_from: str, date_to: str) -> ImportRunSummary:
        normalized_symbol = self._normalize_symbol(symbol)
        if not normalized_symbol:
            raise ValueError("Stock import requires a symbol.")

        started_at = datetime.now(timezone.utc)
        import_run_id = f"stock_import_{normalized_symbol}_{started_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        summary = ImportRunSummary(
            import_run_id=import_run_id,
            provider="FMP",
            import_type="WATCHLIST_SYMBOL",
            started_at=started_at,
            symbols_requested=1,
        )
        self.import_run_repository.upsert_run(summary)

        raw_written = 0
        clean_written = 0
        try:
            profile_payload = self.fmp_client.fetch_company_profile(normalized_symbol)
            raw_written += 1
            self._write_raw(
                category="company_profile",
                symbol=normalized_symbol,
                params={"symbol": normalized_symbol},
                payload=profile_payload,
                fetched_at=started_at,
                status="SUCCESS" if profile_payload else "MISSING",
            )
            if profile_payload:
                self.company_repository.upsert_company(
                    normalize_company_profile_payload(profile_payload, symbol=normalized_symbol, fetched_at=started_at)
                )
                clean_written += 1
            else:
                self._create_issue(normalized_symbol, "company_profile", QUALITY_MISSING, "Provider returned no profile.", started_at)

            price_payload = self.fmp_client.fetch_historical_price_eod_full(normalized_symbol, date_from, date_to)
            raw_written += 1
            self._write_raw(
                category="historical_price",
                symbol=normalized_symbol,
                params={"symbol": normalized_symbol, "from": date_from, "to": date_to},
                payload=price_payload,
                fetched_at=started_at,
                status="SUCCESS" if price_payload else "MISSING",
            )
            price_rows = normalize_historical_price_payload(price_payload, symbol=normalized_symbol, fetched_at=started_at)
            clean_written += self.price_repository.upsert_prices(price_rows)
            if not price_rows:
                self._create_issue(normalized_symbol, "historical_price", QUALITY_MISSING, "Provider returned no price rows.", started_at)

            metric_payloads = [
                ("income_statement", self.fmp_client.fetch_income_statement(normalized_symbol), self.INCOME_METRICS),
                ("key_metrics", self.fmp_client.fetch_key_metrics(normalized_symbol), self.KEY_METRICS),
                ("ratios", self.fmp_client.fetch_ratios(normalized_symbol), self.RATIO_METRICS),
            ]
            metric_rows: list[dict[str, Any]] = []
            for category, payload, fields in metric_payloads:
                raw_written += 1
                self._write_raw(
                    category=category,
                    symbol=normalized_symbol,
                    params={"symbol": normalized_symbol},
                    payload=payload,
                    fetched_at=started_at,
                    status="SUCCESS" if payload else "MISSING",
                )
                metric_rows.extend(
                    normalize_fundamental_metric_payload(
                        payload,
                        symbol=normalized_symbol,
                        metric_fields=fields,
                        fetched_at=started_at,
                    )
                )
            clean_written += self.metrics_repository.upsert_metrics(metric_rows)
            if not metric_rows:
                self._create_issue(
                    normalized_symbol,
                    "financial_metrics",
                    QUALITY_MISSING,
                    "Provider returned no financial or valuation metrics.",
                    started_at,
                )

            summary.completed_at = datetime.now(timezone.utc)
            summary.status = "SUCCESS"
            summary.symbols_succeeded = 1
            summary.raw_responses_written = raw_written
            summary.clean_records_written = clean_written
            self.import_run_repository.upsert_run(summary)
            return summary
        except Exception as exc:
            summary.completed_at = datetime.now(timezone.utc)
            summary.status = "FAILED"
            summary.symbols_failed = 1
            summary.raw_responses_written = raw_written
            summary.clean_records_written = clean_written
            summary.error_message = str(exc)
            self.import_run_repository.upsert_run(summary)
            self._create_issue(normalized_symbol, "stock_import", QUALITY_FAILED, str(exc), started_at)
            return summary
