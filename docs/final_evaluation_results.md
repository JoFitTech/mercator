# Finaler Auswertungsstand fuer die Mercator-Projektarbeit

## 1. Zweck

Diese Datei dokumentiert den Datenbankstand, der zur Befuellung der Ergebniskennzahlen in der Projektarbeit verwendet wird. Die Werte dienen insbesondere Tabelle 4 und Kapitel 5.1 des Projektberichts.

## 2. Auswertungszeitpunkt

- Datum und Uhrzeit der Auswertung: `2026-05-26 11:27:32` (lokal)
- Lokale Zeitzone: `Mitteleuropaeische Sommerzeit` (`UTC+02:00`)

## 3. Verwendete Datenbanken

| System | Datenbank | Relevante Tabellen/Collections | Zweck |
|---|---|---|---|
| MongoDB | `WI24A2_3_DB_User9_DB1` | `insider_trades_raw` | Raw-Store |
| MySQL | `WI24A2_3_DB_User9_DBJosef` | `insider_trades`, `companies`, `market_signal_cache` | Clean-Store |

## 4. SQL- und MongoDB-Abfragen

Die folgenden Abfragen wurden read-only ausgefuehrt.

```sql
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME;
```

```sql
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'insider_trades';
```

```sql
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'companies';
```

```sql
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'market_signal_cache';
```

```sql
SELECT COUNT(*) AS clean_trades_total
FROM insider_trades;
```

```sql
SELECT 
  gate_status,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY gate_status
ORDER BY anzahl DESC;
```

```sql
SELECT 
  COALESCE(score_class, 'NULL') AS score_class,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY score_class
ORDER BY score_class;
```

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND trade_value IS NOT NULL
  AND score IS NOT NULL
  AND score_class IS NOT NULL
  AND gate_status IN ('PASS', 'PROFILE_FETCHED')
ORDER BY score DESC, trade_value DESC
LIMIT 10;
```

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND score IS NOT NULL
  AND score_class IS NOT NULL
ORDER BY score DESC, trade_value DESC
LIMIT 10;
```

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND trade_value IS NOT NULL
ORDER BY trade_value DESC
LIMIT 10;
```

```sql
SELECT
  SUM(CASE WHEN symbol IS NULL THEN 1 ELSE 0 END) AS symbol_null,
  SUM(CASE WHEN reporting_name IS NULL THEN 1 ELSE 0 END) AS reporting_name_null,
  SUM(CASE WHEN transaction_date IS NULL THEN 1 ELSE 0 END) AS transaction_date_null,
  SUM(CASE WHEN trade_value IS NULL THEN 1 ELSE 0 END) AS trade_value_null,
  SUM(CASE WHEN score IS NULL THEN 1 ELSE 0 END) AS score_null,
  SUM(CASE WHEN score_class IS NULL THEN 1 ELSE 0 END) AS score_class_null,
  COUNT(*) AS total_rows
FROM insider_trades;
```

```sql
SELECT 
  gate_status,
  COALESCE(score_class, 'NULL') AS score_class,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY gate_status, score_class
