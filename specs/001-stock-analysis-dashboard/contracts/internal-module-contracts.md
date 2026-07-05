# Internal Module Contracts

These contracts describe internal Python module boundaries for the brownfield implementation. They are not HTTP API contracts.

## RawProviderResponseMongoRepository

- `upsert_response(response: RawProviderResponse) -> str`
- `list_responses(symbol: str, category: str | None = None, limit: int = 100) -> list[dict]`
- `count_by_category() -> dict[str, int]`

Rules:

- Must never store API keys or secrets.
- Must store raw payloads before clean normalization writes.
- Must preserve failed and partial responses with status text.

## WatchlistRepository

- `upsert_item(item: WatchlistItem) -> None`
- `list_items(active_only: bool = True) -> list[dict]`
- `delete_item(symbol: str) -> None`
- `get_item(symbol: str) -> dict | None`

Rules:

- Must keep unresolved symbols visible with status text.
- Must not trigger provider calls directly.

## StockImportService

- `import_symbol(symbol: str, categories: list[str]) -> ImportRunSummary`
- `import_watchlist(categories: list[str]) -> ImportRunSummary`

Rules:

- Must write raw Mongo responses first.
- Must write clean MySQL records only after normalization.
- Must create data-quality issues for missing, stale, incomplete, failed, or partial data.

## FeatureEngineeringService

- `calculate_for_symbol(symbol: str, as_of: date) -> FeatureSummary`
- `calculate_for_watchlist(as_of: date) -> list[FeatureSummary]`

Rules:

- Must use Pandas for time-series calculations.
- Must store unavailable reasons when inputs are insufficient.

## PredictionModelService

- `train_model(model_name: str, horizon_days: int, target_type: str) -> ModelRun`
- `predict_watchlist(model_run_id: str) -> list[PredictionResult]`

Rules:

- Must include confidence, uncertainty, model version, model quality, horizon, and data freshness.
- Must not emit trade decisions.

## BacktestService

- `backtest_model(model_run_id: str) -> BacktestResult`

Rules:

- Must record evaluation window, sample size, quality metrics, and caveats.

## PreferenceScoringService

- `score_symbol(symbol: str, as_of: date) -> PreferenceScore`
- `rank_watchlist(as_of: date) -> list[PreferenceScore]`

Rules:

- Must include fundamentals, technicals, risk, prediction output, and confidence components.
- Must produce visible explanation text for preferred and deprioritized stocks.
- Must not use broker, order, execution, live-trading, or final-decision semantics.
