"""Service für persistente App-Einstellungen und Filter in MySQL."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from src.config.settings import AppSettings
from src.domain_rules import ScoreGatePolicy
from src.db.repositories.settings_repository import (
    AppFilterSettingsRepository,
    AppRuntimePreferencesRepository,
)
from src.utils.logging_utils import get_logger

LOGGER = get_logger(__name__)


def _normalize_score_gate_policy(policy: ScoreGatePolicy) -> ScoreGatePolicy:
    if policy.gate_min_trade_value < 100_000:
        return replace(policy, gate_min_trade_value=100_000)
    return policy


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
    api2_firing_mode: str = "ONLY PASS"
    auto_import_enabled: bool = False
    auto_import_interval_minutes: int = 15
    auto_import_on_start: bool = False
    last_auto_import_at: str | None = None


class AppSettingsService:
    """Lädt/speichert Laufzeit-Einstellungen und UI-Filter mit Env-Defaults."""

    RUNTIME_PREFERENCE_KEY = "runtime_settings"
    SCORE_GATE_POLICY_KEY = "score_gate_policy"
    SESSION_RUNTIME_KEY = "_session_runtime_settings"
    SESSION_SCORE_POLICY_KEY = "_session_score_gate_policy"
    SESSION_FILTER_PREFIX = "_session_filter"

    def __init__(
        self,
        runtime_repo: AppRuntimePreferencesRepository | None,
        filter_repo: AppFilterSettingsRepository | None,
        defaults: AppSettings,
    ) -> None:
        self.runtime_repo = runtime_repo
        self.filter_repo = filter_repo
        self.defaults = defaults

    @staticmethod
    def _session_state():
        try:
            import streamlit as st
            return st.session_state
        except Exception:
            return None

    @classmethod
    def _session_filter_key(cls, setting_scope: str, setting_key: str) -> str:
        return f"{cls.SESSION_FILTER_PREFIX}:{setting_scope}:{setting_key}"

    def is_persistence_available(self) -> bool:
        return self.runtime_repo is not None

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
            api2_firing_mode="ONLY PASS",
            auto_import_enabled=False,
            auto_import_interval_minutes=15,
            auto_import_on_start=False,
            last_auto_import_at=None,
        )

    def load(self) -> RuntimeSettings:
        session = self._session_state()
        if session and self.SESSION_RUNTIME_KEY in session:
            payload = session[self.SESSION_RUNTIME_KEY]
            if isinstance(payload, RuntimeSettings):
                return payload
            if isinstance(payload, dict):
                base = asdict(self.defaults_runtime())
                base.update({k: v for k, v in payload.items() if k in base})
                try:
                    return RuntimeSettings(**base)
                except Exception:
                    LOGGER.warning("Session-Runtime-Settings sind ungueltig. Verwende Defaults.")
                    return self.defaults_runtime()

        if self.runtime_repo is None:
            return self.defaults_runtime()
        try:
            payload = self.runtime_repo.load(self.RUNTIME_PREFERENCE_KEY)
        except Exception as exc:
            LOGGER.warning(
                "Runtime-Settings konnten nicht geladen werden. Verwende Defaults. error=%s",
                exc,
            )
            return self.defaults_runtime()
        if not payload or not isinstance(payload, dict):
            LOGGER.info("Runtime-Settings nicht vorhanden oder ungueltig. Verwende Defaults.")
            return self.defaults_runtime()
        base = asdict(self.defaults_runtime())
        base.update({k: v for k, v in payload.items() if k in base})
        try:
            return RuntimeSettings(**base)
        except Exception as exc:
            LOGGER.warning(
                "Runtime-Settings Payload ungueltig. Verwende Defaults. error=%s",
                exc,
            )
            return self.defaults_runtime()

    def defaults_score_gate_policy(self) -> ScoreGatePolicy:
        return _normalize_score_gate_policy(ScoreGatePolicy(
            gate_validation_status_required="VALID",
            gate_form_type_required="4",
            gate_security_name_required="",
            gate_allowed_acquisition_or_disposition=tuple(self.defaults.gate.allowed_acquisition_or_disposition),
            gate_excluded_transaction_types=("A-Award", "M-Exempt"),
            gate_min_trade_value=int(self.defaults.gate.min_trade_value),
        ))

    def load_score_gate_policy(self) -> ScoreGatePolicy:
        session = self._session_state()
        if session and self.SESSION_SCORE_POLICY_KEY in session:
            payload = session[self.SESSION_SCORE_POLICY_KEY]
            if isinstance(payload, ScoreGatePolicy):
                return _normalize_score_gate_policy(payload)
            if isinstance(payload, dict):
                base = asdict(self.defaults_score_gate_policy())
                base.update({k: v for k, v in payload.items() if k in base})
                try:
                    return _normalize_score_gate_policy(ScoreGatePolicy(**base))
                except Exception:
                    LOGGER.warning("Session-Score/Gate-Policy ist ungueltig. Verwende Defaults.")
                    return self.defaults_score_gate_policy()

        if self.runtime_repo is None:
            return self.defaults_score_gate_policy()
        try:
            payload = self.runtime_repo.load(self.SCORE_GATE_POLICY_KEY)
        except Exception as exc:
            LOGGER.warning(
                "Score/Gate-Policy konnte nicht geladen werden. Verwende Defaults. error=%s",
                exc,
            )
            return self.defaults_score_gate_policy()
        if not payload or not isinstance(payload, dict):
            LOGGER.info("Score/Gate-Policy nicht vorhanden oder ungueltig. Verwende Defaults.")
            return self.defaults_score_gate_policy()
        base = asdict(self.defaults_score_gate_policy())
        base.update({k: v for k, v in payload.items() if k in base})
        for key in ("gate_allowed_acquisition_or_disposition", "gate_excluded_transaction_types"):
            if isinstance(base.get(key), list):
                base[key] = tuple(base[key])
        try:
            policy = _normalize_score_gate_policy(ScoreGatePolicy(**base))
        except Exception as exc:
            LOGGER.warning(
                "Score/Gate-Policy Payload ungueltig. Verwende Defaults. error=%s",
                exc,
            )
            return self.defaults_score_gate_policy()
        return policy

    def save_score_gate_policy(self, policy: ScoreGatePolicy) -> None:
        policy = _normalize_score_gate_policy(policy)
        session = self._session_state()
        if session is not None:
            session[self.SESSION_SCORE_POLICY_KEY] = policy.to_dict()

        if self.runtime_repo is None:
            return
        try:
            self.runtime_repo.upsert(
                {
                    "preference_key": self.SCORE_GATE_POLICY_KEY,
                    "preference_value_json": policy.to_dict(),
                }
            )
        except Exception as exc:
            LOGGER.warning("Score/Gate-Policy konnte nicht persistent gespeichert werden. Bleibt in der Sitzung. error=%s", exc)

    def save(self, runtime: RuntimeSettings) -> None:
        session = self._session_state()
        if session is not None:
            session[self.SESSION_RUNTIME_KEY] = asdict(runtime)

        if self.runtime_repo is None:
            return
        try:
            self.runtime_repo.upsert(
                {
                    "preference_key": self.RUNTIME_PREFERENCE_KEY,
                    "preference_value_json": asdict(runtime),
                }
            )
        except Exception as exc:
            LOGGER.warning("Runtime-Settings konnten nicht persistent gespeichert werden. Bleiben in der Sitzung. error=%s", exc)

    def reset(self) -> RuntimeSettings:
        runtime = self.defaults_runtime()
        self.save(runtime)
        return runtime

    def load_filter(self, setting_scope: str, setting_key: str, default: Any) -> Any:
        """Lädt einen gespeicherten Filterwert oder liefert den Default."""
        session = self._session_state()
        session_key = self._session_filter_key(setting_scope, setting_key)
        if session and session_key in session:
            return session[session_key]

        if self.filter_repo is None:
            return default
        try:
            payload = self.filter_repo.load(setting_scope, setting_key)
        except Exception as exc:
            LOGGER.warning(
                "Filter konnte nicht geladen werden (scope=%s key=%s). Verwende Default. error=%s",
                setting_scope,
                setting_key,
                exc,
            )
            return default
        return default if payload is None else payload

    def save_filter(self, setting_scope: str, setting_key: str, value: Any) -> None:
        """Speichert einen Filterwert per Upsert (Update statt Insert)."""
        session = self._session_state()
        if session is not None:
            session[self._session_filter_key(setting_scope, setting_key)] = value

        if self.filter_repo is None:
            return
        try:
            self.filter_repo.upsert(
                {
                    "setting_scope": setting_scope,
                    "setting_key": setting_key,
                    "setting_value_json": value,
                }
            )
        except Exception as exc:
            LOGGER.warning(
                "Filter konnte nicht persistent gespeichert werden (scope=%s key=%s). Bleibt in der Sitzung. error=%s",
                setting_scope,
                setting_key,
                exc,
            )
