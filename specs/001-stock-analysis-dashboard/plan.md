# Implementation Plan: Personal Stock Analysis Dashboard

**Branch**: `feature/stocklens-brownfield` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-stock-analysis-dashboard/spec.md`

## Summary

Modernize the existing Mercator Streamlit application in place from an insider-trade-specific explorer into a personal stock analysis, prediction, and preference dashboard. The implementation keeps the current Python, Pandas, Streamlit, MongoDB, MySQL, requests, python-dotenv, and pytest stack; adds stock-analysis data structures beside the legacy insider-trade path; then migrates UI, services, repositories, and labels in tested phases without blind global renames.

## Technical Context

**Language/Version**: Python 3.x as currently used by the repository; Docker/local docs reference Python 3.11 for development.

**Primary Dependencies**: Streamlit 1.56.0, Pandas 3.0.2, requests 2.33.1, python-dotenv 1.2.2, pymongo 4.16.0, mysql-connector-python 9.6.0, pytest 9.0.2. Optional existing provider clients remain Alpha Vantage and Polygon.

**Storage**: MongoDB remains raw API response storage. MySQL remains normalized relational storage for watchlists, companies, price history, metrics, features, model runs, predictions, preference scores, backtest results, import runs, and data quality issues.

**Testing**: pytest for unit/integration coverage; existing Playwright E2E tests remain available for Streamlit UI regressions.

**Target Platform**: Existing local/Docker Streamlit application with MySQL and MongoDB targets selected through environment variables.

**Project Type**: Brownfield single Python Streamlit application. No new repository, no greenfield frontend, no broker service.

**Performance Goals**: Watchlist operations should stay interactive for personal-scale lists; data imports should avoid duplicate provider calls through existing API usage tracking, raw response caching, and freshness checks.

**Constraints**: Preserve runnable state after every implementation phase. Keep secrets in environment variables or existing Streamlit secret paths. Do not connect to brokers, execute trades, or present unexplained recommendations.

**Scale/Scope**: Personal dashboard for tens to low hundreds of watched symbols, daily historical prices, selected fundamentals/valuation metrics, and periodic model refreshes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Brownfield preservation**: PASS. Work stays in the current repository and introduces stock-analysis modules beside existing insider-trade modules before replacing navigation or deleting legacy paths. Existing `streamlit_app.py`, `src/app/`, `src/ui/pages/`, `src/services/`, `src/db/`, and `tests/` remain runnable through each phase.
- **No greenfield fork**: PASS. No new app, repository, frontend stack, or product stack is planned. The implementation uses the current Python/Streamlit app.
- **Data-store separation**: PASS. MongoDB stores raw provider responses and import payload metadata; MySQL stores normalized clean entities, features, model outputs, scores, and UI query models.
- **Rename safety**: PASS. This plan includes a repository-analysis-backed rename map and requires scoped rename batches with imports, tests, UI labels, docs, and database compatibility updated together.
- **Prediction transparency**: PASS. Prediction outputs include horizon, target, model version, confidence, uncertainty, model quality, evaluation window, sample size, and input data freshness.
- **Visible data quality**: PASS. Missing, stale, incomplete, failed, low-quality, and unknown data states are first-class MySQL records and must appear as text in Streamlit pages.
- **No trade execution**: PASS. Broker integration, automatic order execution, live trading, and final trading decisions are explicitly out of scope.
- **Streamlit-first UI**: PASS. The first UI remains the current Streamlit app and navigation system.
- **Secrets handling**: PASS. Existing environment-variable and Streamlit secret loading in `src/config/settings.py` remains the configuration path for API keys and database credentials.

## Repository Inventory

### Existing Paths To Preserve Initially

```text
streamlit_app.py
src/app/
src/config/settings.py
src/data_sources/fmp_client.py
src/db/
src/db/repositories/
src/models/
src/preprocessing/
src/services/
src/ui/components/
src/ui/pages/
tests/
tests/e2e/
```

### Current Insider-Trade-Specific Paths

```text
src/models/insider_trade.py
src/db/repositories/trade_repository.py
src/preprocessing/gate_evaluator.py
src/services/import_service.py
src/services/analysis_service.py
src/services/dashboard_service.py
src/services/accumulation_service.py
src/services/buy_engine.py
src/ui/pages/trades_page.py
src/ui/pages/trade_detail_page.py
tests/test_buy_engine.py
tests/test_gate_evaluator.py
tests/test_trade_repository_filters.py
tests/test_accumulation.py
tests/e2e/test_trade_detail.py
```

### Existing Reusable Capabilities

- `src/data_sources/fmp_client.py`: already supports company profile and historical EOD price endpoints.
- `src/services/historical_market_data_service.py`: already derives SMA, momentum, volume, and liquidity state from historical prices.
- `src/db/mongo_repository.py`: already demonstrates raw Mongo upserts and company raw/profile document storage.
- `src/db/schema.py` and `src/db/mysql_client.py`: already initialize and migrate MySQL schema.
- `src/db/repositories/company_repository.py`, `market_signal_cache_repository.py`, `settings_repository.py`, `sync_state_repository.py`: reusable repository patterns.
- `src/ui/components/status_badges.py`, `tables.py`, `charts.py`, `page_scaffold.py`: reusable UI building blocks.
- Existing pytest suite: repository, import, degraded-mode, settings, UI regression, and status badge tests.

## Rename And Separation Map

Renames are staged. The first implementation adds stock-analysis modules and adapters; later phases rename UI labels and retire legacy insider-trade paths only after tests pass.

| Legacy concept/path | New concept/path | Phase | Rule |
|---|---|---:|---|
| `insider_trades` MySQL table | `legacy_insider_trades` marker/comment; new `stock_*` tables | 3 | Do not destructively rename first. Add new tables and optionally mark legacy tables in docs/admin. |
| `InsiderTradeMongoRepository` | `RawProviderResponseMongoRepository` | 4 | Add generic repository first; keep old class for existing imports until legacy import path is isolated. |
| `InsiderTradeMySqlRepository` | `WatchlistRepository`, `PriceHistoryRepository`, `FeatureRepository`, `PredictionRepository` | 3-7 | Split by responsibility. Do not carry trade-shaped API forward. |
| `src/models/insider_trade.py` | stock-analysis models under `src/models/stock_analysis.py` or separate files | 3 | Add new models first. Move imports only when call sites are migrated. |
| `gate_evaluator.py` | `data_quality_evaluator.py` | 4-5 | Convert gate semantics to readiness/data-quality states. Keep old gate evaluator for legacy trade import tests. |
| `buy_engine.py` | `preference_scoring_service.py` | 7 | Remove buy/execution terms; emit preference score, components, confidence, and explanation. |
| `accumulation_service.py` | time-series feature aggregation services | 5 | Retire for stock workflow; do not rename if behavior does not map. |
| `trades_page.py` | `watchlist_page.py` / `stocks_page.py` | 8 | Add new page, wire navigation, then remove/legacy-hide old page. |
| `trade_detail_page.py` | `stock_detail_page.py` | 8 | Add new detail page with profile, price, features, predictions, score, and data-quality text. |
| UI label "Trades" | "Watchlist" or "Stocks" | 8 | Change labels only with page routing and E2E tests. |
| `company_trade_stats` | `stock_analysis_summary` | 3/8 | Add new summary table/view; leave old stats for legacy pages until replaced. |
| Trade Republic universe broker-like fields | reference/availability metadata only | 3/8 | Text must state it is not live tradability and not broker integration. |

## Project Structure

### Documentation (this feature)

```text
specs/001-stock-analysis-dashboard/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── internal-module-contracts.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── app/
│   └── navigation.py
├── config/
│   └── settings.py
├── data_sources/
│   ├── fmp_client.py
│   ├── alpha_vantage_client.py
│   └── polygon_client.py
├── db/
│   ├── schema.py
│   ├── mysql_client.py
│   ├── mongo_repository.py
│   └── repositories/
│       ├── watchlist_repository.py
│       ├── stock_price_repository.py
│       ├── fundamental_metrics_repository.py
│       ├── feature_repository.py
│       ├── prediction_repository.py
│       ├── preference_score_repository.py
│       ├── import_run_repository.py
│       └── data_quality_repository.py
├── models/
│   ├── stock.py
│   ├── watchlist.py
│   ├── features.py
│   ├── prediction.py
│   └── preference.py
├── preprocessing/
│   └── data_quality_evaluator.py
├── services/
│   ├── stock_import_service.py
│   ├── feature_engineering_service.py
│   ├── prediction_model_service.py
│   ├── backtest_service.py
│   ├── preference_scoring_service.py
│   └── stock_analysis_service.py
└── ui/
    └── pages/
        ├── dashboard_page.py
        ├── watchlist_page.py
        ├── stock_detail_page.py
        ├── model_evaluation_page.py
        ├── methodology_page.py
        └── admin_page.py

