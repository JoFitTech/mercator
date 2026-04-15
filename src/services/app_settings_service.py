"""Service für persistente App-Einstellungen und Filter in MySQL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.config.settings import AppSettings
from src.domain_rules import ScoreGatePolicy
from src.db.mysql_repository import (
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
)


@dataclass(slots=True)
class RuntimeSettings:
    min_trade_value: int
    require_purchase_event: bool
    require_common_stock: bool
    allowed_acquisition_or_disposition: tuple[str, ...]
    allowed_transaction_types: tuple[str, ...]
    profile_gate_filter_statuses: tuple[str, ...]
    profile_ttl_days: int
    lookup_mode: str


class AppSettingsService:
    """Lädt/speichert Laufzeit-Einstellungen und UI-Filter mit Env-Defaults."""

    RUNTIME_PREFERENCE_KEY = "runtime_settings"
    SCORE_GATE_POLICY_KEY = "score_gate_policy"

    def __init__(
        self,
        runtime_repo: AppRuntimePreferencesRepository | None,
        filter_repo: AppFilterSettingsRepository | None,
        defaults: AppSettings,
    ) -> None:
        self.runtime_repo = runtime_repo
        self.filter_repo = filter_repo
        self.defaults = defaults

    def defaults_runtime(self) -> RuntimeSettings:
        return RuntimeSettings(
            min_trade_value=self.defaults.gate.min_trade_value,
            require_purchase_event=self.defaults.gate.require_purchase_event,
            require_common_stock=self.defaults.gate.require_common_stock,
            allowed_acquisition_or_disposition=self.defaults.gate.allowed_acquisition_or_disposition,
            allowed_transaction_types=self.defaults.gate.allowed_transaction_types,
            profile_gate_filter_statuses=self.defaults.fmp.profile_gate_filter_statuses,
            profile_ttl_days=self.defaults.fmp.profile_ttl_days,
            lookup_mode=self.defaults.fmp.lookup_mode,
        )

    def load(self) -> RuntimeSettings:
        if self.runtime_repo is None:
            return self.defaults_runtime()
        payload = self.runtime_repo.load(self.RUNTIME_PREFERENCE_KEY)
        if not payload or not isinstance(payload, dict):
            return self.defaults_runtime()
        base = asdict(self.defaults_runtime())
        base.update({k: v for k, v in payload.items() if k in base})
        return RuntimeSettings(**base)

    def defaults_score_gate_policy(self) -> ScoreGatePolicy:
        return ScoreGatePolicy(
            gate_validation_status_required="VALID",
            gate_form_type_required="4",
            gate_security_name_required="Common Stock",
            gate_allowed_acquisition_or_disposition=tuple(self.defaults.gate.allowed_acquisition_or_disposition),
            gate_excluded_transaction_types=("A-Award", "M-Exempt"),
            gate_min_trade_value=int(self.defaults.gate.min_trade_value),
        )

    def load_score_gate_policy(self) -> ScoreGatePolicy:
        if self.runtime_repo is None:
            return self.defaults_score_gate_policy()
        payload = self.runtime_repo.load(self.SCORE_GATE_POLICY_KEY)
        if not payload or not isinstance(payload, dict):
            return self.defaults_score_gate_policy()
        base = asdict(self.defaults_score_gate_policy())
        base.update({k: v for k, v in payload.items() if k in base})
        for key in ("gate_allowed_acquisition_or_disposition", "gate_excluded_transaction_types"):
            if isinstance(base.get(key), list):
                base[key] = tuple(base[key])
        return ScoreGatePolicy(**base)

    def save_score_gate_policy(self, policy: ScoreGatePolicy) -> None:
        if self.runtime_repo is None:
            return
        self.runtime_repo.upsert(
            {
                "preference_key": self.SCORE_GATE_POLICY_KEY,
                "preference_value_json": policy.to_dict(),
            }
        )

    def save(self, runtime: RuntimeSettings) -> None:
        if self.runtime_repo is None:
            return
        self.runtime_repo.upsert(
            {
                "preference_key": self.RUNTIME_PREFERENCE_KEY,
                "preference_value_json": asdict(runtime),
            }
        )

    def reset(self) -> RuntimeSettings:
        runtime = self.defaults_runtime()
        self.save(runtime)
        return runtime

    def load_filter(self, setting_scope: str, setting_key: str, default: Any) -> Any:
        """Lädt einen gespeicherten Filterwert oder liefert den Default."""

        if self.filter_repo is None:
            return default
        payload = self.filter_repo.load(setting_scope, setting_key)
        return default if payload is None else payload

    def save_filter(self, setting_scope: str, setting_key: str, value: Any) -> None:
        """Speichert einen Filterwert per Upsert (Update statt Insert)."""

        if self.filter_repo is None:
            return
        self.filter_repo.upsert(
            {
                "setting_scope": setting_scope,
                "setting_key": setting_key,
                "setting_value_json": value,
            }
        )
