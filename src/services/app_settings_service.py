"""Service für persistente Gate-/Profil-Einstellungen in MongoDB."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.config.settings import AppSettings
from src.db.mongo_repository import AppSettingsMongoRepository


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
    """Lädt/speichert Laufzeit-Einstellungen mit Env-Defaults."""

    def __init__(self, repo: AppSettingsMongoRepository | None, defaults: AppSettings) -> None:
        self.repo = repo
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
        if self.repo is None:
            return self.defaults_runtime()
        payload = self.repo.load()
        if not payload:
            return self.defaults_runtime()
        base = asdict(self.defaults_runtime())
        base.update({k: v for k, v in payload.items() if k in base})
        return RuntimeSettings(**base)

    def save(self, runtime: RuntimeSettings) -> None:
        if self.repo is None:
            return
        payload: dict[str, Any] = asdict(runtime)
        payload["_id"] = AppSettingsMongoRepository.SETTINGS_ID
        self.repo.save(payload)

    def reset(self) -> RuntimeSettings:
        if self.repo is not None:
            self.repo.reset()
        return self.defaults_runtime()
