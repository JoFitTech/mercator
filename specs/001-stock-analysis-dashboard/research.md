# Research: Personal Stock Analysis Dashboard

## Repository Inventory Findings

- The repository is a single Python/Streamlit application, not a multi-app monorepo.
- `streamlit_app.py` is the runtime entry point.
- `src/app/navigation.py` currently routes Dashboard, Trades, Unternehmen, Methodik, Einstellungen, Admin, and detail pages.
- `src/data_sources/fmp_client.py` already supports FMP company profile and historical EOD price endpoints; it also contains insider-trade endpoints that should become legacy.
- `src/db/mongo_repository.py` stores raw insider trades and company documents in MongoDB.
- `src/db/schema.py` and `src/db/mysql_client.py` own MySQL DDL and migrations.
- `src/db/repositories/` follows a repository pattern that can be extended for watchlists, prices, features, predictions, and scores.
- `src/services/historical_market_data_service.py` already derives limited technical signals from historical daily prices.
- `src/services/import_service.py`, `analysis_service.py`, `dashboard_service.py`, `buy_engine.py`, `accumulation_service.py`, and `src/preprocessing/gate_evaluator.py` are insider-trade-shaped and should not be blindly renamed.
- `tests/` already covers repository behavior, import behavior, settings, status badges, degraded mode, and UI regressions.

## Decisions

### Decision 1: Add Stock Modules Beside Legacy Modules First

**Decision**: Introduce new stock-analysis modules and repositories before renaming or deleting insider-trade modules.

**Rationale**: This preserves a runnable Streamlit application after each phase and avoids breaking existing tests while the new workflow is incomplete.

**Alternatives rejected**:

- Blind global rename from trade to stock: unsafe because current data schema, UI, tests, and service semantics are not one-to-one.
- New greenfield app: violates the brownfield constitution and user request.

### Decision 2: Additive MySQL Schema First

**Decision**: Add new stock-analysis tables while leaving `insider_trades` and related legacy tables intact.

**Rationale**: The current app and tests rely on insider-trade tables. Additive tables allow new repositories and UI pages to be tested without destructive migration.

**Alternatives rejected**:

- Immediate table rename: high risk and low value before the stock workflow exists.
- Store clean analysis data in MongoDB only: violates the required raw/clean split.

### Decision 3: Generic Raw Provider Responses In MongoDB

**Decision**: Add a generic raw response collection for profiles, prices, financial metrics, valuation metrics, and later providers.

**Rationale**: The current raw insider collection is too narrow for watchlist-driven stock analysis. A generic collection keeps provider metadata and failures traceable.

**Alternatives rejected**:

- One Mongo collection per endpoint initially: unnecessary fragmentation for v1.
- Only store failed raw responses: loses auditability and replay/debug value.

### Decision 4: Prediction Transparency Is Part Of The Data Model

**Decision**: Store confidence, uncertainty, model quality, model version, horizon, target, evaluation period, sample size, and input freshness with predictions.

**Rationale**: Transparency is a constitutional requirement and cannot be bolted on as UI text only.

**Alternatives rejected**:

- Single prediction score column: insufficient to explain quality and uncertainty.

### Decision 5: Preference Scoring Is Decision Support, Not Trading

**Decision**: New scoring language uses preference, ranking, components, and explanations; it must not use buy/order/execution semantics.

**Rationale**: The first version excludes broker integration, live trading, and final trading decisions.

**Alternatives rejected**:

- Reuse `buy_engine.py` directly: it contains buy/execution terminology that conflicts with the new boundary.

## Open Technical Decisions For Implementation

- Exact advanced model dependency: choose during implementation after checking acceptable dependencies. If no new dependency is approved, use a Pandas/Numpy-compatible advanced heuristic or lightweight model with existing stack.
- Exact FMP endpoints for financial and valuation metrics: add only after confirming provider payloads and entitlement behavior in code/tests.
- Exact initial prediction horizons: likely 5, 20, and/or 60 trading days, but the implementation phase should choose one minimal horizon first.
