# Mercator: Datenfluss, API-Strategie und Firmenmodell

## API-Strategie
- Primärer Feed: `Latest Insider Trading` (`/insider-trading/latest`).
- Profilanreicherung:
  1. primär `Company Profile by CIK` (`/profile-cik`)
  2. Fallback `Company Profile by Symbol` (`/profile?symbol=...`)
- Optionaler Backfill pro Firma: `Search Insider Trades` (`/insider-trading/search`), nur manuell/on-demand.

## Firmenidentität
- Kanonischer Schlüssel:
  - `CIK:<companyCik>` falls CIK vorhanden
  - sonst `SYM:<SYMBOL>`
- `companies` enthält genau eine Zeile pro `company_key`.
- `insider_trades` enthält viele Trades je Firma (`company_key` als FK).

## Statusmodell
- Fachlicher Gate-Status:
  - `gate_status`
  - `gate_reason`
- Technischer Profilstatus:
  - `profile_status`
  - `profile_reason`
- Beide Statusmodelle sind getrennt und werden nicht gegenseitig überschrieben.

## Persistente WebApp-Konfiguration
- Laufzeit-Einstellungen werden in MongoDB `app_settings` gespeichert.
- Fallback-Defaults kommen aus `.env`.
- Unterstützte Aktionen:
  - Laden
  - Speichern
  - Auf Defaults zurücksetzen
