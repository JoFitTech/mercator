# Brownfield Migration Plan: Stock Analysis Dashboard

This document records the setup and repository-inventory phase for modernizing Mercator from an insider-trade explorer into a personal stock analysis, prediction, and preference dashboard.

## Scope Of This Phase

Completed in this phase:

- Repository inventory for current runtime, data, service, UI, and test surfaces.
- Legacy/new module classification for planned migration batches.
- Rename map for future work.
- Risk list for planned renames.
- Current test baseline attempt and blocker.
- Documentation of the brownfield migration plan.

Explicitly not performed in this phase:

- No file renames.
- No database schema changes.
- No removal or hiding of legacy insider-trade functionality.
- No prediction model implementation.
- No new stock-analysis runtime module placeholders.

## Repository Inventory

### Runtime And Navigation

- `streamlit_app.py` is the active Streamlit entry point.
- `src/app/navigation.py` owns header, sidebar, detail-page, and parent-page navigation state.
- Current top-level navigation remains `Dashboard`, `Trades`, `Unternehmen`, with sidebar entries for `Methodik`, `Einstellungen`, and `Admin`.
- Current detail routes remain `Trade-Detail` and `Unternehmens-Detail`.

### Data Providers

- `src/data_sources/fmp_client.py` contains the primary FMP integration.
- Existing FMP behavior includes insider-trading endpoints plus reusable company profile and historical price support.
- `src/data_sources/alpha_vantage_client.py` and `src/data_sources/polygon_client.py` are optional provider surfaces and should remain untouched until a provider fallback story needs them.
- `src/data_sources/trade_republic_universe_source.py` is reference-data ingestion, not broker integration.

### Storage

- `src/db/mongo_repository.py` contains `InsiderTradeMongoRepository`, `CompanyMongoRepository`, and app settings Mongo repositories.
- `src/db/schema.py` currently creates legacy tables including `companies`, `insider_trades`, `company_trade_stats`, `market_signal_cache`, app settings/state tables, and Trade Republic reference tables.
- `src/db/repositories/trade_repository.py` contains the active `InsiderTradeRepository` and `InsiderTradeMySqlRepository` for clean trade data.
- Reusable repository patterns already exist in `company_repository.py`, `market_signal_cache_repository.py`, `settings_repository.py`, `sync_state_repository.py`, and `api_usage_repository.py`.

### Services And Preprocessing

- `src/services/import_service.py` orchestrates insider-trade import, raw writes, normalization, profile enrichment, scoring, and clean MySQL writes.
- `src/preprocessing/cleaning.py`, `deduplication.py`, `normalization.py`, and `gate_evaluator.py` are currently insider-trade-shaped.
- `src/services/analysis_service.py`, `dashboard_service.py`, `scoring_service.py`, `buy_engine.py`, and `accumulation_service.py` power current trade dashboard, explorer, scoring, and detail workflows.
- `src/services/historical_market_data_service.py` is a reusable seed for future technical feature calculations.
- `src/services/security_normalization_service.py`, `company_profile_enrichment_service.py`, `api_usage_service.py`, and database status/startup services are reusable infrastructure.

### UI

- `src/ui/pages/dashboard_page.py`, `trades_page.py`, `trade_detail_page.py`, `companies_page.py`, `company_detail_page.py`, `methodology_page.py`, `settings_page.py`, and `admin_page.py` are current production pages.
- `src/ui/components/status_badges.py`, `tables.py`, `charts.py`, `filters.py`, `formatting.py`, `context_bar.py`, and `page_scaffold.py` are reusable UI infrastructure.
- Existing trade-specific labels and table helpers must remain until replacement watchlist and stock-detail pages pass tests.

### Tests

- Legacy behavior is covered by unit/integration tests such as `tests/test_trade_repository_filters.py`, `tests/test_gate_evaluator.py`, `tests/test_buy_engine.py`, `tests/test_accumulation.py`, `tests/test_import_service_raw_clean_sync.py`, and `tests/test_ui_page_regressions.py`.
- E2E coverage for current navigation and trade UI lives in `tests/e2e/test_navigation.py`, `tests/e2e/test_trade_detail.py`, `tests/e2e/test_explorer_filters.py`, and `tests/e2e/test_accumulation_toggle.py`.
- New setup-phase baseline guards live in `tests/test_stocklens_baseline.py`.

## Legacy/New Module Classification

| Classification | Paths | Migration handling |
|---|---|---|
| Preserve initially | `streamlit_app.py`, `src/app/navigation.py`, `src/config/settings.py`, `src/services/factory.py`, `src/app/bootstrap.py`, database target resolvers | Keep stable while new modules are added beside existing paths. |
| Legacy insider-trade runtime | `src/models/insider_trade.py`, `src/db/repositories/trade_repository.py`, `src/db/mysql_repository.py`, `src/services/import_service.py`, `src/services/analysis_service.py`, `src/services/dashboard_service.py`, `src/preprocessing/gate_evaluator.py`, `src/services/buy_engine.py`, `src/services/accumulation_service.py`, `src/ui/pages/trades_page.py`, `src/ui/pages/trade_detail_page.py` | Do not rename or delete first. Introduce stock-analysis replacements, then migrate callers and tests in batches. |
| Reusable with adaptation | `src/data_sources/fmp_client.py`, `src/db/mongo_repository.py`, `src/db/schema.py`, `src/db/repositories/company_repository.py`, `src/db/repositories/market_signal_cache_repository.py`, `src/services/historical_market_data_service.py`, `src/ui/components/status_badges.py`, `src/ui/components/tables.py`, `src/ui/components/charts.py` | Extend additively; keep legacy behavior covered by tests. |
| Reference-only / compatibility | `src/data_sources/trade_republic_universe_source.py`, `src/domain/trade_republic_universe.py`, `src/services/trade_republic_universe_service.py`, Trade Republic repository/UI/admin tab | Treat as availability/reference metadata only. Do not imply broker connectivity, live tradability, or order execution. |
| Planned new stock-analysis modules | `watchlist_repository.py`, `stock_price_repository.py`, `fundamental_metrics_repository.py`, `feature_repository.py`, `prediction_repository.py`, `preference_score_repository.py`, `stock_import_service.py`, `feature_engineering_service.py`, `prediction_model_service.py`, `backtest_service.py`, `preference_scoring_service.py`, `watchlist_page.py`, `stock_detail_page.py`, `model_evaluation_page.py` | Add in later phases only, after baseline and additive schema tasks are ready. |

