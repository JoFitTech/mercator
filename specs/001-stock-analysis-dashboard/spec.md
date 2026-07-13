# Feature Specification: Personal Stock Analysis Dashboard

**Feature Branch**: `feature/stocklens-brownfield`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "Modernize the existing Mercator repository into a personal stock analysis, prediction, and preference dashboard. Reuse the existing Python, Pandas, Streamlit, MongoDB, and MySQL architecture. Refactor the current insider-trade-specific application into a broader stock analysis system through safe repository analysis, renaming, and restructuring. Support manual watchlists, company profiles, historical daily prices, financial and valuation metrics, technical and fundamental features, prediction models, backtesting, confidence, model quality, transparent preference scoring, ranked explanations, Streamlit pages, visible data-quality states, and manual trading outside the application. Exclude broker integration, automatic order execution, live trading, and hidden recommendations."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintain A Manual Stock Watchlist (Priority: P1)

As a personal investor, I want to add, edit, remove, and review a manual stock watchlist so Mercator analyzes only the securities I care about first.

**Why this priority**: A watchlist is the new domain anchor that replaces the current insider-trade feed as the primary user workflow while preserving the existing app until the replacement flow exists.

**Independent Test**: Can be tested by adding at least three symbols to the watchlist, refreshing the page, and confirming the same symbols, names, statuses, and data freshness text remain visible.

**Acceptance Scenarios**:

1. **Given** the Streamlit app is running with empty watchlist data, **When** the user adds a valid stock symbol, **Then** the watchlist shows the symbol with explicit profile, price, financial, prediction, and preference data status text.
2. **Given** a symbol is already on the watchlist, **When** the user edits notes, priority, or removes the symbol, **Then** the change is persisted and reflected in the dashboard and stock detail page.
3. **Given** a symbol cannot be resolved by the configured provider, **When** the user adds it, **Then** the watchlist keeps the entry visible with an explicit unresolved or failed status and no silent deletion.

---

### User Story 2 - Import And Normalize Stock Data (Priority: P1)

As a user, I want Mercator to import company profiles, historical daily prices, selected financial metrics, and selected valuation metrics for watchlist stocks so analysis is based on current and traceable source data.

**Why this priority**: Prediction, scoring, detail pages, and rankings cannot be useful without reliable raw and clean data flowing through the existing MongoDB and MySQL architecture.

**Independent Test**: Can be tested by importing data for one watchlist symbol and verifying raw API payloads exist in MongoDB while normalized profile, price, financial, valuation, and data-quality records exist in MySQL.

**Acceptance Scenarios**:

1. **Given** a watchlist symbol and valid API key environment variables, **When** the user triggers data import, **Then** raw provider responses are stored in MongoDB and normalized clean records are stored in MySQL.
2. **Given** the provider returns partial data, stale timestamps, rate limits, or an error, **When** the import completes, **Then** the UI and clean data store show explicit missing, stale, incomplete, or failed status text for each affected dataset.
3. **Given** historical daily prices are imported, **When** the clean store is updated, **Then** the system can identify the latest available trading date and the freshness of that price series.

---

### User Story 3 - Calculate Technical And Fundamental Features (Priority: P1)

As a user, I want Mercator to calculate technical and fundamental features for each watchlist stock so rankings and predictions are based on transparent factors.

**Why this priority**: Feature generation provides the explainable basis for predictions, model evaluation, and preference scoring.

**Independent Test**: Can be tested by loading a symbol with sufficient price and financial history and verifying feature values plus explicit unavailable reasons for any feature that cannot be calculated.

**Acceptance Scenarios**:

1. **Given** sufficient daily price history exists, **When** feature calculation runs, **Then** momentum, moving averages, volatility, drawdown, and volume trend features are stored and shown with source freshness.
2. **Given** selected financial and valuation metrics exist, **When** feature calculation runs, **Then** revenue growth, earnings growth, margins, valuation ratios, debt metrics, and market capitalization are stored where available.
3. **Given** a feature cannot be calculated because inputs are missing or too short, **When** results are shown, **Then** the UI displays an explicit reason rather than a blank cell or color-only signal.

---

### User Story 4 - Train, Backtest, And Compare Prediction Models (Priority: P2)

As a user, I want at least one baseline model and one more advanced model to generate and backtest stock predictions over defined horizons so I can see whether predictions have historical support.

**Why this priority**: Predictions are central to the target product, but they must be built after watchlist data and features exist.

**Independent Test**: Can be tested by training or refreshing models for a fixed horizon, generating predictions for watchlist stocks, and reviewing backtest metrics for each model.

