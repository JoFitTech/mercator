# Quickstart: Personal Stock Analysis Dashboard

This quickstart describes validation steps for each implementation phase. It does not introduce a new repository or app.

## Existing App Baseline

```bash
python -m pytest tests/test_service_factory.py tests/test_database_status_service.py tests/test_status_badges.py
streamlit run streamlit_app.py
```

Expected result: the current Mercator Streamlit app still starts before stock-analysis replacement modules are complete.

## Schema Phase

```bash
python -m pytest tests/test_init_mysql_schema.py tests/test_schema.py
python -m pytest tests/test_watchlist_repository.py tests/test_data_quality_repository.py
```

Expected result: new stock-analysis MySQL tables initialize additively and legacy insider-trade tables remain available.

## Watchlist MVP Phase

```bash
python -m pytest tests/test_watchlist_repository.py tests/test_watchlist_service.py tests/test_stock_analysis_pages.py
python -m pytest tests/test_ui_page_regressions.py tests/test_stocklens_baseline.py
MERCATOR_E2E_AUTOSTART=true python -m pytest tests/e2e/test_watchlist_page.py
```

Expected result: a user can persist watchlist entries and reload the Watchlist page while symbol metadata, resolution status, and explicit profile, price, financial, prediction, and preference status text remain visible without requiring ranking data.

## Import Phase

```bash
python -m pytest tests/test_stock_import_service.py tests/test_mongo_repository.py
```

Expected result: mocked provider responses are written to MongoDB raw storage first, then normalized clean records and data-quality statuses are written to MySQL.

## Feature Phase

```bash
python -m pytest tests/test_feature_engineering_service.py tests/test_data_quality_evaluator.py
```

Expected result: technical and fundamental features are deterministic for fixture data and unavailable reasons are explicit for missing inputs.

## Model And Scoring Phase

```bash
python -m pytest tests/test_prediction_model_service.py tests/test_backtest_service.py tests/test_preference_scoring_service.py
```

Expected result: predictions include confidence, uncertainty, model quality, model version, horizon, and freshness; preference scores include component explanations.

## UI Phase

```bash
python -m pytest tests/test_stock_analysis_pages.py tests/test_ui_page_regressions.py
python -m pytest tests/e2e/test_navigation.py tests/e2e/test_watchlist_page.py tests/e2e/test_stock_detail_page.py
```

Expected result: Streamlit pages show watchlist, stock detail, model evaluation, methodology, and admin workflows with explicit text for missing, stale, incomplete, or failed data.

## Full Regression

```bash
python -m pytest
```

Expected result: new stock-analysis tests pass and legacy tests continue passing until corresponding legacy modules are intentionally retired.