tests/
├── test_watchlist_repository.py
├── test_stock_import_service.py
├── test_data_quality_evaluator.py
├── test_feature_engineering_service.py
├── test_prediction_model_service.py
├── test_backtest_service.py
├── test_preference_scoring_service.py
├── test_stock_analysis_pages.py
└── e2e/
    ├── test_watchlist_page.py
    ├── test_stock_detail_page.py
    └── test_model_evaluation_page.py
```

**Structure Decision**: Single existing Python/Streamlit application. Add modular stock-analysis repositories, services, models, and pages beside legacy modules, then migrate routing and remove/mark legacy paths in later phases.

## Database Design Direction

### MongoDB Collections

- `raw_provider_responses`: generic raw payloads keyed by provider, endpoint/category, request hash, symbol, fetched_at, status, response payload, and error metadata.
- Existing `insider_trades_raw`: kept as legacy until old import path is removed or archived.
- Existing `companies`: either retained for raw company/profile documents or gradually replaced by `raw_provider_responses` category values for profile payloads.

### MySQL Tables To Add

- `watchlist_items`
- `stock_companies` or compatible extension of existing `companies`
- `stock_price_history`
- `fundamental_metrics`
- `technical_features`
- `fundamental_features`
- `model_runs`
- `prediction_results`
- `preference_scores`
- `backtest_results`
- `import_runs`
- `data_quality_issues`
- `stock_analysis_summary`

### Legacy Tables

- `insider_trades`, `company_trade_stats`, and trade-specific indexes stay intact until the stock-analysis UI and repositories are verified.
- Admin/methodology documentation should mark these as legacy insider-trade artifacts once new stock-analysis paths are active.
- Migration from legacy insider-trade data is optional and only needed if a future feature uses historical insider activity as one stock-analysis signal.

## Implementation Phases

### Phase 1: Repository Inventory And Rename Map

- Confirm all legacy insider-trade import, repository, service, and UI call sites.
- Finalize rename map with exact files, tests, and database objects.
- Add tests that protect the existing app startup, current navigation, and legacy import service before structural changes.
- Output: checked-in inventory notes in `research.md` and this plan's rename map.

### Phase 2: Spec Kit Artifacts

- Maintain `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and internal contracts.
- Keep constitution checks current after data-model and architecture decisions.
- Output: reviewed artifacts ready for `speckit-tasks`.

