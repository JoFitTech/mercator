# Tasks: Personal Stock Analysis Dashboard

**Input**: Design documents from `/specs/001-stock-analysis-dashboard/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/internal-module-contracts.md`, `.specify/memory/constitution.md`

**Tests**: Included because the feature specification defines mandatory independent tests and `quickstart.md` defines phase validation commands.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as an independent increment after shared foundations are complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture current behavior, protect the brownfield app, and prepare additive stock-analysis modules without renaming legacy paths.

- [X] T001 Document the scoped legacy-to-stock rename inventory in `specs/001-stock-analysis-dashboard/research.md`
- [X] T002 Add baseline startup and navigation regression tests for the current app in `tests/test_stocklens_baseline.py`
- [ ] T003 [P] Add stock-analysis package exports without changing legacy imports in `src/models/__init__.py`
- [ ] T004 [P] Add stock-analysis repository module placeholders in `src/db/repositories/__init__.py`
- [ ] T005 [P] Add stock-analysis service module placeholders in `src/services/__init__.py`
- [ ] T006 Run baseline validation command from quickstart in `tests/test_service_factory.py`, `tests/test_database_status_service.py`, and `tests/test_status_badges.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared data structures, schema, raw storage, and data-quality infrastructure required by all user stories.

**CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T007 Add stock-analysis MySQL DDL for `watchlist_items`, `stock_price_history`, `fundamental_metrics`, `technical_features`, `fundamental_features`, `model_runs`, `prediction_results`, `backtest_results`, `preference_scores`, `import_runs`, and `data_quality_issues` in `src/db/schema.py`
- [ ] T008 Add schema migration coverage for additive stock-analysis tables and preserved legacy tables in `tests/test_schema.py`
- [ ] T009 [P] Create raw provider response and import run models in `src/models/stock.py`
- [ ] T010 [P] Create watchlist and data-quality models in `src/models/watchlist.py`
- [ ] T011 [P] Create feature models in `src/models/features.py`
- [ ] T012 [P] Create prediction and backtest models in `src/models/prediction.py`
- [ ] T013 [P] Create preference score models in `src/models/preference.py`
- [ ] T014 Implement `RawProviderResponseMongoRepository` while preserving existing insider raw methods in `src/db/mongo_repository.py`
- [ ] T015 [P] Implement `ImportRunRepository` in `src/db/repositories/import_run_repository.py`
- [ ] T016 [P] Implement `DataQualityRepository` in `src/db/repositories/data_quality_repository.py`
- [ ] T017 Implement data-quality status mapping and visible-message helpers in `src/preprocessing/data_quality_evaluator.py`
- [ ] T018 Add repository and evaluator foundation tests in `tests/test_data_quality_repository.py` and `tests/test_data_quality_evaluator.py`
- [ ] T019 Verify additive schema initialization from quickstart in `tests/test_init_mysql_schema.py` and `tests/test_schema.py`

**Checkpoint**: Foundation ready; story implementation can now proceed in priority order or in parallel where dependencies allow.

---

## Phase 3: User Story 1 - Maintain A Manual Stock Watchlist (Priority: P1) MVP

**Goal**: A user can add, edit, remove, reload, and review manually selected stocks with persistent metadata and explicit data status text.

**Independent Test**: Add at least three symbols to the watchlist, refresh Streamlit, and confirm symbols, names, notes, priority, active state, resolution status, and freshness/status text remain visible.

### Tests for User Story 1

- [ ] T020 [P] [US1] Add repository tests for add/edit/remove/list unresolved watchlist items in `tests/test_watchlist_repository.py`
- [ ] T021 [P] [US1] Add service tests for watchlist metadata persistence and status summaries in `tests/test_watchlist_service.py`
- [ ] T022 [P] [US1] Add Streamlit watchlist page tests for visible status text and reload behavior in `tests/test_stock_analysis_pages.py`
- [ ] T023 [P] [US1] Add E2E watchlist workflow smoke test for three symbols in `tests/e2e/test_watchlist_page.py`

### Implementation for User Story 1

- [ ] T024 [US1] Implement `WatchlistRepository` CRUD and unresolved-symbol persistence in `src/db/repositories/watchlist_repository.py`
- [ ] T025 [US1] Implement watchlist workflow service in `src/services/watchlist_service.py`
- [ ] T026 [US1] Implement watchlist status summary queries in `src/services/stock_analysis_service.py`
- [ ] T027 [US1] Add watchlist page with add/edit/remove controls and explicit profile, price, financial, prediction, and preference status text in `src/ui/pages/watchlist_page.py`
- [ ] T028 [US1] Add watchlist navigation entry while preserving legacy Trades routing in `src/app/navigation.py`
- [ ] T029 [US1] Add watchlist table/status rendering helpers in `src/ui/components/tables.py` and `src/ui/components/status_badges.py`
- [ ] T030 [US1] Document MVP watchlist validation in `specs/001-stock-analysis-dashboard/quickstart.md`

**Checkpoint**: User Story 1 is independently functional and is the suggested MVP scope.

---

## Phase 4: User Story 2 - Import And Normalize Stock Data (Priority: P1)

**Goal**: Watchlist symbols can import company profiles, daily prices, financial metrics, and valuation metrics with raw MongoDB payloads and normalized MySQL records.

**Independent Test**: Import one watchlist symbol and verify raw API payloads exist in MongoDB while normalized profile, price, financial, valuation, import-run, and data-quality records exist in MySQL.

### Tests for User Story 2

- [ ] T031 [P] [US2] Add raw provider response repository tests for success, partial, failed, and rate-limited payloads in `tests/test_mongo_repository.py`
- [ ] T032 [P] [US2] Add FMP stock profile, historical price, financial metric, and valuation client tests in `tests/test_fmp_stock_data_client.py`
- [ ] T033 [P] [US2] Add stock import service tests for raw-before-clean writes and partial provider data in `tests/test_stock_import_service.py`
- [ ] T034 [P] [US2] Add price and fundamental repository tests in `tests/test_stock_data_repositories.py`

### Implementation for User Story 2

- [ ] T035 [P] [US2] Add company profile, financial metric, and valuation endpoint methods in `src/data_sources/fmp_client.py`
- [ ] T036 [P] [US2] Implement stock price history repository in `src/db/repositories/stock_price_repository.py`
- [ ] T037 [P] [US2] Implement fundamental metrics repository in `src/db/repositories/fundamental_metrics_repository.py`
- [ ] T038 [US2] Extend company repository for stock profile freshness and symbol resolution in `src/db/repositories/company_repository.py`
- [ ] T039 [US2] Implement provider normalization for profiles, daily prices, financial metrics, and valuation metrics in `src/preprocessing/normalization.py`
- [ ] T040 [US2] Implement watchlist-driven stock import orchestration in `src/services/stock_import_service.py`
- [ ] T041 [US2] Wire import run and data-quality issue creation into `src/services/stock_import_service.py`
- [ ] T042 [US2] Add admin import controls and status text for stock imports in `src/ui/pages/admin_page.py`
- [ ] T043 [US2] Run import phase validation from quickstart in `tests/test_stock_import_service.py` and `tests/test_mongo_repository.py`

**Checkpoint**: User Story 2 can be validated independently with mocked providers and database repositories.

---

## Phase 5: User Story 3 - Calculate Technical And Fundamental Features (Priority: P1)

**Goal**: Technical and fundamental feature sets are calculated from clean data with source freshness and explicit unavailable reasons.

**Independent Test**: Load a symbol with sufficient price and financial history and verify calculated feature values plus explicit unavailable reasons for missing or short inputs.

### Tests for User Story 3

- [ ] T044 [P] [US3] Add deterministic technical feature tests for momentum, moving averages, volatility, drawdown, and volume trends in `tests/test_feature_engineering_service.py`
- [ ] T045 [P] [US3] Add deterministic fundamental feature tests for growth, margins, valuation, debt, and market capitalization in `tests/test_feature_engineering_service.py`
- [ ] T046 [P] [US3] Add feature repository tests for freshness, unavailable reasons, and idempotent upserts in `tests/test_feature_repositories.py`

### Implementation for User Story 3

- [ ] T047 [P] [US3] Implement technical feature repository in `src/db/repositories/feature_repository.py`
- [ ] T048 [P] [US3] Implement fundamental feature repository in `src/db/repositories/feature_repository.py`
- [ ] T049 [US3] Expand existing price-derived calculations for stock features in `src/services/historical_market_data_service.py`
- [ ] T050 [US3] Implement `FeatureEngineeringService.calculate_for_symbol` and `calculate_for_watchlist` in `src/services/feature_engineering_service.py`
- [ ] T051 [US3] Store explicit feature unavailable reasons through `DataQualityRepository` in `src/services/feature_engineering_service.py`
- [ ] T052 [US3] Show feature values, freshness, and unavailable reason text in `src/ui/pages/stock_detail_page.py`
- [ ] T053 [US3] Run feature phase validation from quickstart in `tests/test_feature_engineering_service.py` and `tests/test_data_quality_evaluator.py`

**Checkpoint**: User Story 3 can be validated independently for symbols with sufficient and insufficient clean inputs.

---

## Phase 6: User Story 4 - Train, Backtest, And Compare Prediction Models (Priority: P2)

**Goal**: At least one baseline model and one advanced model can generate transparent predictions and backtest metrics for defined horizons.

**Independent Test**: Train or refresh models for a fixed horizon, generate predictions for watchlist stocks, and review model quality metrics for each model.

### Tests for User Story 4

- [ ] T054 [P] [US4] Add prediction repository tests for model runs, prediction results, transparency fields, and obsolete model versions in `tests/test_prediction_repositories.py`
- [ ] T055 [P] [US4] Add baseline and advanced model tests with insufficient-data behavior in `tests/test_prediction_model_service.py`
- [ ] T056 [P] [US4] Add backtest metric and caveat tests in `tests/test_backtest_service.py`
- [ ] T057 [P] [US4] Add model evaluation page tests for quality metrics and freshness text in `tests/test_stock_analysis_pages.py`

### Implementation for User Story 4

- [ ] T058 [P] [US4] Implement prediction repository for `model_runs` and `prediction_results` in `src/db/repositories/prediction_repository.py`
- [ ] T059 [P] [US4] Implement backtest repository for `backtest_results` in `src/db/repositories/backtest_repository.py`
- [ ] T060 [US4] Implement baseline model training and prediction for one initial horizon in `src/services/prediction_model_service.py`
- [ ] T061 [US4] Implement advanced model training and prediction using approved existing or explicitly added dependencies in `src/services/prediction_model_service.py`
- [ ] T062 [US4] Implement backtest evaluation window, sample size, quality metrics, and caveats in `src/services/backtest_service.py`
- [ ] T063 [US4] Show model evaluation, prediction confidence, uncertainty, model version, model quality, and freshness in `src/ui/pages/model_evaluation_page.py`
- [ ] T064 [US4] Run model validation from quickstart in `tests/test_prediction_model_service.py`, `tests/test_backtest_service.py`, and `tests/test_preference_scoring_service.py`

**Checkpoint**: User Story 4 can be validated independently after features exist.

---

## Phase 7: User Story 5 - Rank Stocks With Transparent Preference Scores (Priority: P2)

**Goal**: Watchlist stocks are ranked by transparent preference score with component contributions, confidence, warnings, and plain-language explanations.

**Independent Test**: Rank a watchlist and verify every row has component scores, explanation text, uncertainty/confidence, and data-quality warnings.

### Tests for User Story 5

- [ ] T065 [P] [US5] Add preference repository tests for score components, rankings, warnings, and explanations in `tests/test_preference_score_repository.py`
- [ ] T066 [P] [US5] Add preference scoring tests for ranking order, missing-data penalties, conflicting signals, and no trade-execution wording in `tests/test_preference_scoring_service.py`
- [ ] T067 [P] [US5] Add ranking UI tests for visible component and warning text in `tests/test_stock_analysis_pages.py`

### Implementation for User Story 5

- [ ] T068 [P] [US5] Implement preference score repository in `src/db/repositories/preference_score_repository.py`
- [ ] T069 [US5] Implement component scoring for fundamentals, technicals, risk, prediction output, and confidence in `src/services/preference_scoring_service.py`
- [ ] T070 [US5] Implement explanation generation and data-quality warning summaries in `src/services/preference_scoring_service.py`
- [ ] T071 [US5] Integrate ranking summaries into dashboard query service in `src/services/dashboard_service.py`
- [ ] T072 [US5] Show ranked watchlist rows with component scores, explanations, confidence, uncertainty, and data-quality text in `src/ui/pages/dashboard_page.py`
- [ ] T073 [US5] Replace buy/execution wording in new stock-analysis paths with preference/ranking terminology in `src/services/preference_scoring_service.py` and `src/ui/pages/dashboard_page.py`

**Checkpoint**: User Story 5 can be validated independently after predictions or explicit missing-prediction warnings exist.

---

## Phase 8: User Story 6 - Navigate Stock Analysis Pages (Priority: P3)

**Goal**: The Streamlit workflow exposes overview, watchlist, stock detail, model evaluation, methodology, and admin pages with explicit data-quality and no-trade-execution text.

**Independent Test**: Open each page in Streamlit and confirm data status, freshness, explanation text, and manual-trading boundary are visible without relying on color alone.

### Tests for User Story 6

- [ ] T074 [P] [US6] Add navigation tests for overview, watchlist, stock detail, model evaluation, methodology, and admin routes in `tests/e2e/test_navigation.py`
- [ ] T075 [P] [US6] Add stock detail E2E test for profile, price, features, predictions, preference, and missing/stale/failed text in `tests/e2e/test_stock_detail_page.py`
- [ ] T076 [P] [US6] Add model evaluation E2E test for metric definitions and data freshness text in `tests/e2e/test_model_evaluation_page.py`
- [ ] T077 [P] [US6] Add methodology/admin page tests for no broker integration and manual trading boundary text in `tests/test_stock_analysis_pages.py`

### Implementation for User Story 6

- [ ] T078 [US6] Complete stock detail page sections for profile, price summaries, features, predictions, preference score, explanations, and status text in `src/ui/pages/stock_detail_page.py`
- [ ] T079 [US6] Refactor overview dashboard to stock-analysis KPIs and preference ranking summaries in `src/ui/pages/dashboard_page.py`
- [ ] T080 [US6] Update methodology page with prediction/scoring method text and no broker/no trade execution boundary in `src/ui/pages/methodology_page.py`
- [ ] T081 [US6] Update admin page with stock import, data-quality, model refresh, and legacy artifact status sections in `src/ui/pages/admin_page.py`
- [ ] T082 [US6] Update navigation labels from legacy Trades-first flow to stock-analysis pages after new page tests pass in `src/app/navigation.py`
- [ ] T083 [US6] Add shared text-first data-quality components for missing, stale, incomplete, low-quality, failed, ready, and unknown states in `src/ui/components/status_badges.py`
- [ ] T084 [US6] Run UI phase validation from quickstart in `tests/test_stock_analysis_pages.py`, `tests/test_ui_page_regressions.py`, `tests/e2e/test_navigation.py`, `tests/e2e/test_watchlist_page.py`, and `tests/e2e/test_stock_detail_page.py`

**Checkpoint**: User Story 6 completes the first-version Streamlit workflow.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, compatibility cleanup, and full regression after selected story scope is complete.

- [ ] T085 [P] Update README setup and validation instructions for the stock-analysis dashboard in `README.md`
- [ ] T086 [P] Update database and data-flow documentation for Mongo raw responses and MySQL clean analysis tables in `docs/`
- [ ] T087 Audit secrets handling for provider keys and database credentials in `src/config/settings.py`
- [ ] T088 Audit new stock-analysis code for prohibited broker, order execution, live trading, and hidden recommendation semantics in `src/` and `tests/`
- [ ] T089 Mark or hide legacy insider-trade pages only after replacement navigation is verified in `src/app/navigation.py`
- [ ] T090 Remove obsolete compatibility adapters only when their callers and tests are migrated in `src/services/`, `src/db/repositories/`, and `tests/`
- [ ] T091 Run full regression suite documented in `specs/001-stock-analysis-dashboard/quickstart.md` with `python -m pytest`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2 and is the MVP.
- **Phase 4 US2**: Depends on Phase 2 and can start after watchlist repository contracts from US1 are stable.
- **Phase 5 US3**: Depends on US2 clean price and financial data.
- **Phase 6 US4**: Depends on US3 feature data.
- **Phase 7 US5**: Depends on US3 and benefits from US4 predictions; must still show missing-prediction warnings if US4 data is unavailable.
- **Phase 8 US6**: Depends on page/service surfaces from US1 through US5.
- **Phase 9 Polish**: Depends on the selected story scope being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational; no dependency on other stories.
- **US2 (P1)**: Can start after Foundational; integrates with US1 watchlist symbols.
- **US3 (P1)**: Requires imported clean data from US2.
- **US4 (P2)**: Requires features from US3.
- **US5 (P2)**: Requires US3; uses US4 predictions where available.
- **US6 (P3)**: Integrates completed surfaces from US1-US5.

### Parallel Opportunities

- Setup placeholders T003-T005 can run in parallel.
- Foundational models T009-T013 can run in parallel.
- Foundational repositories T015-T016 can run in parallel after schema T007.
- Test tasks within each user story can be written in parallel before implementation.
- US2 repositories T036-T037 can run in parallel with FMP client work T035.
- US3 repositories T047-T048 can run in parallel.
- US4 repositories T058-T059 can run in parallel with UI test scaffolding T057.
- US5 repository T068 can run in parallel with UI test scaffolding T067.
- US6 page tests T074-T077 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Write failing US1 tests together:
Task: "T020 Add repository tests for add/edit/remove/list unresolved watchlist items in tests/test_watchlist_repository.py"
Task: "T021 Add service tests for watchlist metadata persistence and status summaries in tests/test_watchlist_service.py"
Task: "T022 Add Streamlit watchlist page tests for visible status text and reload behavior in tests/test_stock_analysis_pages.py"
Task: "T023 Add E2E watchlist workflow smoke test for three symbols in tests/e2e/test_watchlist_page.py"

# Implement UI components while repository/service work proceeds:
Task: "T027 Add watchlist page with add/edit/remove controls and explicit status text in src/ui/pages/watchlist_page.py"
Task: "T029 Add watchlist table/status rendering helpers in src/ui/components/tables.py and src/ui/components/status_badges.py"
```

