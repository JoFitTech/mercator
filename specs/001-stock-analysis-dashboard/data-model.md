# Data Model: Personal Stock Analysis Dashboard

## MongoDB Collections

### raw_provider_responses

- `response_id`: stable hash or generated id.
- `provider`: `fmp`, `alpha_vantage`, `polygon`, or other configured provider.
- `category`: `company_profile`, `historical_price`, `financial_metric`, `valuation_metric`, `model_input_snapshot`, etc.
- `symbol`: normalized symbol when available.
- `request_params`: sanitized request parameters without secrets.
- `request_hash`: deterministic hash for dedupe/idempotency.
- `status`: `SUCCESS`, `PARTIAL`, `FAILED`, `RATE_LIMITED`, `UNAUTHORIZED`, `STALE`, `UNKNOWN`.
- `payload`: raw provider response.
- `error_message`: optional text.
- `fetched_at`: UTC timestamp.
- `source_url`: endpoint path or sanitized source reference.

Existing `insider_trades_raw` remains legacy until the old import path is retired.

## MySQL Tables

### watchlist_items

- `id`
- `symbol`
- `company_key`
- `display_name`
- `notes`
- `priority`
- `active`
- `resolution_status`
- `created_at`
- `updated_at`

### companies

Use the existing `companies` table where compatible. Add columns only if needed for stock-analysis profile freshness and symbol resolution. Avoid a duplicate company table unless the existing table cannot support the clean stock workflow.

### stock_price_history

- `symbol`
- `price_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `adjusted_close`
- `volume`
- `provider`
- `source_refreshed_at`
- `quality_status`
- Unique key: `symbol`, `price_date`, `provider`.

### fundamental_metrics

- `symbol`
- `metric_name`
- `period_type`
- `period_end`
- `value`
- `unit`
- `provider`
- `source_refreshed_at`
- `quality_status`
- Unique key: `symbol`, `metric_name`, `period_type`, `period_end`, `provider`.

### technical_features

- `symbol`
- `feature_date`
- `momentum_1m`
- `momentum_3m`
- `momentum_6m`
- `sma_20`
- `sma_50`
- `sma_200`
- `volatility_20d`
- `max_drawdown_1y`
- `volume_trend_20d`
- `feature_status`
- `unavailable_reason`
- `input_refreshed_at`
- Unique key: `symbol`, `feature_date`.

### fundamental_features

- `symbol`
- `feature_period`
- `revenue_growth`
- `earnings_growth`
- `gross_margin`
- `operating_margin`
- `net_margin`
- `valuation_ratio`
- `debt_to_equity`
- `market_cap`
- `feature_status`
- `unavailable_reason`
- `input_refreshed_at`
- Unique key: `symbol`, `feature_period`.

### model_runs

- `model_run_id`
- `model_name`
- `model_type`
- `model_version`
- `target_type`
- `horizon_days`
- `training_started_at`
- `training_completed_at`
- `training_window_start`
- `training_window_end`
- `feature_set_version`
- `status`
- `quality_summary_json`
- `error_message`

### prediction_results

- `prediction_id`
- `model_run_id`
- `symbol`
- `prediction_as_of`
- `horizon_days`
- `target_type`
- `direction`
- `return_class`
- `expected_return`
- `confidence`
- `uncertainty`
- `model_quality_score`
- `input_refreshed_at`
- `created_at`

### backtest_results

- `backtest_id`
- `model_run_id`
- `horizon_days`
- `evaluation_start`
- `evaluation_end`
- `sample_size`
- `accuracy`
- `precision_score`
- `recall_score`
- `mean_absolute_error`
- `calibration_summary_json`
- `caveats_text`
- `created_at`

### preference_scores

- `preference_score_id`
- `symbol`
- `score_as_of`
- `preference_score`
- `rank_position`
- `fundamental_component`
- `technical_component`
- `risk_component`
- `prediction_component`
- `confidence_component`
- `confidence`
- `uncertainty`
- `explanation_positive`
- `explanation_negative`
- `data_quality_summary`
- `created_at`

### import_runs

- `import_run_id`
- `provider`
- `import_type`
- `started_at`
- `completed_at`
- `status`
- `symbols_requested`
- `symbols_succeeded`
- `symbols_failed`
- `raw_responses_written`
- `clean_records_written`
- `error_message`

### data_quality_issues

- `issue_id`
- `symbol`
- `data_category`
- `severity`
- `status`
- `message`
- `detected_at`
- `source_refreshed_at`
- `resolved_at`

## Legacy Tables

- `insider_trades`: keep intact for legacy UI/import path until replacement is complete.
- `company_trade_stats`: keep intact until `stock_analysis_summary` replaces dashboard needs.
- `market_signal_cache`: can seed `technical_features`; do not drop until consumers migrate.
- Trade Republic reference tables: keep only as reference metadata if still useful; never represent broker connectivity.