**Acceptance Scenarios**:

1. **Given** clean historical features and outcomes exist, **When** model training or refresh runs, **Then** Mercator creates at least one baseline model and one more advanced model for a defined prediction horizon.
2. **Given** models have been evaluated, **When** the user opens model evaluation, **Then** the page shows historical model quality, evaluation period, sample size, horizon, metric definitions, and data freshness.
3. **Given** a model produces direction, return class, or expected return predictions, **When** predictions are shown, **Then** each prediction includes confidence, uncertainty, model version, model quality, and input freshness.

---

### User Story 5 - Rank Stocks With Transparent Preference Scores (Priority: P2)

As a user, I want a transparent preference score that combines fundamentals, technical factors, risk, prediction output, and confidence so I can rank stocks and understand why one is preferred or deprioritized.

**Why this priority**: Preference ranking is the final decision-support surface, and it must explain its inputs without becoming an unexplained recommendation engine.

**Independent Test**: Can be tested by ranking a watchlist and verifying every ranked row has component scores, explanation text, uncertainty/confidence, and data-quality warnings.

**Acceptance Scenarios**:

1. **Given** a watchlist has feature and prediction data, **When** ranking is calculated, **Then** each stock receives a preference score with component contributions from fundamentals, technicals, risk, prediction output, and confidence.
2. **Given** data is incomplete or stale for a stock, **When** ranking is shown, **Then** the stock remains visible with an explicit penalty, warning, or "not enough data" explanation.
3. **Given** one stock ranks above another, **When** the user opens the explanation, **Then** the UI states the main positive and negative factors behind the ranking in plain language.

---

### User Story 6 - Navigate Stock Analysis Pages (Priority: P3)

As a user, I want an overview dashboard, watchlist page, stock detail page, model evaluation page, methodology page, and admin page so the analysis workflow is complete inside Streamlit.

**Why this priority**: Navigation and page coverage make the modernized product usable after the core data, feature, prediction, and ranking workflows exist.

**Independent Test**: Can be tested by opening each page in Streamlit and confirming that data status, freshness, and explanation text are visible without relying on color alone.

**Acceptance Scenarios**:

1. **Given** the modernized app is running, **When** the user navigates the top-level pages, **Then** the overview dashboard, watchlist, stock detail, model evaluation, methodology, and admin pages are reachable.
2. **Given** a stock has mixed data quality, **When** the user opens its detail page, **Then** the page shows company profile, historical price summaries, features, predictions, preference score, explanations, and explicit missing/stale/failed data text.
3. **Given** the user opens methodology, **When** prediction or scoring logic is described, **Then** the page states that Mercator does not execute trades and final trading decisions remain outside the application.

### Edge Cases

