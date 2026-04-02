"""Tests für das Laden und Validieren der Umgebungs-Settings."""

from __future__ import annotations

from src.config.settings import Settings


def test_settings_from_env(monkeypatch) -> None:
    """Prüft, dass alle relevanten MySQL-Settings korrekt aus Env gelesen werden."""

    monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_DATABASE", "finanzport_academic")
    monkeypatch.setenv("MYSQL_USER", "tester")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")
    monkeypatch.setenv("MYSQL_CONNECT_TIMEOUT", "15")
    monkeypatch.setenv("MYSQL_CREATE_DATABASE", "false")
    monkeypatch.setenv("MYSQL_SSL_DISABLED", "true")
    monkeypatch.setenv("MYSQL_SSL_CA", "")
    monkeypatch.setenv("MYSQL_SSL_CERT", "")
    monkeypatch.setenv("MYSQL_SSL_KEY", "")

    settings = Settings.from_env()

    assert settings.mysql_host == "127.0.0.1"
    assert settings.mysql_port == 3307
    assert settings.mysql_database == "finanzport_academic"
    assert settings.mysql_user == "tester"
    assert settings.mysql_password == "secret"
    assert settings.mysql_connect_timeout == 15
    assert settings.mysql_create_database is False
    assert settings.mysql_ssl_disabled is True
    assert settings.mysql_ssl_ca is None
    assert settings.mysql_ssl_cert is None
    assert settings.mysql_ssl_key is None


def test_mysql_connection_kwargs_ssl_disabled(monkeypatch) -> None:
    """Prüft, dass Verbindungsparameter für deaktiviertes SSL korrekt gesetzt werden."""

    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_DATABASE", "finanzport_academic")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_PASSWORD", "change_me")
    monkeypatch.setenv("MYSQL_CONNECT_TIMEOUT", "10")
    monkeypatch.setenv("MYSQL_CREATE_DATABASE", "false")
    monkeypatch.setenv("MYSQL_SSL_DISABLED", "true")

    settings = Settings.from_env()
    kwargs = settings.mysql_connection_kwargs(include_database=True)

    assert kwargs["host"] == "localhost"
    assert kwargs["database"] == "finanzport_academic"
    assert kwargs["ssl_disabled"] is True


# TODO: Integrationstest mit echter Uni-MySQL-Verbindung ergänzen, sobald Zugangsdaten vorliegen.
