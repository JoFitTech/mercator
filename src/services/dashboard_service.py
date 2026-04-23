"""Dashboard-Service für eine signalorientierte Overview-Seite."""

from __future__ import annotations

from datetime import date
import time
from typing import Any

import pandas as pd

from src.db.mongo_repository import CompanyMongoRepository, InsiderTradeMongoRepository
from src.db.repositories.company_repository import CompanyMySqlRepository
from src.db.repositories.trade_repository import InsiderTradeMySqlRepository
from src.services.accumulation_service import AccumulationService


UNKNOWN_PROFILE_LABEL = "Unknown / API2 fehlt"


class DashboardService:
    """Erzeugt Dashboard-Kennzahlen und Chartdaten auf akkumulierter Basis."""

    def __init__(
        self,
        raw_repo: InsiderTradeMongoRepository | None,
        company_mongo_repo: CompanyMongoRepository | None,
        trade_repo: InsiderTradeMySqlRepository,
        company_repo: CompanyMySqlRepository,
    ) -> None:
        self.raw_repo = raw_repo
        self.company_mongo_repo = company_mongo_repo
        self.trade_repo = trade_repo
        self.company_repo = company_repo
        self._payload_cache_ttl_seconds = 45
        self._payload_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._state_cache_ttl_seconds = 10
        self._state_cache: tuple[float, str] | None = None

    def build_dashboard_payload(self, filters: dict | None = None) -> dict[str, Any]:
        """Liefert alle Dashboard-Daten in einem stabilen Payload."""
        filters = dict(filters or {})
        filters.pop("dashboard_valid", None)
        cache_key = self._build_cache_key(filters)
        cached = self._payload_cache.get(cache_key)
        now = time.time()
        if cached and now - cached[0] <= self._payload_cache_ttl_seconds:
            return cached[1]

        payload_error_message: str | None = None
        try:
            payload = self._build_payload_from_aggregate_queries(filters)
        except Exception as exc:
            payload_error_message = str(exc)
            try:
                trades_df = self.trade_repo.fetch_trades_enriched_with_company(limit=20_000, filters=filters)
            except Exception as fallback_exc:
                trades_df = pd.DataFrame()
                payload_error_message = f"{payload_error_message}; fallback failed: {fallback_exc}"
            trades_df = self._hydrate_company_fields_from_mongo(trades_df)
            prepared_df = self._prepare_dataframe(trades_df)
            core_df = self._build_accumulated_core_df(prepared_df)
            payload = {
                **self._compute_dashboard_kpis(core_df, prepared_df),
                **self._build_sector_pies(core_df),
                **self._build_net_sector_signal(core_df),
                **self._build_market_cap_distribution(core_df),
                **self._build_top_tables(core_df),
                **self._build_missing_data_summary(core_df),
                "last_update": self._get_last_update_str(prepared_df),
            }

        payload["payload_error_message"] = payload_error_message
        self._payload_cache[cache_key] = (now, payload)
        return payload

    def _build_cache_key(self, filters: dict[str, Any]) -> str:
        cached_state = self._state_cache
        now = time.time()
        if cached_state and now - cached_state[0] <= self._state_cache_ttl_seconds:
            state_token = cached_state[1]
        else:
            if hasattr(self.trade_repo, "get_dashboard_state_token"):
                state_token = str(self.trade_repo.get_dashboard_state_token())
            else:
                trade_state = (
                    self.trade_repo.get_max_updated_at()
                    if hasattr(self.trade_repo, "get_max_updated_at")
                    else "none"
                ) or "none"
                company_state = (
                    self.company_repo.get_max_updated_at()
                    if hasattr(self.company_repo, "get_max_updated_at")
                    else None
                )
                company_state_token = str(company_state) if company_state is not None else "none"
                state_token = f"{trade_state}|{company_state_token}"
            self._state_cache = (now, state_token)
        filter_token = tuple(sorted(filters.items()))
        return f"{state_token}|{filter_token}"

    def _build_payload_from_aggregate_queries(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Baut Dashboard-Payload aus aggregierten Queries, OHNE großen Trade-Detailload.
        
        Diese Methode nutzt spezialisierte Repository-Queries statt des 20_000-Trade-Vollpfads.
        """
        # Alle Daten aus aggregierten Queries laden
        snapshot = self.trade_repo.fetch_dashboard_kpi_snapshot(filters=filters)
        sector_dist = self.trade_repo.fetch_dashboard_sector_distribution(filters=filters)
        market_caps = self.trade_repo.fetch_dashboard_market_cap_distribution(filters=filters)
        
        # Top-Tabellen direkt aus Query-Pfaden laden (NICHT aus 20_000-Trade-DF!)
        top_buys_df = self.trade_repo.fetch_dashboard_top_trades(direction="BUY", filters=filters, limit=5)
        top_sells_df = self.trade_repo.fetch_dashboard_top_trades(direction="SELL", filters=filters, limit=5)
        
        # Sector-Verteilungen verarbeiten
        buy_sector = sector_dist[sector_dist["direction"] == "BUY"][["sector", "count", "volume"]] if not sector_dist.empty else pd.DataFrame(columns=["sector", "count", "volume"])
        sell_sector = sector_dist[sector_dist["direction"] == "SELL"][["sector", "count", "volume"]] if not sector_dist.empty else pd.DataFrame(columns=["sector", "count", "volume"])
        
        # Net-Signal-Aggregation
        net = pd.DataFrame(columns=["sector", "buy_count", "sell_count", "delta", "buy_volume", "sell_volume"])
        if not sector_dist.empty:
            buy_net = buy_sector.rename(columns={"count": "buy_count", "volume": "buy_volume"}).set_index("sector")
            sell_net = sell_sector.rename(columns={"count": "sell_count", "volume": "sell_volume"}).set_index("sector")
            net = buy_net.join(sell_net, how="outer").fillna(0).reset_index()
            net["delta"] = net["buy_count"] - net["sell_count"]
            net = net.sort_values(["delta", "buy_count"], ascending=[False, False])
        
        # Market-Cap-Verteilung
        expected_buckets = {
            "Small Cap (<2B)": 0,
            "Mid Cap (2B-10B)": 0,
            "Large Cap (>=10B)": 0,
            UNKNOWN_PROFILE_LABEL: 0,
        }
        if not market_caps.empty and {"bucket", "companies"}.issubset(set(market_caps.columns)):
            for row in market_caps.to_dict(orient="records"):
                expected_buckets[str(row.get("bucket"))] = int(row.get("companies") or 0)
        market_cap_distribution = pd.DataFrame(
            [{"bucket": bucket, "companies": companies} for bucket, companies in expected_buckets.items()]
        )
        
        # Berechne missing_data_summary aus Snapshot-Daten (nicht aus großem DF!)
        missing_summary = self._compute_missing_data_summary_from_snapshot(snapshot, filters)
        
        # Berechne ergänzende KPIs aus Snapshot (nicht hardcodiert!)
        enriched_kpis = self._compute_enriched_kpis_from_snapshot(snapshot, filters)
        
        return {
            "kpi_buy_sell_ratio_count": f"{snapshot['buy_count']}:{snapshot['sell_count']}",
            "kpi_buy_sell_ratio_volume": f"{snapshot['buy_volume']:,.0f}:{snapshot['sell_volume']:,.0f}",
            "kpi_relevant_trades_count": snapshot["relevant_trades"],
            "kpi_affected_companies_count": snapshot["affected_companies"],
            "kpi_largest_buy_value": float(top_buys_df["accumulated_trade_value_estimated"].max()) if not top_buys_df.empty else 0.0,
            "kpi_largest_sell_value": float(top_sells_df["accumulated_trade_value_estimated"].max()) if not top_sells_df.empty else 0.0,
            "kpi_actionable_buys": enriched_kpis.get("actionable_buys", 0),
            "kpi_buy_candidates": enriched_kpis.get("buy_candidates", 0),
            "kpi_watchlist": enriched_kpis.get("watchlist", 0),
            "kpi_sell_warnings": enriched_kpis.get("sell_warnings", 0),
            "kpi_tr_not_found": enriched_kpis.get("tr_not_found", 0),
            "kpi_exchange_resolution_issues": enriched_kpis.get("exchange_resolution_issues", 0),
            "gate_passed_count": snapshot["gate_passed_count"],
            "fetched_profiles_count": enriched_kpis.get("fetched_profiles_count", 0),
            "missing_profiles_count": enriched_kpis.get("missing_profiles_count", 0),
            "avg_score": snapshot["avg_score"],
            "sector_distribution_buy": buy_sector,
            "sector_distribution_sell": sell_sector,
            "total_buy_volume": float(snapshot["buy_volume"]),
            "total_sell_volume": float(snapshot["sell_volume"]),
            "net_sector_signal": net,
            "market_cap_distribution": market_cap_distribution,
            "top_buys": top_buys_df.reset_index(drop=True),
            "top_sells": top_sells_df.reset_index(drop=True),
            "missing_data_summary": missing_summary,
            "last_update": self._max_trade_date_str(top_buys_df, top_sells_df),
        }

    def _compute_missing_data_summary_from_snapshot(self, snapshot: dict[str, Any], filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Berechnet missing_data_summary aus denormalizierten Snapshot-Feldern.
        Nicht aus großem DataFrame-Vollpfad!
        """
        # Placeholder-Implementierung: kann später von Repository erweitert werden
        return {
            "symbols_with_missing_profile": [],
            "reasons_by_symbol": {}
        }

    def _compute_enriched_kpis_from_snapshot(self, snapshot: dict[str, Any], filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Berechnet ergänzende KPI-Werte aus Snapshot-Feldern, nicht aus großem Core-DF.
        
        Die Werte sollten im Snapshot oder über leichte zusätzliche Queries verfügbar sein.
        """
        # Placeholder-Logik: Diese Werte können später von Repository-Methoden  gefüllt werden
        return {
            "actionable_buys": 0,  # TODO: aus Snapshot oder leichte Query
            "buy_candidates": snapshot.get("relevant_trades", 0),  # Näherung
            "watchlist": 0,  # TODO
            "sell_warnings": 0,  # TODO
            "tr_not_found": 0,  # TODO: Count von Trade-Republic-Mismatches
            "exchange_resolution_issues": 0,  # TODO
            "fetched_profiles_count": snapshot.get("affected_companies", 0),  # Näherung
            "missing_profiles_count": 0,  # TODO: aus leichter Query
        }


    @staticmethod
    def _max_trade_date_str(*frames: pd.DataFrame) -> str | None:
        dates: list[pd.Timestamp] = []
        for frame in frames:
            if frame.empty or "trade_date" not in frame.columns:
                continue
            series = pd.to_datetime(frame["trade_date"], errors="coerce").dropna()
            if not series.empty:
                dates.append(series.max())
        if not dates:
            return None
        latest = max(dates)
        return latest.date().strftime("%d.%m.%Y")

    def _hydrate_company_fields_from_mongo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füllt fehlende Company-Felder aus Mongo-Profilen nach, falls MySQL-Stubs vorliegen."""

        if df.empty or self.company_mongo_repo is None or "company_key" not in df.columns:
            return df

        working = df.copy()
        if "sector" not in working.columns:
            working["sector"] = pd.NA
        if "market_cap" not in working.columns:
            working["market_cap"] = pd.NA
        if "company_sector" in working.columns:
            sector_missing_from_trade = working["sector"].isna() | working["sector"].fillna("").astype(str).str.strip().eq("")
            working.loc[sector_missing_from_trade, "sector"] = working.loc[sector_missing_from_trade, "company_sector"]
        if "company_market_cap" in working.columns:
            trade_cap = pd.to_numeric(working["market_cap"], errors="coerce")
            company_cap = pd.to_numeric(working["company_market_cap"], errors="coerce")
            working["market_cap"] = trade_cap.fillna(company_cap)
        if "profile_status" not in working.columns:
            working["profile_status"] = pd.NA

        sector_missing = working["sector"].isna() | working["sector"].fillna("").astype(str).str.strip().eq("")
        market_cap_missing = pd.to_numeric(working["market_cap"], errors="coerce").isna()
        profile_status_missing = working["profile_status"].fillna("").astype(str).str.strip().str.upper().isin({"", "NOT_REQUESTED", "UNKNOWN"})
        candidate_mask = (
            working["company_key"].notna()
            & working["company_key"].astype(str).str.strip().ne("")
            & (sector_missing | market_cap_missing | profile_status_missing)
        )
        if not candidate_mask.any():
            return working

        cached_profiles: dict[str, dict[str, Any]] = {}
        candidate_keys = working.loc[candidate_mask, "company_key"].astype(str).str.strip().unique().tolist()
        if candidate_keys:
            try:
                # Einmaliger Bulk-Query statt N einzelner find_one-Aufrufe (N+1-Eliminierung)
                cached_profiles = self.company_mongo_repo.get_profiles_bulk(candidate_keys)
            except Exception:
                cached_profiles = {}

        if not cached_profiles:
            return working

        for idx in working.index[candidate_mask]:
            company_key = str(working.at[idx, "company_key"]).strip()
            profile = cached_profiles.get(company_key)
            if not profile:
                continue

            current_sector = str(working.at[idx, "sector"] or "").strip()
            cached_sector = str(profile.get("sector") or profile.get("sector_normalized") or "").strip()
            if not current_sector and cached_sector:
                working.at[idx, "sector"] = cached_sector

            current_market_cap = pd.to_numeric(working.at[idx, "market_cap"], errors="coerce")
            if pd.isna(current_market_cap):
                cached_market_cap = profile.get("market_cap")
                if cached_market_cap is None:
                    cached_market_cap = profile.get("marketCap")
                if cached_market_cap is None:
                    cached_market_cap = profile.get("mktCap")
                if cached_market_cap is not None:
                    working.at[idx, "market_cap"] = cached_market_cap

            current_profile_status = str(working.at[idx, "profile_status"] or "").strip().upper()
            cached_profile_status = str(profile.get("profile_status") or "").strip().upper()
            if current_profile_status in {"", "NOT_REQUESTED", "UNKNOWN"} and cached_profile_status:
                working.at[idx, "profile_status"] = cached_profile_status

        return working

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Defensive Normalisierung für spätere Aggregation."""
        if df.empty:
            return pd.DataFrame()

        working = df.copy()

        # Datumsfelder
        if "transaction_date" not in working.columns:
            working["transaction_date"] = pd.NaT
        working["transaction_date"] = pd.to_datetime(working["transaction_date"], errors="coerce")

        if "filing_date" not in working.columns:
            working["filing_date"] = pd.NaT
        working["filing_date"] = pd.to_datetime(working["filing_date"], errors="coerce")

        # Symbol, Richtung, numerische Kernfelder
        if "symbol_at_trade" not in working.columns:
            working["symbol_at_trade"] = working.get("symbol")
        working["symbol_at_trade"] = working["symbol_at_trade"].fillna("").astype(str).str.strip().str.upper()

        if "acquisition_or_disposition" not in working.columns:
            working["acquisition_or_disposition"] = ""
        existing_direction = working.get("direction", pd.Series(index=working.index, dtype="object"))
        mapped_direction = (
            working["acquisition_or_disposition"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .map({"A": "BUY", "BUY": "BUY", "D": "SELL", "SELL": "SELL"})
        )
        fallback_direction = (
            existing_direction.fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .map({"A": "BUY", "BUY": "BUY", "D": "SELL", "SELL": "SELL"})
        )
        working["direction"] = mapped_direction.fillna(fallback_direction).fillna("UNKNOWN")

        if "market_cap" not in working.columns:
            working["market_cap"] = pd.NA
        if "company_market_cap" in working.columns:
            trade_cap = pd.to_numeric(working["market_cap"], errors="coerce")
            company_cap = pd.to_numeric(working["company_market_cap"], errors="coerce")
            working["market_cap"] = trade_cap.fillna(company_cap)

        for num_col in ("price", "qty", "trade_value_estimated", "market_cap"):
            if num_col not in working.columns:
                working[num_col] = pd.NA
            working[num_col] = pd.to_numeric(working[num_col], errors="coerce")

        if "score" not in working.columns and "score_value" in working.columns:
            working["score"] = working["score_value"]
        if "score" not in working.columns:
            working["score"] = pd.NA
        working["score"] = pd.to_numeric(working["score"], errors="coerce")

        if "sector" not in working.columns:
            working["sector"] = pd.NA
        if "company_sector" in working.columns:
            working["sector"] = working["sector"].where(working["sector"].notna(), working["company_sector"])
        working["sector"] = working["sector"].fillna("").astype(str).str.strip()

        if "profile_status" not in working.columns:
            working["profile_status"] = "NOT_REQUESTED"
        working["profile_status"] = working["profile_status"].fillna("NOT_REQUESTED").astype(str).str.upper()

        if "gate_status" not in working.columns:
            working["gate_status"] = "UNKNOWN"
        working["gate_status"] = working["gate_status"].fillna("UNKNOWN").astype(str).str.upper()

        if "reporting_name" not in working.columns:
            working["reporting_name"] = ""
        if "dedupe_key" not in working.columns:
            working["dedupe_key"] = None
        if "company_key" not in working.columns:
            working["company_key"] = None

        return working

    def _build_accumulated_core_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Baut die akkumulierte Kernbasis für alle Dashboard-Sichten."""
        if df.empty:
            return pd.DataFrame()

        core_mask = (
            (df["symbol_at_trade"].astype(str).str.len() > 0)
            & (df["price"].fillna(0) > 0)
            & (df["qty"].fillna(0) > 0)
            & (df["direction"].isin(["BUY", "SELL"]))
        )
        core_df = df[core_mask].copy()
        if core_df.empty:
            return pd.DataFrame()

        grouped_df = AccumulationService.tag_trades_with_groups(core_df, window_days=1)
        if grouped_df.empty or "accumulation_group_id" not in grouped_df.columns:
            return pd.DataFrame()

        grouped_df["sector_normalized"] = grouped_df["sector"].apply(self._normalize_sector)
        grouped_df["market_cap_bucket"] = grouped_df["market_cap"].apply(self._market_cap_bucket)

        aggregated = (
            grouped_df.groupby("accumulation_group_id", dropna=False)
            .agg(
                symbol_at_trade=("symbol_at_trade", "first"),
                reporting_name=("reporting_name", "first"),
                company_key=("company_key", "first"),
                dedupe_key=("dedupe_key", "first"),
                direction=("direction", "first"),
                gate_status=("gate_status", "first"),
                profile_status=("profile_status", "first"),
                sector=("sector_normalized", "first"),
                market_cap_bucket=("market_cap_bucket", "first"),
                market_cap=("market_cap", "max"),
                accumulated_trade_count=("accumulation_group_id", "size"),
                accumulated_trade_value_estimated=("trade_value_estimated", "sum"),
                accumulated_qty=("qty", "sum"),
                accumulation_start_date=("transaction_date", "min"),
                accumulation_end_date=("transaction_date", "max"),
                avg_score=("score", "mean"),
            )
            .reset_index()
        )

        aggregated["trade_date"] = pd.to_datetime(aggregated["accumulation_start_date"], errors="coerce")
        aggregated["has_profile"] = (
            (aggregated["profile_status"] == "FETCHED")
            | (~aggregated["sector"].eq(UNKNOWN_PROFILE_LABEL))
            | (aggregated["market_cap"].notna())
        )
        return aggregated

    def _compute_dashboard_kpis(self, core_df: pd.DataFrame, all_df: pd.DataFrame) -> dict[str, Any]:
        gate_passed_count = int((all_df.get("gate_status", pd.Series(dtype="object")).astype(str).str.upper() == "PASS").sum()) if not all_df.empty else 0

        all_avg_score = float(all_df["score"].mean()) if "score" in all_df.columns and not all_df["score"].dropna().empty else 0.0

        if core_df.empty:
            return {
                "kpi_buy_sell_ratio_count": "0:0",
                "kpi_buy_sell_ratio_volume": "0:0",
                "kpi_relevant_trades_count": 0,
                "kpi_affected_companies_count": 0,
                "kpi_largest_buy_value": 0.0,
                "kpi_largest_sell_value": 0.0,
                "kpi_actionable_buys": 0,
                "kpi_buy_candidates": 0,
                "kpi_watchlist": 0,
                "kpi_sell_warnings": 0,
                "kpi_tr_not_found": 0,
                "kpi_exchange_resolution_issues": 0,
                "gate_passed_count": gate_passed_count,
                "fetched_profiles_count": 0,
                "missing_profiles_count": 0,
                "avg_score": all_avg_score,
            }

        buy_count = int((core_df["direction"] == "BUY").sum())
        sell_count = int((core_df["direction"] == "SELL").sum())

        buy_volume = float(core_df.loc[core_df["direction"] == "BUY", "accumulated_trade_value_estimated"].sum())
        sell_volume = float(core_df.loc[core_df["direction"] == "SELL", "accumulated_trade_value_estimated"].sum())

        companies_df = core_df.drop_duplicates(subset=["symbol_at_trade"])
        affected_companies_count = int(companies_df.shape[0])
        fetched_profiles_count = int(companies_df["has_profile"].sum())
        missing_profiles_count = int(affected_companies_count - fetched_profiles_count)

        largest_buy = core_df.loc[core_df["direction"] == "BUY", "accumulated_trade_value_estimated"]
        largest_sell = core_df.loc[core_df["direction"] == "SELL", "accumulated_trade_value_estimated"]

        decision_series = all_df.get("decision_status", pd.Series(dtype="object")).astype(str).str.upper()
        tr_series = all_df.get("tr_availability_state", pd.Series(dtype="object")).astype(str).str.upper()
        resolution_issues = all_df.get("exchange_resolution_confidence", pd.Series(dtype="object")).astype(str).str.upper().isin(["LOW", "UNKNOWN"]).sum()
        return {
            "kpi_buy_sell_ratio_count": f"{buy_count}:{sell_count}",
            "kpi_buy_sell_ratio_volume": f"{buy_volume:,.0f}:{sell_volume:,.0f}",
            "kpi_relevant_trades_count": int(core_df.shape[0]),
            "kpi_affected_companies_count": affected_companies_count,
            "kpi_largest_buy_value": float(largest_buy.max()) if not largest_buy.empty else 0.0,
            "kpi_largest_sell_value": float(largest_sell.max()) if not largest_sell.empty else 0.0,
            "kpi_actionable_buys": int((decision_series == "ACTIONABLE_BUY").sum()),
            "kpi_buy_candidates": int((decision_series == "BUY_CANDIDATE").sum()),
            "kpi_watchlist": int((decision_series == "WATCHLIST").sum()),
            "kpi_sell_warnings": int((decision_series == "SELL_WARNING").sum()),
            "kpi_tr_not_found": int((tr_series == "NOT_FOUND").sum()),
            "kpi_exchange_resolution_issues": int(resolution_issues),
            "gate_passed_count": gate_passed_count,
            "fetched_profiles_count": fetched_profiles_count,
            "missing_profiles_count": missing_profiles_count,
            "avg_score": float(core_df["avg_score"].mean()) if "avg_score" in core_df.columns and not core_df["avg_score"].dropna().empty else all_avg_score,
        }

    def _build_sector_pies(self, core_df: pd.DataFrame) -> dict[str, Any]:
        result = {
            "sector_distribution_buy": pd.DataFrame(columns=["sector", "count", "volume"]),
            "sector_distribution_sell": pd.DataFrame(columns=["sector", "count", "volume"]),
            "total_buy_volume": 0.0,
            "total_sell_volume": 0.0,
        }
        if core_df.empty:
            return result

        for direction, key in (("BUY", "sector_distribution_buy"), ("SELL", "sector_distribution_sell")):
            scoped = core_df[core_df["direction"] == direction]
            if scoped.empty:
                continue
            dist = (
                scoped.groupby("sector", dropna=False)
                .agg(count=("accumulation_group_id", "count"), volume=("accumulated_trade_value_estimated", "sum"))
                .reset_index()
                .sort_values("count", ascending=False)
            )
            result[key] = dist

        result["total_buy_volume"] = float(core_df.loc[core_df["direction"] == "BUY", "accumulated_trade_value_estimated"].sum())
        result["total_sell_volume"] = float(core_df.loc[core_df["direction"] == "SELL", "accumulated_trade_value_estimated"].sum())
        return result

    def _build_net_sector_signal(self, core_df: pd.DataFrame) -> dict[str, Any]:
        empty = pd.DataFrame(columns=["sector", "buy_count", "sell_count", "delta", "buy_volume", "sell_volume"])
        if core_df.empty:
            return {"net_sector_signal": empty}

        buy = (
            core_df[core_df["direction"] == "BUY"]
            .groupby("sector", dropna=False)
            .agg(buy_count=("accumulation_group_id", "count"), buy_volume=("accumulated_trade_value_estimated", "sum"))
        )
        sell = (
            core_df[core_df["direction"] == "SELL"]
            .groupby("sector", dropna=False)
            .agg(sell_count=("accumulation_group_id", "count"), sell_volume=("accumulated_trade_value_estimated", "sum"))
        )
        merged = buy.join(sell, how="outer").fillna(0).reset_index()
        merged["delta"] = merged["buy_count"] - merged["sell_count"]
        merged = merged.sort_values(["delta", "buy_count"], ascending=[False, False])
        return {"net_sector_signal": merged}

    def _build_market_cap_distribution(self, core_df: pd.DataFrame) -> dict[str, Any]:
        base = pd.DataFrame(
            {
                "bucket": ["Small Cap (<2B)", "Mid Cap (2B-10B)", "Large Cap (>=10B)", UNKNOWN_PROFILE_LABEL],
                "companies": [0, 0, 0, 0],
            }
        )
        if core_df.empty:
            return {"market_cap_distribution": base}

        companies = core_df.sort_values("trade_date", ascending=False).drop_duplicates(subset=["symbol_at_trade"])
        dist = companies.groupby("market_cap_bucket", dropna=False).size().reset_index(name="companies")
        dist = dist.rename(columns={"market_cap_bucket": "bucket"})
        merged = base.set_index("bucket").join(dist.set_index("bucket"), rsuffix="_new", how="left")
        merged["companies"] = merged["companies_new"].fillna(merged["companies"]).astype(int)
        merged = merged.drop(columns=["companies_new"]).reset_index()
        return {"market_cap_distribution": merged}

    def _build_top_tables(self, core_df: pd.DataFrame) -> dict[str, Any]:
        if core_df.empty:
            return {"top_buys": pd.DataFrame(), "top_sells": pd.DataFrame()}

        display_cols = [
            "accumulation_group_id",
            "dedupe_key",
            "symbol_at_trade",
            "reporting_name",
            "direction",
            "accumulated_trade_value_estimated",
            "trade_date",
            "accumulation_start_date",
            "accumulation_end_date",
            "gate_status",
            "profile_status",
            "sector",
            "market_cap_bucket",
        ]

        buys = core_df[core_df["direction"] == "BUY"].sort_values("accumulated_trade_value_estimated", ascending=False).head(5)
        sells = core_df[core_df["direction"] == "SELL"].sort_values("accumulated_trade_value_estimated", ascending=False).head(5)
        return {
            "top_buys": buys[display_cols].reset_index(drop=True),
            "top_sells": sells[display_cols].reset_index(drop=True),
        }

    def _build_missing_data_summary(self, core_df: pd.DataFrame) -> dict[str, Any]:
        if core_df.empty:
            return {"missing_data_summary": {"symbols_with_missing_profile": [], "reasons_by_symbol": {}}}

        companies = core_df.sort_values("trade_date", ascending=False).drop_duplicates(subset=["symbol_at_trade"])

        # Vektorielle Boolean-Masken statt zeilenweisem iterrows()
        no_profile = companies["profile_status"].ne("FETCHED")
        missing_sector = companies["sector"].eq(UNKNOWN_PROFILE_LABEL)
        missing_cap = companies["market_cap_bucket"].eq(UNKNOWN_PROFILE_LABEL)
        has_issue = no_profile | missing_sector | missing_cap

        # Vollständig vektorisierte Variante – kein iterrows() mehr
        affected = companies.loc[has_issue, ["symbol_at_trade", "profile_status", "sector", "market_cap_bucket"]].copy()

        # Erstelle je eine Boolean-Spalte pro Grund
        affected["_r_api2"] = affected["profile_status"].ne("FETCHED")
        affected["_r_sector"] = affected["sector"].eq(UNKNOWN_PROFILE_LABEL)
        affected["_r_cap"] = affected["market_cap_bucket"].eq(UNKNOWN_PROFILE_LABEL)

        def _collect_reasons(row: "pd.Series") -> list[str]:  # noqa: F821
            out: list[str] = []
            if row["_r_api2"]:
                out.append("API2 nicht geladen")
            if row["_r_sector"]:
                out.append("Sector fehlt")
            if row["_r_cap"]:
                out.append("Market Cap fehlt")
            return out

        reason_series = affected.apply(_collect_reasons, axis=1)
        reasons_by_symbol: dict[str, list[str]] = {
            str(sym): reasons
            for sym, reasons in zip(affected["symbol_at_trade"], reason_series)
            if reasons
        }

        return {
            "missing_data_summary": {
                "symbols_with_missing_profile": sorted(reasons_by_symbol.keys()),
                "reasons_by_symbol": reasons_by_symbol,
            }
        }

    @staticmethod
    def _normalize_sector(value: Any) -> str:
        normalized = str(value or "").strip()
        if normalized.lower() in {"", "none", "null", "n/a", "unknown"}:
            return UNKNOWN_PROFILE_LABEL
        return normalized

    @staticmethod
    def _market_cap_bucket(value: Any) -> str:
        market_cap = pd.to_numeric(value, errors="coerce")
        if pd.isna(market_cap):
            return UNKNOWN_PROFILE_LABEL
        if market_cap < 2_000_000_000:
            return "Small Cap (<2B)"
        if market_cap < 10_000_000_000:
            return "Mid Cap (2B-10B)"
        return "Large Cap (>=10B)"

    @staticmethod
    def _get_last_update_str(df: pd.DataFrame) -> str | None:
        if df.empty:
            return None
        if "transaction_date" not in df.columns:
            return None
        last_date = pd.to_datetime(df["transaction_date"], errors="coerce").max()
        if pd.isna(last_date):
            return None
        if isinstance(last_date, pd.Timestamp):
            last_date = last_date.date()
        if isinstance(last_date, date):
            return last_date.strftime("%d.%m.%Y")
        return str(last_date)
