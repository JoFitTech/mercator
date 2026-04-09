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


def initialize_mysql_schema_for_target(target_name: str) -> list[str]:
    """Initialisiert das Schema gezielt für ein bestimmtes MySQL-Ziel.

    Args:
        target_name: Zielname (``local`` oder ``uni``).

    Returns:
        Liste der durchgeführten Aktionen.

    Raises:
        SettingsError: Bei Konfigurationsfehlern.
        Exception: Bei Verbindungs- oder SQL-Fehlern.
    """

    settings = load_settings()
    client = build_mysql_client_for_target(settings.mysql, target_name)
    connected, message = client.test_connection()
    if not connected:
        raise Exception(f"Connection to '{target_name}' failed: {message}")
    return client.initialize_schema()


def initialize_all_targets() -> dict[str, list[str]]:
    """Initialisiert das Schema für alle konfigurierten Ziele (local + uni).

    Returns:
        Mapping von Zielname zu durchgeführten Aktionen.
    """

    results: dict[str, list[str]] = {}
    for target in ["local", "uni"]:
        try:
            results[target] = initialize_mysql_schema_for_target(target)
        except Exception as exc:
            results[target] = [f"FAILED: {exc}"]
    return results


def main() -> None:
    """Startet die CLI und initialisiert alle Ziele."""

    print("Starte MySQL-Schema-Initialisierung für alle Ziele (local + uni)...")
    results = initialize_all_targets()
    
    any_failed = False
    for target, actions in results.items():
        print(f"\nZiel: {target}")
        if not actions:
            print("  - Schema bereits aktuell (keine Änderungen nötig).")
        else:
            for action in actions:
                print(f"  - {action}")
                if action.startswith("FAILED"):
                    any_failed = True
    
    if any_failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