## Parallel Example: User Story 2

```bash
Task: "T035 Add company profile, financial metric, and valuation endpoint methods in src/data_sources/fmp_client.py"
Task: "T036 Implement stock price history repository in src/db/repositories/stock_price_repository.py"
Task: "T037 Implement fundamental metrics repository in src/db/repositories/fundamental_metrics_repository.py"
Task: "T034 Add price and fundamental repository tests in tests/test_stock_data_repositories.py"
```

## Parallel Example: User Story 4

```bash
Task: "T054 Add prediction repository tests in tests/test_prediction_repositories.py"
Task: "T055 Add baseline and advanced model tests in tests/test_prediction_model_service.py"
Task: "T056 Add backtest metric and caveat tests in tests/test_backtest_service.py"
Task: "T057 Add model evaluation page tests in tests/test_stock_analysis_pages.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup and Phase 2 foundational infrastructure.
2. Complete Phase 3 User Story 1.
3. Stop and validate watchlist persistence, reload behavior, unresolved symbols, and visible status text.
4. Keep legacy insider-trade pages available until stock-analysis replacement pages pass tests.

### Incremental Delivery

1. Deliver US1 watchlist as the first usable increment.
2. Add US2 import and normalization for one provider and one symbol before expanding categories.
3. Add US3 feature calculation from imported clean data.
4. Add US4 prediction and backtesting only after feature readiness is explicit.
5. Add US5 ranking and explanation once component inputs are traceable.
6. Add US6 navigation and page completeness after underlying services exist.

### Validation Commands

Use the phase commands in `specs/001-stock-analysis-dashboard/quickstart.md`, ending with:

```bash
python -m pytest
```

## Notes

- All stock-analysis changes must be additive until replacement flows are tested.
- Do not use blind global search-and-replace for insider-trade terminology.
- MongoDB remains raw provider response storage; MySQL remains clean normalized analysis storage.
- Every data-quality state shown in the UI must include visible text, not only color or icons.
- New prediction, ranking, and preference code must not execute trades, connect to brokers, or describe output as a final trading decision.