### Phase 3: Database Schema Redesign

- Add MySQL DDL for watchlists, stock companies/company extensions, price history, fundamental metrics, features, model runs, predictions, preference scores, backtests, import runs, and data quality issues.
- Add repository classes with focused tests before wiring services.
- Add generic Mongo raw response repository while preserving `InsiderTradeMongoRepository`.
- Mark old insider-trade tables as legacy in docs/admin; do not destructively migrate.
- Verification: schema initialization tests and repository CRUD/upsert tests.

### Phase 4: Data Import Refactor

- Add watchlist-driven `StockImportService`.
- Reuse `FmpClient` profile and historical EOD methods; add financial/valuation endpoint methods only in scoped client changes with tests.
- Store every provider payload in MongoDB before normalization.
- Normalize clean profile, price, financial, and valuation records into MySQL.
- Record `import_runs` and `data_quality_issues` for partial, stale, failed, or missing data.
- Verification: mocked provider tests for success, partial data, rate-limit/error, and raw-to-clean sync.

### Phase 5: Feature Engineering

- Expand price-derived feature calculations from `HistoricalMarketDataService` into `FeatureEngineeringService`.
- Calculate momentum, moving averages, volatility, drawdown, and volume trends with Pandas.
- Calculate revenue growth, earnings growth, margins, valuation ratios, debt metrics, and market capitalization where metrics exist.
- Store unavailable reasons and freshness status with features.
- Verification: deterministic Pandas tests using fixed fixtures and missing-data cases.

### Phase 6: Prediction Model Layer

- Add baseline model, such as simple momentum/majority/naive return classifier.
- Add advanced model using available accepted dependencies or a dependency decision captured before implementation.
- Define horizons, targets, model versions, training windows, and feature set versions.
- Add backtesting against historical outcomes and store model quality metrics.
- Verification: model tests with fixed small datasets, insufficient-data behavior, and backtest metric calculations.

### Phase 7: Preference Scoring

- Add `PreferenceScoringService` to combine fundamental, technical, risk, prediction, and confidence components.
- Ensure outputs include component weights, score, rank, confidence, explanation text, and data-quality warnings.
- Replace buy/execution wording from new paths.
- Verification: unit tests for ranking order, explanation generation, missing-data penalties, and no broker/trade language.

### Phase 8: Streamlit UI Refactor

- Add watchlist page, stock detail page, and model evaluation page.
- Refactor dashboard to stock-analysis KPIs and ranking overview after repositories/services exist.
- Update navigation labels from "Trades" to "Watchlist" or "Stocks" only when new page tests pass.
- Keep methodology and admin pages explicit about data freshness, model quality, no broker integration, and manual trading outside the app.
- Verification: UI regression tests and E2E smoke/navigation tests.

### Phase 9: Tests And Documentation

- Expand pytest coverage for repositories, import flows, feature engineering, prediction, backtesting, preference scoring, and UI text states.
- Update README, methodology page, database diagrams, and project report diagrams after behavior changes.
- Remove or archive legacy insider-trade docs only after the new stock-analysis workflow is complete.
- Verification: full pytest suite where local dependencies allow; targeted E2E smoke for Streamlit navigation.

## Risk Controls

- Add tests before database or import refactors.
- Avoid global replacement commands; use scoped edits by module and test group.
- Keep old imports and compatibility classes until the replacement path is wired and verified.
- Make database changes additive first.
- Do not start broker, order, or live-trading abstractions.
- Surface missing/stale/failed states in text on every affected page.

## Complexity Tracking

No constitution violations are planned. The system is broad, but the complexity is required by the requested product scope and is contained by phased additive implementation, repository boundaries, and tests before risky refactors.