ORDER BY gate_status, score_class;
```

```js
db.getCollectionNames()
```

```js
db.insider_trades_raw.countDocuments({})
```

```js
db.insider_trades_raw.findOne({}, { _id: 0 })
```

```js
db.insider_trades_raw.aggregate([
  { $group: { _id: "$gate_status", anzahl: { $sum: 1 } } },
  { $sort: { anzahl: -1 } }
])
```

```js
db.insider_trades_raw.aggregate([
  { $group: { _id: "$profile_status", anzahl: { $sum: 1 } } },
  { $sort: { anzahl: -1 } }
])
```

## 5. Ergebniskennzahlen fuer Tabelle 4

| Kennzahl | Wert | Datenquelle | Abfragebasis |
|---|---:|---|---|
| MongoDB Raw-Trades | 588 | MongoDB | `insider_trades_raw.countDocuments({})` |
| MySQL Clean-Trades | 1458 | MySQL | `COUNT(*) FROM insider_trades` |
| Unternehmen im Clean-Store | 388 | MySQL | `COUNT(*) FROM companies` |
| Market-Signal-Datensaetze | 0 | MySQL | `COUNT(*) FROM market_signal_cache` |
| Gate PASS | 41 | MySQL | `GROUP BY gate_status` |
| Gate FAIL | 639 | MySQL | `GROUP BY gate_status` |
| Gate PENDING | 113 | MySQL | `GROUP BY gate_status` |
| Gate PRE_GATE_FAIL | 578 | MySQL | `GROUP BY gate_status` |
| Gate PROFILE_FETCHED | 87 | MySQL | `GROUP BY gate_status` |
| Score A | 0 | MySQL | `GROUP BY score_class` |
| Score B | 12 | MySQL | `GROUP BY score_class` |
| Score C | 111 | MySQL | `GROUP BY score_class` |
| Score D | 382 | MySQL | `GROUP BY score_class` |
| Score E | 683 | MySQL | `GROUP BY score_class` |
| Score NULL | 270 | MySQL | `score_class IS NULL` |
| Vollstaendig befuellte Top-Kandidaten | 0 | MySQL | strenge Top-Kandidaten-Abfrage |

## 6. Ausgefuehrte MySQL-Abfragen und Ergebnisse

### 6.1 Gesamtzahl Clean-Trades

```sql
SELECT COUNT(*) AS clean_trades_total
FROM insider_trades;
```

Ergebnis: `1458`

### 6.2 Gate-Verteilung

```sql
SELECT 
  gate_status,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY gate_status
ORDER BY anzahl DESC;
```

| gate_status | anzahl |
|---|---:|
| FAIL | 639 |
| PRE_GATE_FAIL | 578 |
| PENDING | 113 |
| PROFILE_FETCHED | 87 |
| PASS | 41 |

### 6.3 Score-Verteilung

```sql
SELECT 
  COALESCE(score_class, 'NULL') AS score_class,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY score_class
ORDER BY score_class;
```

| score_class | anzahl |
|---|---:|
| B | 12 |
| C | 111 |
| D | 382 |
| E | 683 |
| NULL | 270 |

### 6.4 Unternehmen im Clean-Store

```sql
SELECT COUNT(*) AS companies_total
FROM companies;
```

Ergebnis: `388`

### 6.5 Market-Signal-Cache

```sql
SELECT COUNT(*) AS market_signal_cache_total
FROM market_signal_cache;
```

Ergebnis: `0`

### 6.6 Vollstaendig befuellte Top-Kandidaten

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND trade_value IS NOT NULL
  AND score IS NOT NULL
  AND score_class IS NOT NULL
  AND gate_status IN ('PASS', 'PROFILE_FETCHED')
ORDER BY score DESC, trade_value DESC
LIMIT 10;
```

- Anzahl gefundener Datensaetze: `0`
- Die strenge Kandidatenabfrage lieferte 0 Datensaetze.

### 6.7 Top 10 nach Score ohne Gate-Filter

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND score IS NOT NULL
  AND score_class IS NOT NULL
ORDER BY score DESC, trade_value DESC
LIMIT 10;
```

Ergebnis: `0` Datensaetze.

### 6.8 Top 10 nach Trade Value

```sql
SELECT 
  symbol,
  reporting_name,
  transaction_date,
  trade_value,
  score,
  score_class,
  gate_status
FROM insider_trades
WHERE symbol IS NOT NULL
  AND trade_value IS NOT NULL
