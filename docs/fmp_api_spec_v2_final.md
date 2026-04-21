# Mercator FMP API Specification v2 Final

## Runtime Pipeline
`API1 latest insider trades -> lokale Validation -> lokale statische Gates -> lokale 3-Tage-Akkumulation -> API2 profile -> optional search-cik/profile-cik -> API3 historical-price-eod/full -> finales lokales Scoring -> Storage -> UI`

## API Stack
- API1: `GET /stable/insider-trading/latest?page=0&limit=100&apikey=...`
- API2: `GET /stable/profile?symbol={SYMBOL}&apikey=...`
- API2 Fallbacks (nur bei Identity/Symbol-Problemen):
  - `GET /stable/search-cik?...`
  - `GET /stable/profile-cik?cik=...`
- API3: `GET /stable/historical-price-eod/full?symbol={SYMBOL}&from={DATE_FROM}&to={DATE_TO}&apikey=...`

## Instrument Scope
Nur **Aktien** und **ETFs** sind im finalen Kaufpfad zulässig.
Nicht zulässig: ADRs, Funds/Mutual Funds, Notes, Preferred Shares, derivative Sonderinstrumente, Unknown Types.

## Transaction Code Taxonomy (normativ, lokal versioniert)
- `CORE_BUY`: `P`
- `CORE_SELL`: `S`
- `SECONDARY_SIGNAL`: `I`, `L`
- `MANUAL_REVIEW`: `J`, optional `V`
- `EXCLUDE_FROM_CORE`: `A`, `C`, `D`, `E`, `F`, `G`, `H`, `M`, `O`, `U`, `W`, `X`, `Z`, `K`

Warum nur `P` als Core Buy:
`P` bildet Open-Market/Private Purchases mit dem stärksten positiven Signal ab. Die übrigen Codes sind technisch, kompensationsnah oder kontextabhängig und dürfen nicht als normaler Kauf im Core-Score gewertet werden.

Kurz-Erklärungen:
- `P`: Purchase, stärkster positiver Kaufcode.
- `S`: Sale, stärkster negativer Verkaufscode.
- `A`: Award, meist Compensation, kein echter Marktkauf.
- `C`: Conversion, technischer Vorgang.
- `D`: Return/Disposition an Emittenten.
- `E`: ExpireShort, technischer Vorgang.
- `F`: InKind, oft vesting-/steuergetrieben.
- `G`: Gift, kein Trading-Signal.
- `H`: ExpireLong, technischer Vorgang.
- `I`: Discretionary, sekundär.
- `J`: Other, nur mit Zusatzkontext.
- `L`: Small, Zusatzhinweis, nie Kernsignal.
- `M`: Exempt, nicht mit Marktkauf verwechseln.
- `O`: OutOfTheMoney, technischer Vorgang.
- `U`: Tender, Sondersituation.
- `W`: Will/Erbfolge, kein Markt-Signal.
- `X`: InTheMoney, Optionen/Derivateffekt.
- `Z`: Trust/Ownership-Struktur.
- `K`: EquitySwap, nicht Core Buy.
- `V`: Voluntary, nur mit Zusatzkontext.

## Warum API3 und nicht Income Statement
API3 liefert historische Preis-/Volumenzeitreihen und ist damit die geeignete Quelle für Trend-, Liquiditäts- und Timing-Signale (SMA, Momentum, Dollar Volume). Income Statements sind dafür nicht der richtige Datenpfad.
