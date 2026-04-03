"""CLI-Entry-Point, um die MySQL-Struktur initial anzulegen."""

from src.config.settings import SettingsError, load_settings
from src.db.mysql_client import MySqlClient


def initialize_mysql_schema():
    """Initialisiert die Zieltabellen in MySQL und liefert einen Exit-Code."""

    try:
        settings = load_settings()
        client = MySqlClient(settings.mysql)

        connected, message = client.test_connection()
        if not connected:
            return 1

        client.initialize_schema()
        return 0
    except SettingsError:
        return 2
    except:  # pragma: no cover - defensiver Catch fuer CLI-Fehlerpfade
        return 3


def main():
    """Startet die CLI und beendet den Prozess mit passendem Exit-Code."""

    initialize_mysql_schema()


if __name__ == "__main__":
    main()

