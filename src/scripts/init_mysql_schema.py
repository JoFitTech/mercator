"""CLI-Entry-Point, um die MySQL-Struktur initial anzulegen."""

from __future__ import annotations


from src.config.settings import SettingsError, load_settings
from src.db.mysql_client import MySqlClient


def initialize_mysql_schema() -> int:
    """Initialisiert die Zieltabellen in MySQL und liefert einen Exit-Code."""

    try:
        settings = load_settings()
        client = MySqlClient(settings.mysql)

        connected, _message = client.test_connection()
        if not connected:
            return 1

        client.initialize_schema()
        return 0
    except SettingsError:
        return 2
    except Exception:  # pragma: no cover - defensiver Catch fuer CLI-Fehlerpfade
        return 3


def main() -> None:
    """Startet die CLI und beendet den Prozess mit passendem Exit-Code."""

    raise SystemExit(initialize_mysql_schema())


if __name__ == "__main__":
    main()
