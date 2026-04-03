# TODOs und offene Fragen

## MySQL Target-Switch / Sync
- Klären, ob README-Begriff „Sqitch/Switch“ eine echte externe Sqitch-Integration meint oder weiterhin nur den internen Switch beschreibt.
- Uni-MySQL-SSL-Vorgaben klären (CA, Client-Zertifikate, Pflichtfelder).
- Reale Uni-Zugangsdaten für Entwicklungs-/Testumgebungen abstimmen und sicher bereitstellen.

## Tests
- Integrationstest gegen echte Uni-MySQL-Verbindung ergänzen, sobald Zugangsdaten und Netzwerkzugang vorliegen.
- DDL-Ausführung gegen temporäre Test-MySQL (z. B. CI-Service) zusätzlich zu den Unit-Tests validieren.

## Fachliche Regeln
- Gate-Schwellenwerte fachlich final abstimmen.
- Scheduler für den 1h-Importlauf ergänzen.

## Architektur
- Bei wachsendem Projektumfang ein Migrationswerkzeug evaluieren (statt nur direkter DDL-Initialisierung).
