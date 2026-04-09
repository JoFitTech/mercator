from __future__ import annotations

import sys
from typing import Any

from src.config.settings import load_settings
from src.db.mysql_client_factory import build_mysql_client_for_target


def run_doctor() -> None:
    """Analysiert das MySQL-Schema beider Ziele und führt notwendige Reparaturen durch."""
    
    print("=== Mercator DB-Doctor ===")
    print("Analysiere Schema-Zustand für local und uni...\n")
    
    settings = load_settings()
    targets = ["local", "uni"]
    
    for target in targets:
        print(f"Prüfe Ziel: {target}...")
        try:
            client = build_mysql_client_for_target(settings.mysql, target)
            ok, msg = client.test_connection()
            if not ok:
                print(f"  [!] Verbindung fehlgeschlagen: {msg}")
                continue
            
            actions = client.initialize_schema()
            if not actions:
                print("  [OK] Schema ist aktuell. Keine Reparaturen nötig.")
            else:
                print(f"  [i] {len(actions)} Änderungen/Reparaturen durchgeführt:")
                for action in actions:
                    print(f"    - {action}")
                print("  [OK] Ziel erfolgreich aktualisiert.")
        except Exception as exc:
            print(f"  [FEHLER] Unerwarteter Fehler bei '{target}': {exc}")
        print("-" * 30)


if __name__ == "__main__":
    run_doctor()
