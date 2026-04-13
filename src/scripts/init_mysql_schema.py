"""CLI-Entry-Point, um die MySQL-Struktur je Zielsystem initial anzulegen."""

from __future__ import annotations

import sys

from src.config.settings import SettingsError, load_settings
from src.db.mysql_client_factory import build_mysql_client_for_target
from src.db.mysql_target_resolver import resolve_active_target


def initialize_mysql_schema() -> int:
    """Initialisiert das Schema für das aktive (oder gefallbackte) MySQL-Ziel.

    Returns:
        Exit-Code (0=ok, 1=Connection, 2=Settings, 3=unerwartet).
    """

    try:
        settings = load_settings()
        _target_name, client, _messages = resolve_active_target(settings.mysql)
        client.initialize_schema()
        return 0
    except SettingsError:
        return 2
    except Exception:  # pragma: no cover - defensiver Catch fuer CLI-Fehlerpfade
        return 3


def initialize_mysql_schema_for_target(target_name: str) -> int:
    """Initialisiert das Schema gezielt für ein bestimmtes MySQL-Ziel.

    Args:
        target_name: Zielname (``local`` oder ``uni``).

    Returns:
        Exit-Code (0=ok, 1=Connection).

    Raises:
        SettingsError: Bei Konfigurationsfehlern.
    """

    settings = load_settings()
    client = build_mysql_client_for_target(settings.mysql, target_name)
    connected, message = client.test_connection()
    if not connected:
        return 1
    _ = message
    client.initialize_schema()
    return 0


def initialize_all_targets() -> dict[str, list[str]]:
    """Initialisiert das Schema für alle konfigurierten Ziele (local + uni).

    Returns:
        Mapping von Zielname zu durchgeführten Aktionen.
    """

    results: dict[str, list[str]] = {}
    for target in ["local", "uni"]:
        try:
            exit_code = initialize_mysql_schema_for_target(target)
            results[target] = ["OK"] if exit_code == 0 else [f"FAILED: Connection to '{target}' failed."]
        except Exception as exc:
            results[target] = [f"FAILED: {exc}"]
    return results


def main() -> None:
    """Startet die CLI und beendet den Prozess mit dem Init-Exit-Code."""

    sys.exit(initialize_mysql_schema())


if __name__ == "__main__":
    main()
