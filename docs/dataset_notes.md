# Datensatz-Notizen

## Datenquelle
Financial Modeling Prep (Stable API), ausschließlich:
- Latest Insider Trading
- Company Profile

## Feldmapping (MVP)
- `securitiesTransacted` → `qty`
- `securitiesOwned` → `securities_owned`
- `url` → `source_url`
- `qty * price` → `trade_value_estimated`

## Datenqualitätsregeln
- Datums- und Zahlenfelder werden defensiv geparst.
- Parsingprobleme werden geloggt.
- Deduplizierung über technischen SHA256-Schlüssel.

## Gate-Status im MVP
- `PENDING`
- `PASS`
- `FAIL`
- `PROFILE_FETCHED`
- `PROFILE_FETCH_FAILED`

## Offene Punkte
- Zentrale Liste: `docs/todos_offene_fragen.md`.
