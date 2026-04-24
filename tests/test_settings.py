"""Tests für das Laden und Validieren der Umgebungs-Settings."""

from __future__ import annotations

import pytest

from src.config import settings as settings_module
from src.config.settings import (
    MongoConfig,
    MongoSettings,
    Settings,
    SettingsError,
    load_settings,
    validate_fmp_api_key,
)


def test_settings_from_env_reads_targets(monkeypatch) -> None:
    """Prüft, dass beide MySQL-Targets korrekt aus Env geladen werden."""

    monkeypatch.setenv("MYSQL_ACTIVE_TARGET", "uni")
    monkeypatch.setenv("MYSQL_AUTO_FALLBACK_TO_LOCAL", "true")
    monkeypatch.setenv("MYSQL_SYNC_ENABLED", "false")

    monkeypatch.setenv("LOCAL_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_MYSQL_PORT", "3307")
    monkeypatch.setenv("LOCAL_MYSQL_DATABASE", "mercator_local")
    monkeypatch.setenv("LOCAL_MYSQL_USER", "local_user")
    monkeypatch.setenv("LOCAL_MYSQL_PASSWORD", "local_secret")
    monkeypatch.setenv("LOCAL_MYSQL_CONNECT_TIMEOUT", "15")

    monkeypatch.setenv("UNI_MYSQL_HOST", "uni-db")
    monkeypatch.setenv("UNI_MYSQL_PORT", "3306")
    monkeypatch.setenv("UNI_MYSQL_DATABASE", "mercator_uni")
    monkeypatch.setenv("UNI_MYSQL_USER", "uni_user")
    monkeypatch.setenv("UNI_MYSQL_PASSWORD", "uni_secret")
    monkeypatch.setenv("UNI_MYSQL_CONNECT_TIMEOUT", "5")

    settings = Settings.from_env()

    assert settings.mysql_active_target == "uni"
    assert settings.mysql_auto_fallback_to_local is True
    assert settings.mysql_sync_enabled is False

    assert settings.local_mysql.host == "127.0.0.1"
    assert settings.local_mysql.port == 3307
    assert settings.local_mysql.database == "mercator_local"
    assert settings.local_mysql.user == "local_user"
    assert settings.local_mysql.password == "local_secret"
    assert settings.local_mysql.connect_timeout == 15

    assert settings.uni_mysql.host == "uni-db"
    assert settings.uni_mysql.database == "mercator_uni"


def test_mysql_connection_kwargs_ssl_disabled(monkeypatch) -> None:
    """Prüft, dass Verbindungsparameter bei deaktiviertem SSL korrekt gesetzt werden."""

    monkeypatch.setenv("LOCAL_MYSQL_HOST", "localhost")
    monkeypatch.setenv("LOCAL_MYSQL_PORT", "3306")
    monkeypatch.setenv("LOCAL_MYSQL_DATABASE", "mercator")
    monkeypatch.setenv("LOCAL_MYSQL_USER", "root")
    monkeypatch.setenv("LOCAL_MYSQL_PASSWORD", "change_me")
    monkeypatch.setenv("LOCAL_MYSQL_SSL_DISABLED", "true")

    settings = Settings.from_env()
    kwargs = settings.local_mysql.mysql_connection_kwargs(include_database=True)

    assert kwargs["host"] == "localhost"
    assert kwargs["database"] == "mercator"
    assert kwargs["ssl_disabled"] is True