- A watchlist symbol changes ticker, has multiple listings, or maps ambiguously to provider records.
- A provider returns raw data successfully but normalization fails for part of the payload.
- Historical price history is too short for moving averages, volatility, drawdown, horizon outcomes, or backtesting.
- Financial metrics are unavailable for ETFs, ADRs, new listings, foreign listings, or provider-limited plans.
- Model training has too few samples for a requested horizon or produces unstable quality metrics.
- Predictions are older than their input data or were generated by an obsolete model version.
- Rankings encounter conflicting signals, such as strong fundamentals with weak technicals or positive prediction with low confidence.
- MongoDB or MySQL is unavailable, falls back to a configured target, or contains stale synchronized data.
- API keys are missing, invalid, rate limited, or not authorized for selected provider endpoints.
- Existing insider-trade pages or modules still exist while replacement stock-analysis modules are not yet complete.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be modernized in the existing Mercator repository and MUST preserve the current working Streamlit application until replacement modules are available.
- **FR-002**: System MUST reuse the existing Python, Pandas, Streamlit, MongoDB, and MySQL architecture.
- **FR-003**: System MUST provide a manual stock watchlist with persistent symbols and user-maintained metadata such as notes, priority, or active/inactive state.
- **FR-004**: System MUST import company profile data for watchlist symbols.
- **FR-005**: System MUST import historical daily price data for watchlist symbols.
- **FR-006**: System MUST import selected financial and valuation metrics for watchlist symbols where provider data is available.
- **FR-007**: System MUST store raw external API responses and provider metadata in MongoDB.
- **FR-008**: System MUST store normalized clean analysis data, features, predictions, evaluations, preference scores, and watchlist records in MySQL.
- **FR-009**: System MUST track data freshness, provider, import status, and failure reason for each imported data category.
- **FR-010**: System MUST calculate technical features including momentum, moving averages, volatility, drawdown, and volume trends where sufficient data exists.
- **FR-011**: System MUST calculate fundamental features including revenue growth, earnings growth, margins, valuation ratios, debt metrics, and market capitalization where sufficient data exists.
- **FR-012**: System MUST create prediction models for explicitly defined horizons.
- **FR-013**: System MUST include at least one baseline model and at least one more advanced model.
- **FR-014**: System MUST produce predictions for at least one of direction, return class, or expected return.
- **FR-015**: System MUST backtest predictions against historical outcomes for each supported horizon and model.
- **FR-016**: System MUST show model confidence, uncertainty, historical model quality, model version, evaluation period, and data freshness with predictions.
- **FR-017**: System MUST calculate a transparent preference score from fundamentals, technical factors, risk, prediction output, and confidence.
- **FR-018**: System MUST rank watchlist stocks by preference score.
- **FR-019**: System MUST explain why each stock is preferred or deprioritized using visible text and component contributions.
- **FR-020**: System MUST include Streamlit pages for overview dashboard, watchlist, stock detail, model evaluation, methodology, and admin workflows.
- **FR-021**: System MUST show missing, stale, incomplete, low-quality, or failed data explicitly as text in the UI, not only through color, icons, or chart styling.
- **FR-022**: System MUST keep manual trading outside the application.
- **FR-023**: System MUST NOT include broker integration, automatic order execution, live trading, or hidden recommendations without explanation.
- **FR-024**: System MUST keep API keys, tokens, and secrets in environment variables or existing secret-management paths.
- **FR-025**: System MUST safely refactor insider-trade-specific concepts into stock-analysis concepts based on repository analysis and a rename map; blind global search-and-replace is prohibited.
- **FR-026**: System MUST update imports, tests, UI references, documentation, configuration, and database references together when a module or concept is renamed.
- **FR-027**: System MUST provide compatibility or migration behavior for existing data paths until replacement stock-analysis paths are verified.

### Brownfield Repository Analysis

Current repository capabilities to reuse:

- **Streamlit entry and navigation**: `streamlit_app.py`, `src/app/navigation.py`, and `src/ui/pages/` already provide a multi-page Streamlit app.
- **Provider clients**: `src/data_sources/fmp_client.py` already supports company profiles and historical EOD prices, with optional Alpha Vantage and Polygon clients available.
- **Raw MongoDB storage**: `src/db/mongo_repository.py` stores insider raw payloads and company documents; this pattern should become generic raw provider-response storage for watchlist-driven stock data.
- **Clean MySQL storage**: `src/db/schema.py`, `src/db/mysql_client.py`, and `src/db/repositories/` already define relational tables, migrations, and repositories for companies, trades, market signal cache, settings, and sync state.
- **Existing price-derived signals**: `src/services/historical_market_data_service.py` already calculates SMA, momentum, volume, and liquidity state from historical EOD prices and can be expanded.
- **Existing scoring and dashboard patterns**: `src/services/scoring_service.py`, `src/services/dashboard_service.py`, and UI components provide patterns for score calculation, status badges, tables, and charts.
- **Existing tests**: `tests/` and `tests/e2e/` cover repositories, status badges, UI regressions, import flows, and startup behavior and should be extended during implementation.

### Safe Rename And Restructuring Map

The following rename map is the starting point for implementation planning. Each rename must be performed in scoped batches with imports, tests, UI text, docs, and database compatibility considered together.

| Current insider-trade concept | Target stock-analysis concept | Notes |
|---|---|---|
| `insider_trades` table | `stock_events` or archived compatibility table | Do not rename blindly; first introduce watchlist, prices, features, predictions, and scores tables. Preserve compatibility until old pages are replaced. |
| `InsiderTrade` model | `StockEvent` only if event history remains needed | Watchlist-driven analysis may not need a direct one-to-one replacement. |
| `trade_repository.py` | `stock_repository.py`, `watchlist_repository.py`, or compatibility repository | Split by responsibility instead of carrying trade semantics forward. |
| `trades_page.py` | `watchlist_page.py` or `stocks_page.py` | Replace UI only after watchlist data path exists. |
| `trade_detail_page.py` | `stock_detail_page.py` | Must include profile, price, feature, prediction, preference, freshness, and explanation sections. |
| `buy_engine.py` | `preference_scoring_service.py` | Remove buy/execution semantics; output decision-support preference scores only. |
| `gate_evaluator.py` and gate statuses | `data_quality_evaluator.py` and analysis readiness statuses | Gates should become data readiness/quality, not trade filters. |
| `AccumulationService` | retire or replace with time-series feature aggregation | Insider transaction clustering does not map directly to watchlist analysis. |
| `market_signal_cache` | `technical_features` or expanded market feature store | Existing fields can seed v1 technical feature calculations. |
| `company_trade_stats` | `stock_analysis_summary` | Summary should track watchlist and analysis state rather than insider activity. |
| `Trade Republic` universe fields | availability/reference metadata only if still useful | Must not imply broker connectivity, live tradability, or order execution. |