## Rename Map

| Current insider-trade surface | Target stock-analysis surface | Batch | Required safeguards |
|---|---|---|---|
| `insider_trades` table | Legacy table plus new watchlist, price, feature, prediction, and score tables | Schema phase | Additive DDL first; keep legacy table and tests. |
| `company_trade_stats` table | `stock_analysis_summary` or service-level stock summary | Schema/UI phase | Build new summary path before dashboard switch. |
| `market_signal_cache` table | `technical_features` seed or compatibility source | Feature phase | Keep current consumers until feature repository exists. |
| `InsiderTradeMongoRepository` | `RawProviderResponseMongoRepository` | Import phase | Add generic repository while preserving old raw trade methods. |
| `InsiderTradeRepository` / `InsiderTradeMySqlRepository` | Split repositories for watchlist, prices, metrics, features, predictions, and scores | Schema through scoring phases | Split by responsibility; no one-to-one rename. |
| `src/models/insider_trade.py` | Stock, watchlist, feature, prediction, and preference models | Foundation phases | Add new model files; migrate imports intentionally. |
| `normalize_insider_trade` | Provider-specific stock normalization functions | Import phase | Keep insider normalization for legacy raw-to-clean sync. |
| `GateEvaluator` / gate statuses | Data-quality/readiness evaluator and statuses | Import/feature phases | Keep gate evaluator for legacy tests; map new statuses to visible text. |
| `buy_engine.py` | `preference_scoring_service.py` | Scoring phase | Remove buy/order/execution semantics from new path. |
| `AccumulationService` | Time-series feature aggregation or retire | Feature phase | Do not rename if behavior does not map to stock analysis. |
| `trades_page.py` | `watchlist_page.py` and stock list workflows | UI phase | Add new page and tests before navigation label changes. |
| `trade_detail_page.py` | `stock_detail_page.py` | UI phase | Preserve old detail route until stock detail route passes tests. |
| Navigation label `Trades` | `Watchlist` or `Stocks` | UI phase | Change only with E2E coverage and parent-detail routing updates. |
| Trade Republic fields | Reference availability metadata | Schema/UI phase | Update text to avoid broker/trading implication. |

## Rename Risks

- **Runtime routing breakage**: `streamlit_app.py`, `src/app/navigation.py`, and E2E helpers share string route names. Rename routes only with navigation and E2E updates in the same batch.
- **Schema/data loss**: `insider_trades`, `company_trade_stats`, and foreign keys are used by repository and dashboard code. Keep changes additive until stock-analysis tables and consumers are verified.
- **Raw/clean sync regression**: `ImportService` currently writes Mongo raw payloads, normalized MySQL records, profile status, and stats recomputation. New imports must preserve raw-before-clean ordering.
- **Semantic drift**: `buy_engine.py` and gate statuses contain action-oriented terms. New scoring must use preference/ranking language and explicit explanations.
- **Test blast radius**: Legacy tests assert SQL fragments, UI labels, and route names. Batch migrations must update tests only after replacement runtime paths exist.
- **Provider entitlement gaps**: FMP financial/valuation endpoints may return partial or unauthorized data. New code must store failed/partial raw responses and visible data-quality text.
- **Trade Republic confusion**: Existing reference metadata can be mistaken for broker integration. New UI/docs must state it is reference data only.
- **Performance regressions**: Dashboard and trade pages currently use aggregate query paths. Replacement summaries need similar aggregate access before switching UI defaults.

## Current Test Baseline

Baseline command requested by `quickstart.md`:

```bash
python -m pytest tests/test_service_factory.py tests/test_database_status_service.py tests/test_status_badges.py
```

Observed in this environment:

- `python` is not available in the shell.
- `python3` is available as Python 3.12.3.
- `python3 -m pytest tests/test_service_factory.py tests/test_database_status_service.py tests/test_status_badges.py` fails before collection because pytest is not installed in the system interpreter.
- No repository test failures were observed; the baseline is blocked by missing local test tooling.

The setup-phase baseline guard added in `tests/test_stocklens_baseline.py` is source-level and should run once the project test environment has pytest installed.

## Next Phase Entry Criteria

- Install/use the project Python environment with pytest available.
- Run the quickstart baseline plus `tests/test_stocklens_baseline.py`.
- Proceed to additive schema work only after baseline tests are executable.
- Keep all legacy insider-trade routes and modules available until replacement watchlist, import, feature, scoring, and UI paths are implemented and tested.
