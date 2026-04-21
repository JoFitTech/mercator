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
    assert "create table if not exists app_filter_settings" in ddl_blob
    assert "create table if not exists app_runtime_preferences" in ddl_blob


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


# Offene Testpunkte stehen zentral in ``docs/todos_offene_fragen.md``.
