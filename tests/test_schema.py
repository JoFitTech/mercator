"""Tests für die deklarative MySQL-DDL-Liste."""

from __future__ import annotations

from src.db.schema import MYSQL_SCHEMA_STATEMENTS


def test_mysql_schema_statements_exist() -> None:
    """Prüft, dass DDL-Statements als nicht-leere Liste vorliegen."""

    assert isinstance(MYSQL_SCHEMA_STATEMENTS, list)
    assert MYSQL_SCHEMA_STATEMENTS


def test_mysql_schema_contains_required_tables() -> None:
    """Prüft, dass beide geforderten Tabellen in der DDL vorkommen."""

    ddl_blob = "\n".join(MYSQL_SCHEMA_STATEMENTS).lower()
    assert "create table if not exists companies" in ddl_blob
    assert "create table if not exists insider_trades" in ddl_blob


# Offene Testpunkte stehen zentral in ``docs/todos_offene_fragen.md``.