### Key Entities *(include if feature involves data)*

- **Watchlist Item**: A user-selected stock symbol with optional notes, priority, active state, created/updated timestamps, and symbol resolution status.
- **Security / Company**: A normalized company or instrument record with symbol, name, exchange, identifiers, sector, industry, country, market capitalization, and profile freshness.
- **Raw Provider Response**: A MongoDB document containing provider name, endpoint/category, request parameters, response payload, fetched timestamp, status, and error metadata.
- **Historical Daily Price**: A clean MySQL record for symbol, trading date, open/high/low/close/adjusted close, volume, provider, and freshness.
- **Financial Metric**: A clean MySQL record for selected financial, fundamental, and valuation metrics with period, value, unit, source, and freshness.
- **Technical Feature Set**: Derived metrics for a symbol and calculation date, including momentum, moving averages, volatility, drawdown, and volume trends plus readiness status.
- **Fundamental Feature Set**: Derived metrics for a symbol and period, including growth, margin, valuation, debt, and market capitalization features plus readiness status.
- **Prediction Model**: A named model with type, horizon, target, version, training window, feature set version, and lifecycle status.
- **Prediction Result**: A symbol-level model output for a horizon, including direction, return class, expected return, confidence, uncertainty, input freshness, and model version.
- **Backtest Result**: Historical evaluation results for a model and horizon, including sample size, evaluation period, quality metrics, and caveats.
- **Preference Score**: A transparent ranking output composed of fundamental, technical, risk, prediction, and confidence components plus explanation text and data-quality warnings.
- **Data Quality Status**: A normalized status object for missing, stale, incomplete, failed, low-quality, ready, or unknown data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can add at least five watchlist symbols and see persisted metadata, resolution status, and data freshness/status text after a Streamlit reload.
- **SC-002**: For a successfully imported symbol, raw profile, historical price, financial, and valuation provider responses are stored in MongoDB and corresponding normalized records are queryable from MySQL.
- **SC-003**: For symbols with at least 250 trading days of price history, the system calculates momentum, moving average, volatility, drawdown, and volume trend features without manual spreadsheet work.
- **SC-004**: For symbols with available financial data, the system calculates at least one growth metric, one margin metric, one valuation metric, one debt metric, and market capitalization.
- **SC-005**: The model evaluation page displays at least one baseline model and one advanced model with horizon, target type, sample size, evaluation window, and historical quality metrics.
- **SC-006**: Every displayed prediction includes confidence, uncertainty, model version, model quality, and input data freshness.
- **SC-007**: Every ranked stock includes a preference score, component score breakdown, and at least one positive or negative explanation sentence.
- **SC-008**: Missing, stale, incomplete, and failed data states are visible as text on overview, watchlist, stock detail, model evaluation, and admin pages.
- **SC-009**: No first-version page or service connects to a broker, places an order, executes a trade, starts live trading, or presents unexplained recommendations.

## First-Version Exclusions

- Broker integration.
- Automatic order execution.
- Live trading.
- Hidden or unexplained recommendations.
- Any workflow that treats Mercator output as a final trading decision.

## Assumptions

- FMP remains the primary provider for v1 because the existing client already supports company profiles and historical daily price data.
- Alpha Vantage and Polygon may remain optional fallback providers if existing code paths can be reused without expanding scope.
- The first UI remains Streamlit and uses the existing navigation/app bootstrap pattern.
- The app is single-user or personal-use scoped unless a later feature explicitly introduces multi-user behavior.
- Prediction horizons will be defined during planning, with reasonable initial candidates such as 5, 20, or 60 trading days.
- The advanced model can be implemented with dependencies already acceptable for the repository or added through an explicit plan.
- Existing insider-trade functionality may remain temporarily visible until replacement watchlist, stock detail, scoring, and dashboard pages exist.
- Provider entitlements may limit available financial or valuation metrics; unavailable metrics must be surfaced as data-quality states rather than treated as failures of the whole stock.