def test_settings_uses_legacy_mysql_env_for_local_target(monkeypatch) -> None:
    """Prüft die Kompatibilität mit alten MYSQL_* Variablen für das lokale Ziel."""

    monkeypatch.setenv("MYSQL_HOST", "legacy-host")
    monkeypatch.setenv("MYSQL_PORT", "3310")
    monkeypatch.setenv("MYSQL_DATABASE", "legacy_db")
    monkeypatch.setenv("MYSQL_USER", "legacy_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "legacy_password")
    monkeypatch.delenv("LOCAL_MYSQL_HOST", raising=False)
    monkeypatch.delenv("LOCAL_MYSQL_PORT", raising=False)
    monkeypatch.delenv("LOCAL_MYSQL_DATABASE", raising=False)
    monkeypatch.delenv("LOCAL_MYSQL_USER", raising=False)
    monkeypatch.delenv("LOCAL_MYSQL_PASSWORD", raising=False)

    settings = Settings.from_env()

    assert settings.local_mysql.host == "legacy-host"
    assert settings.local_mysql.port == 3310
    assert settings.local_mysql.database == "legacy_db"
    assert settings.local_mysql.user == "legacy_user"
    assert settings.local_mysql.password == "legacy_password"


def test_load_settings_reads_gate_and_profile_filters(monkeypatch) -> None:
    """Prueft, dass Gate-Regeln und Profil-Fetch-Statusfilter aus Env geladen werden."""

    monkeypatch.setenv("LOCAL_MYSQL_HOST", "localhost")
    monkeypatch.setenv("LOCAL_MYSQL_PORT", "3306")
    monkeypatch.setenv("LOCAL_MYSQL_DATABASE", "mercator")
    monkeypatch.setenv("LOCAL_MYSQL_USER", "root")
    monkeypatch.setenv("LOCAL_MYSQL_PASSWORD", "change_me")
    monkeypatch.setenv("FMP_API_KEY", "demo")
    monkeypatch.setenv("GATE_MIN_TRADE_VALUE", "25000")
    monkeypatch.setenv("GATE_REQUIRE_PURCHASE_EVENT", "false")
    monkeypatch.setenv("GATE_REQUIRE_COMMON_STOCK", "false")
    monkeypatch.setenv("PROFILE_GATE_FILTER_STATUSES", "PASS,PENDING")

    settings = load_settings()

    assert settings.gate.min_trade_value == 25000
    assert settings.gate.require_purchase_event is False
    assert settings.gate.require_common_stock is False
    assert settings.fmp.profile_gate_filter_statuses == ("PASS", "PENDING")


def test_settings_parses_bool_and_int_values(monkeypatch) -> None:
    """Prüft die Konvertierung von booleschen und numerischen Env-Werten."""

    monkeypatch.setenv("MYSQL_AUTO_FALLBACK_TO_LOCAL", "false")
    monkeypatch.setenv("MYSQL_SYNC_ENABLED", "true")
    monkeypatch.setenv("LOCAL_MYSQL_PORT", "3309")
    monkeypatch.setenv("LOCAL_MYSQL_CONNECT_TIMEOUT", "12")

    settings = Settings.from_env()

    assert settings.mysql_auto_fallback_to_local is False
    assert settings.mysql_sync_enabled is True
    assert settings.local_mysql.port == 3309
    assert settings.local_mysql.connect_timeout == 12


def test_settings_raises_on_invalid_boolean(monkeypatch) -> None:
    """Prüft die Fehlermeldung bei ungültigen Bool-Werten."""

    monkeypatch.setenv("MYSQL_AUTO_FALLBACK_TO_LOCAL", "sometimes")
    with pytest.raises(SettingsError):
        Settings.from_env()


@pytest.mark.parametrize(
    "bad_key",
    ["", "   ", "YOUR_API_KEY", "changeme", "placeholder", "None", "null", "demo"],
)
def test_validate_fmp_api_key_rejects_placeholders(bad_key: str) -> None:
    """Prueft die Erkennung typischer Platzhalterwerte fuer FMP_API_KEY."""

    with pytest.raises(ValueError):
        validate_fmp_api_key(bad_key)


def test_load_settings_reads_fmp_api_key_from_streamlit_secrets(monkeypatch) -> None:
    """Prueft Fallback auf Streamlit-Secrets, wenn kein ENV-Wert gesetzt ist."""

    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.setattr(settings_module, "_read_streamlit_secret", lambda name: "secret_from_streamlit")

    app_settings = load_settings()

    assert app_settings.fmp.api_key == "secret_from_streamlit"
    assert app_settings.fmp.api_key_source == "streamlit_secrets"


def test_load_settings_reads_review_mode_flags(monkeypatch) -> None:
    monkeypatch.setenv("MERCATOR_REVIEW_MODE", "true")
    monkeypatch.setenv("MERCATOR_DISABLE_IMPORT", "true")
    monkeypatch.setenv("MERCATOR_DISABLE_ADMIN_DELETE", "true")
    monkeypatch.setenv("MERCATOR_UI_TEST_MODE", "true")

    settings = load_settings()

    assert settings.review_mode is True
    assert settings.disable_import is True
    assert settings.disable_admin_delete is True
    assert settings.ui_test_mode is True


def test_load_settings_forces_admin_delete_block_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MERCATOR_DISABLE_ADMIN_DELETE", "false")

    settings = load_settings()

    assert settings.disable_admin_delete is True


def test_load_settings_forces_public_share_off_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_PUBLIC_SHARE", "true")

    settings = load_settings()

    assert settings.public_share.enabled is False


def test_load_settings_forces_cloudflare_public_share_to_host_mode(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_PUBLIC_SHARE", "true")
    monkeypatch.setenv("PUBLIC_SHARE_PROVIDER", "cloudflare")
    monkeypatch.setenv("PUBLIC_SHARE_EXECUTION_MODE", "container")

    settings = load_settings()

    assert settings.public_share.provider == "cloudflare"
    assert settings.public_share.execution_mode == "host"


def test_mongo_config_trims_whitespace_in_uri(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv(
        "UNI_MONGO_URI",
        "  mongodb://user:pw@mongo.uni.example:27017/?authSource=admin  ",
    )
    monkeypatch.setenv("UNI_MONGO_DATABASE", "uni")

    config = MongoConfig.from_env()

    assert config.uri == "mongodb://user:pw@mongo.uni.example:27017/?authSource=admin"
    assert config.database == "uni"


def test_mongo_config_rejects_uri_with_line_break(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv(
        "UNI_MONGO_URI",
        "mongodb://user:pw@mongo.uni.example:27017/\n?authSource=admin",
    )
    monkeypatch.setenv("UNI_MONGO_DATABASE", "uni")

    with pytest.raises(SettingsError, match="line break"):
        MongoConfig.from_env()


def test_mongo_config_rejects_database_mismatch_between_uri_and_env(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv(
        "UNI_MONGO_URI",
        "mongodb://user:pw@mongo.uni.example:27017/admin?authSource=admin",
    )
    monkeypatch.setenv("UNI_MONGO_DATABASE", "uni")

    with pytest.raises(SettingsError, match="database mismatch"):
        MongoConfig.from_env()


def test_mongo_config_requires_uni_database_for_uni_target(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv(
        "UNI_MONGO_URI",
        "mongodb://user:pw@mongo.uni.example:27017/?authSource=admin",
    )
    monkeypatch.setenv("UNI_MONGO_DATABASE", "   ")

    with pytest.raises(SettingsError, match="UNI_MONGO_DATABASE"):
        MongoConfig.from_env()


def test_mongo_settings_reads_auto_fallback_flag(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv("MONGO_AUTO_FALLBACK_TO_LOCAL", "false")
    monkeypatch.setenv("UNI_MONGO_URI", "mongodb://user:pw@mongo.uni.example:27017/?authSource=admin")
    monkeypatch.setenv("UNI_MONGO_DATABASE", "uni")
    monkeypatch.setenv("LOCAL_MONGO_URI", "mongodb://localhost:27017/")
    monkeypatch.setenv("LOCAL_MONGO_DATABASE", "mercator")

    mongo_settings = MongoSettings.from_env()

    assert mongo_settings.mongo_auto_fallback_to_local is False


def test_mongo_settings_loads_both_targets(monkeypatch) -> None:
    monkeypatch.setenv("MONGO_ACTIVE_TARGET", "uni")
    monkeypatch.setenv("MONGO_AUTO_FALLBACK_TO_LOCAL", "true")
    monkeypatch.setenv("LOCAL_MONGO_URI", "mongodb://localhost:27017/")
    monkeypatch.setenv("LOCAL_MONGO_DATABASE", "mercator")
    monkeypatch.setenv("UNI_MONGO_URI", "mongodb://user:pw@mongo.uni.example:27017/?authSource=admin")
    monkeypatch.setenv("UNI_MONGO_DATABASE", "uni")

    mongo_settings = MongoSettings.from_env()

    assert mongo_settings.local_mongo.database == "mercator"
    assert mongo_settings.uni_mongo.database == "uni"


# Offene Testpunkte stehen zentral in ``docs/todos_offene_fragen.md``.
