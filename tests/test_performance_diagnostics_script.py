from __future__ import annotations

from types import SimpleNamespace

from src.scripts import performance_diagnostics as diag


def test_benchmark_import_batch_vs_legacy_shows_lower_query_count_for_batch() -> None:
    legacy, batch = diag.benchmark_import_batch_vs_legacy()

    assert legacy.sql_queries > batch.sql_queries
    assert legacy.rows == batch.rows == 100


def test_benchmark_dashboard_cache_keeps_state_lookup_on_cache_hit() -> None:
    miss, hit = diag.benchmark_dashboard_cache()

    assert miss.area == "Dashboard"
    assert "state lookup" in miss.scenario
    assert "state lookup only" in hit.scenario
    assert miss.sql_queries >= 3
    assert hit.sql_queries <= 2


def test_benchmark_api3_cache_hit_miss_reports_both_paths() -> None:
    miss, hit = diag.benchmark_api3_cache_hit_miss()
    assert miss.area == "API3"
    assert miss.scenario == "cache miss"
    assert hit.scenario == "cache hit"


def test_dashboard_normal_aggregate_scenario_avoids_full_load() -> None:
    row = diag.benchmark_dashboard_normal_aggregate_path_without_full_load()
    assert row.area == "Dashboard"
    assert row.scenario == "Normal aggregate path (no full-load)"


def test_dashboard_fallback_scenario_is_explicit() -> None:
    row = diag.benchmark_dashboard_fallback_full_load_path()
    assert row.area == "Dashboard"
    assert row.scenario == "Fallback full-load path"


def test_company_trade_stats_recompute_scenario_present() -> None:
    row = diag.benchmark_company_trade_stats_recompute_path()
    assert row.area == "company_trade_stats"
    assert row.rows == 250


def test_api2_bulk_vs_single_simulation_reports_query_delta() -> None:
    single, bulk = diag.benchmark_api2_bulk_cache_lookup_vs_legacy_single(symbols=30)
    assert single.sql_queries == 30
    assert bulk.sql_queries == 1
    assert single.duration_ms > bulk.duration_ms


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


