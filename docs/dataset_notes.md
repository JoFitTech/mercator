# Datensatz-Notizen: FinanzPort Academic

## Datenquelle
Wir nutzen die **Financial Modeling Prep (FMP) Stable API** mit Fokus auf folgende Endpunkte:
- **Latest Insider Trading:** `/insider-trading/latest`
- **Company Profile:** `/profile`

## Feldmapping & Konventionen (MVP)
- `securitiesTransacted` → `qty`
- `url` → `source_url`
- `securitiesOwned` → `securities_owned`
- `trade_value_estimated` = `qty * price`
- `dedupe_key`: Stabiler SHA256-Hash über Kernattribute zur Dublettenvermeidung.
- `gate_reason`: Begründung für den jeweiligen Gate-Status.
- **Timestamps:** Alle Zeitstempel werden intern in UTC gespeichert.

## Datenqualitätsregeln
- **Defensives Parsing:** Datumswerte und Zahlen werden robust konvertiert (Pandas `to_datetime`, Float-Konvertierung).
- **Nullpreis-Behandlung:** Wenn `price = 0`, wird `trade_value_estimated` als `NULL` gespeichert (häufig bei Awards/RSUs), um analytische Verfälschungen zu vermeiden.
- **Fehlerbehandlung:** Parsing-Fehler führen nicht zum Abbruch, sondern werden geloggt und der Datensatz markiert.

## Gate-Status-Werte
- `PENDING`: Standardstatus nach Import.
- `PASS`: Erfolgreich durch das Gate (Kriterium für Profil-Abruf).
- `FAIL`: Erfüllt die Gate-Kriterien nicht.
- `PROFILE_FETCHED`: Unternehmensprofil wurde erfolgreich geladen.
- `PROFILE_FETCH_FAILED`: Profil-Abruf schlug fehl (z.B. Symbol nicht bei FMP bekannt).

## Speicherstrategie
- **MongoDB:** Speicherung des vollständigen `raw_payload` pro Trade zur Nachvollziehbarkeit.
- **MySQL:** Bereinigte, fachliche Felder für effiziente Abfragen in der UI.
