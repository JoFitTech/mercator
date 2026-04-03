"""Tests fuer den MySQL-Init-CLI-Entry-Point."""

from src.scripts import init_mysql_schema


class _DummySettings:
    mysql = "dummy"


class _ClientSuccess:
    """Testdouble fuer einen erfolgreichen Init-Lauf."""

    target_name = "local"

    def test_connection(self):
        return True, "Connection successful."

    def initialize_schema(self):
        return None


class _ClientConnectionFail:
    """Testdouble fuer eine fehlschlagende Verbindung."""

    target_name = "local"

    def test_connection(self):
        return False, "Connection failed"

    def initialize_schema(self):
        return None


def test_initialize_mysql_schema_success(monkeypatch, capsys):
    """Prueft Exit-Code 0 bei erfolgreicher Initialisierung via Resolver."""

    monkeypatch.setattr(init_mysql_schema, "load_settings", lambda: _DummySettings())
    monkeypatch.setattr(init_mysql_schema, "resolve_active_target", lambda mysql_settings: ("local", _ClientSuccess(), ["ok"]))

    exit_code = init_mysql_schema.initialize_mysql_schema()
    _ = capsys.readouterr().out

    assert exit_code == 0


def test_initialize_mysql_schema_for_target_connection_fail(monkeypatch, capsys):
    """Prueft Exit-Code 1 bei Verbindungsfehler fuer explizites Ziel."""

    monkeypatch.setattr(init_mysql_schema, "load_settings", lambda: _DummySettings())
    monkeypatch.setattr(init_mysql_schema, "build_mysql_client_for_target", lambda mysql_settings, target_name: _ClientConnectionFail())

    exit_code = init_mysql_schema.initialize_mysql_schema_for_target("uni")
    _ = capsys.readouterr().out

    assert exit_code == 1


def test_main_uses_initialize_exit_code(monkeypatch):
    """Prueft, dass main den Exit-Code von initialize_mysql_schema weitergibt."""

    monkeypatch.setattr(init_mysql_schema, "initialize_mysql_schema", lambda: 7)

    try:
        init_mysql_schema.main()
    except SystemExit as exc:
        assert exc.code == 7
    else:  # pragma: no cover - defensiver Pfad fuer fehlerhafte Exit-Weitergabe
        assert False, "main() sollte SystemExit ausloesen"