ORDER BY trade_value DESC
LIMIT 10;
```

Ergebnis: `0` Datensaetze.

### 6.9 Null-Werte-Diagnose fuer zentrale Felder

```sql
SELECT
  SUM(CASE WHEN symbol IS NULL THEN 1 ELSE 0 END) AS symbol_null,
  SUM(CASE WHEN reporting_name IS NULL THEN 1 ELSE 0 END) AS reporting_name_null,
  SUM(CASE WHEN transaction_date IS NULL THEN 1 ELSE 0 END) AS transaction_date_null,
  SUM(CASE WHEN trade_value IS NULL THEN 1 ELSE 0 END) AS trade_value_null,
  SUM(CASE WHEN score IS NULL THEN 1 ELSE 0 END) AS score_null,
  SUM(CASE WHEN score_class IS NULL THEN 1 ELSE 0 END) AS score_class_null,
  COUNT(*) AS total_rows
FROM insider_trades;
```

| symbol_null | reporting_name_null | transaction_date_null | trade_value_null | score_null | score_class_null | total_rows |
|---:|---:|---:|---:|---:|---:|---:|
| 1458 | 0 | 0 | 1259 | 270 | 270 | 1458 |

### 6.10 Kombination aus Gate-Status und Score-Klasse

```sql
SELECT 
  gate_status,
  COALESCE(score_class, 'NULL') AS score_class,
  COUNT(*) AS anzahl
