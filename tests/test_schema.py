"""Tests für die deklarative MySQL-DDL-Liste."""

from __future__ import annotations

from src.db.schema import MYSQL_SCHEMA_STATEMENTS


def test_mysql_schema_statements_exist() -> None:
    """Prüft, dass DDL-Statements als nicht-leere Liste vorliegen."""

    assert isinstance(MYSQL_SCHEMA_STATEMENTS, list)
    assert MYSQL_SCHEMA_STATEMENTS


def test_mysql_schema_contains_required_tables() -> None:
    """Prüft, dass alle geforderten Tabellen in der DDL vorkommen."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()
    assert "create table if not exists companies" in ddl_blob
    assert "create table if not exists insider_trades" in ddl_blob
    assert "create table if not exists company_trade_stats" in ddl_blob
    assert "create table if not exists market_signal_cache" in ddl_blob
    assert "create table if not exists app_filter_settings" in ddl_blob
    assert "create table if not exists app_runtime_preferences" in ddl_blob
    assert "create table if not exists app_data_state" in ddl_blob


def test_mysql_schema_contains_stock_analysis_tables() -> None:
    """Prueft, dass die Stock-Analysis-DDL additiv enthalten ist."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()
    required_tables = [
        "watchlist_items",
        "stock_price_history",
        "fundamental_metrics",
        "technical_features",
        "fundamental_features",
        "model_runs",
        "prediction_results",
        "backtest_results",
        "preference_scores",
        "import_runs",
        "data_quality_issues",
    ]

    for table_name in required_tables:
        assert f"create table if not exists {table_name}" in ddl_blob


def test_mysql_schema_preserves_legacy_tables_while_adding_stock_analysis() -> None:
    """Schuetzt die Brownfield-Regel: keine Legacy-Tabellen entfernen."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()

    assert "create table if not exists insider_trades" in ddl_blob
    assert "create table if not exists company_trade_stats" in ddl_blob
    assert "create table if not exists market_signal_cache" in ddl_blob
    assert "create table if not exists watchlist_items" in ddl_blob
    assert "create table if not exists prediction_results" in ddl_blob


def test_mysql_schema_contains_stock_analysis_keys_and_quality_fields() -> None:
    """Prueft zentrale Schluessel und sichtbare Datenqualitaetsfelder."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()

    assert "unique key uq_watchlist_items_symbol" in ddl_blob
    assert "unique key uq_stock_price_history_symbol_date_provider" in ddl_blob
    assert "unique key uq_fundamental_metrics_symbol_metric_period_provider" in ddl_blob
    assert "unique key uq_technical_features_symbol_date" in ddl_blob
    assert "unique key uq_fundamental_features_symbol_period" in ddl_blob
    assert "quality_status" in ddl_blob
    assert "feature_status" in ddl_blob
    assert "unavailable_reason" in ddl_blob
    assert "data_quality_summary" in ddl_blob


def test_mysql_schema_contains_required_fields() -> None:
    """Prüft, dass Validierung/Score und Sync-Metadaten in der DDL enthalten sind."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()
    assert "validation_status" in ddl_blob
    assert "score" in ddl_blob
    assert "score_class" in ddl_blob
    assert "source_system" in ddl_blob
    assert "sync_version" in ddl_blob


def test_mysql_schema_contains_v2_api3_fields() -> None:
    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()
    assert "transaction_code_class" in ddl_blob
    assert "avg_20d_volume" in ddl_blob
    assert "avg_20d_dollar_volume" in ddl_blob
    assert "momentum_3m" in ddl_blob
    assert "liquidity_state" in ddl_blob
    assert "lookback_from" in ddl_blob
    assert "lookback_to" in ddl_blob


# Offene Testpunkte stehen zentral in ``docs/todos_offene_fragen.md``.
