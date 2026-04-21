from __future__ import annotations

from types import SimpleNamespace

from src.scripts import performance_diagnostics as diag


def test_benchmark_import_batch_vs_legacy_shows_lower_query_count_for_batch() -> None:
    legacy, batch = diag.benchmark_import_batch_vs_legacy()

    assert legacy.sql_queries > batch.sql_queries
    assert legacy.rows == batch.rows == 100


def test_diagnose_mongo_classifies_missing_local_service(monkeypatch) -> None:
    monkeypatch.setattr(
        diag,
        "load_settings",
        lambda: SimpleNamespace(mongo=SimpleNamespace(uri="mongodb://localhost:27017/")),
    )

    def fake_create_connection(*args, **kwargs):
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr(diag.socket, "create_connection", fake_create_connection)

    class _Db:
        def command(self, name: str):
            raise RuntimeError("no ping")

    monkeypatch.setattr(
        diag,
        "MongoClientWrapper",
        lambda config, server_selection_timeout_ms=2000: SimpleNamespace(get_database=lambda: _Db()),
    )

    result = diag.diagnose_mongo()

    assert result["classification"] == "runtime_environment_or_missing_service"