FROM insider_trades
GROUP BY gate_status, score_class
ORDER BY gate_status, score_class;
```

| gate_status | score_class | anzahl |
|---|---|---:|
| FAIL | B | 11 |
| FAIL | C | 109 |
| FAIL | D | 350 |
| FAIL | E | 105 |
| FAIL | NULL | 64 |
| PASS | B | 1 |
| PASS | C | 2 |
| PASS | D | 13 |
| PASS | E | 25 |
| PENDING | NULL | 113 |
| PRE_GATE_FAIL | D | 19 |
| PRE_GATE_FAIL | E | 553 |
| PRE_GATE_FAIL | NULL | 6 |
| PROFILE_FETCHED | NULL | 87 |

## 7. Ausgefuehrte MongoDB-Abfragen und Ergebnisse

### 7.1 Raw-Trades zaehlen

```js
db.insider_trades_raw.countDocuments({})
```

Ergebnis: `588`

### 7.2 Optional: Raw-Status-Verteilung (feldabhaengig)

Pruefung auf Feldverfuegbarkeit:

```js
db.insider_trades_raw.findOne({}, { _id: 0 })
```

Erkannte relevante Felder im Beispiel-Dokument:
- `gate_status`: vorhanden
- `profile_status`: vorhanden
- `validation_status`: nicht vorhanden

Aggregation `gate_status`:

```js
db.insider_trades_raw.aggregate([
  { $group: { _id: "$gate_status", anzahl: { $sum: 1 } } },
  { $sort: { anzahl: -1 } }
])
```

| gate_status | anzahl |
|---|---:|
| PRE_GATE_FAIL | 259 |
| PENDING | 171 |
| FAIL | 141 |
| PASS | 17 |

Aggregation `profile_status`:

```js
db.insider_trades_raw.aggregate([
  { $group: { _id: "$profile_status", anzahl: { $sum: 1 } } },
  { $sort: { anzahl: -1 } }
])
```

| profile_status | anzahl |
|---|---:|
| NOT_REQUESTED | 588 |

`validation_status`: nicht vorhanden, daher keine Aggregation ausgefuehrt.

## 8. Berichtstaugliche Tabelle 4

**Tabelle 4: Ergebniskennzahlen des finalen Auswertungsstands**

| Kennzahl | Wert | Interpretation |
|---|---:|---|
| MongoDB Raw-Trades | 588 | Rohdatensaetze im dokumentenorientierten Raw-Store |
| MySQL Clean-Trades | 1458 | Bereinigte oder weiterverarbeitete Datensaetze im relationalen Clean-Store |
| Unternehmen im Clean-Store | 388 | Anzahl persistierter Unternehmensstammsaetze im Clean-Store |
| Market-Signal-Datensaetze | 0 | Aktuell keine Cache-Eintraege in `market_signal_cache` |
| Gate PASS | 41 | Datensaetze mit Gate-Status PASS |
| Gate FAIL | 639 | Datensaetze mit Gate-Status FAIL |
| Gate PENDING | 113 | Datensaetze mit Gate-Status PENDING |
| Gate PRE_GATE_FAIL | 578 | Datensaetze mit fruehem Gate-Ausschluss |
| Gate PROFILE_FETCHED | 87 | Datensaetze mit Profilstatus im Gate-Verlauf |
| Score A | 0 | Keine Datensaetze in Score-Klasse A |
| Score B | 12 | Datensaetze mit Score-Klasse B |
| Score C | 111 | Datensaetze mit Score-Klasse C |
| Score D | 382 | Datensaetze mit Score-Klasse D |
| Score E | 683 | Datensaetze mit Score-Klasse E |
| Score NULL | 270 | Datensaetze ohne zugewiesene Score-Klasse |
| Vollstaendig befuellte Top-Kandidaten | 0 | Keine finalen Top-Kandidaten bei strenger Filterung |

## 9. Berichtstauglicher Fliesstext fuer Kapitel 5.1

Zum Auswertungszeitpunkt wurden im MongoDB-Raw-Store (`insider_trades_raw`) 588 Rohdatensaetze und im MySQL-Clean-Store (`insider_trades`) 1458 bereinigte bzw. weiterverarbeitete Datensaetze festgestellt. Die Werte sind nicht als direkte 1:1-Transformationsquote zu interpretieren, sondern als dokumentierter Stand zweier unterschiedlicher Persistenzschichten. Die Gate-Verteilung (u. a. 639 FAIL, 578 PRE_GATE_FAIL, 41 PASS) sowie die Score-Verteilung (Schwerpunkt in D und E, 270 ohne Score-Klasse) machen die Filter- und Bewertungslogik transparent. Die strenge Top-Kandidatenabfrage lieferte im aktuellen Datenstand 0 Datensaetze. Daraus wird keine Anlageempfehlung abgeleitet.

## 10. Berichtstaugliche Einordnung fuer Kapitel 5.2

Die Anwendung macht den Zusammenhang zwischen Rohdaten, bereinigten Daten, Gate-Status und Score-Klassen technisch nachvollziehbar. Die Filterlogik reduziert den Kandidatenbestand deutlich und fuehrt in der strengen Endselektion aktuell zu keiner final befuellten Top-Kandidatenliste. Dieses Ergebnis ist als datenstandsabhaengiger, fachlich interpretierbarer Befund zu lesen. Der Schwerpunkt der Projektarbeit liegt auf der robusten technischen Umsetzung der analytischen Datenanwendung und nicht auf einer empirischen Kapitalmarktvalidierung.

## 11. Offene Punkte fuer die weitere Finalisierung

- Screenshots der Streamlit-App erstellen.
- Dashboard-Screenshot ergaenzen.
- Trade-Explorer-Screenshot ergaenzen.
- Detailansicht mit Score-Breakdown ergaenzen.
- Tabelle 4 in die Projektarbeit uebernehmen.
- Ergebnistext in Kapitel 5.1 uebernehmen.
- Quellen und Verzeichnisse final pruefen.

## 12. Qualitaetskriterien

Pruefstatus dieser Datei:

- Alle tatsaechlich ausfuehrbaren Abfragen wurden read-only ausgefuehrt: **erfuellt**.
- Alle Ergebnisse wurden dokumentiert: **erfuellt**.
- Zugangsdaten sind nicht enthalten: **erfuellt**.
- Es wurden keine Werte erfunden: **erfuellt**.
- Fehlerhistorie ist nicht enthalten: **erfuellt**.
- Eine direkt uebernehmbare Tabelle 4 ist enthalten: **erfuellt**.
- Ein direkt uebernehmbarer Text fuer Kapitel 5.1 ist enthalten: **erfuellt**.
- Ein direkt uebernehmbarer Text fuer Kapitel 5.2 ist enthalten: **erfuellt**.

