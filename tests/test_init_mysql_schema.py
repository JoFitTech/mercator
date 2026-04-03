"""Tests fuer den MySQL-Init-CLI-Entry-Point."""

from src.scripts import init_mysql_schema


class _DummySettings:
    mysql = "dummy"


class _ClientSuccess:
    """Testdouble fuer einen erfolgreichen Init-Lauf."""

    def __init__(self, settings):
        self._settings = settings
        self.initialize_called = False

    def test_connection(self):
        return True, "Connection successful."

    def initialize_schema(self):
        self.initialize_called = True


class _ClientConnectionFail:
    """Testdouble fuer eine fehlschlagende Verbindung."""

    def __init__(self, settings):
        self._settings = settings

    def test_connection(self):
        return False, "Connection failed"

    def initialize_schema(self):
        # Diese Methode darf im Fehlerpfad nicht ausgefuehrt werden.
        pass


def test_initialize_mysql_schema_success(monkeypatch, capsys):
    """Prueft Exit-Code 0 und Erfolgs-Ausgabe bei erfolgreicher Initialisierung."""

    monkeypatch.setattr(init_mysql_schema, "load_settings", lambda: _DummySettings())
    monkeypatch.setattr(init_mysql_schema, "MySqlClient", _ClientSuccess)

    exit_code = init_mysql_schema.initialize_mysql_schema()
    _ = capsys.readouterr().out

    assert exit_code == 0


def test_initialize_mysql_schema_connection_fail(monkeypatch, capsys):
    """Prueft Exit-Code 1 und Fehlermeldung bei Verbindungsfehler."""

    monkeypatch.setattr(init_mysql_schema, "load_settings", lambda: _DummySettings())
    monkeypatch.setattr(init_mysql_schema, "MySqlClient", _ClientConnectionFail)

    exit_code = init_mysql_schema.initialize_mysql_schema()
    _ = capsys.readouterr().out

    assert exit_code == 1

