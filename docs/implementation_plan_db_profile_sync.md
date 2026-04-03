# Implementierungsplan: Umschaltbares DB-Profil und MySQL-Sync

## Zielbild
- Eine App-Konfiguration steuert aktiv das DB-Profil (`local` Docker-DB vs. `uni`).
- Alle MySQL-Zugriffe laufen über ein einheitliches Verbindungs-Fabrikmuster.
- Ein dedizierter Sync-Workflow überträgt `companies` und `insider_trades` richtungsbasiert (`local->uni`, `uni->local`).
- Sync-Läufe sind wiederholbar (idempotent) ohne Duplikate.
- Aktives Profil und Sync-Richtung sind in CLI/Logs klar sichtbar.

## Architektur
- **Konfiguration:** `src/config/settings.py` erweitert um zwei MySQL-Profile plus aktive Auswahl.
- **DB-Client:** `src/db/mysql_client.py` erhält Aufbau für `source`/`target` je Profil.
- **Repository:** `src/db/mysql_repository.py` nutzt bestehende Upsert-Mechanik weiter.
- **Sync-Orchestrator:** neuer Service unter `src/services/` (z. B. `mysql_sync_service.py`).
- **CLI:** neues Sync-Skript unter `src/scripts/` für reproduzierbare Läufe.

## Konfigurationsvariablen
- `DB_PROFILE_ACTIVE=local|uni`
- `MYSQL_LOCAL_HOST`, `MYSQL_LOCAL_PORT`, `MYSQL_LOCAL_DATABASE`, `MYSQL_LOCAL_USER`, `MYSQL_LOCAL_PASSWORD`
- `MYSQL_UNI_HOST`, `MYSQL_UNI_PORT`, `MYSQL_UNI_DATABASE`, `MYSQL_UNI_USER`, `MYSQL_UNI_PASSWORD`
- SSL je Profil:
  - `MYSQL_LOCAL_SSL_DISABLED`, `MYSQL_LOCAL_SSL_CA`, `MYSQL_LOCAL_SSL_CERT`, `MYSQL_LOCAL_SSL_KEY`
  - `MYSQL_UNI_SSL_DISABLED`, `MYSQL_UNI_SSL_CA`, `MYSQL_UNI_SSL_CERT`, `MYSQL_UNI_SSL_KEY`
- Sync-Steuerung:
  - `SYNC_DIRECTION=local_to_uni|uni_to_local`
  - `SYNC_BATCH_SIZE`
  - `SYNC_DRY_RUN=true|false`

## Notwendige Dateiänderungen
- `src/config/settings.py`
  - Profilmodell (`local`/`uni`) und `DB_PROFILE_ACTIVE` einführen.
- `src/db/mysql_client.py`
  - profilbasierten Verbindungsaufbau kapseln.
- `streamlit_app.py`
  - aktives Profil transparent verwenden.
- `src/services/mysql_sync_service.py` (neu)
  - tabellenweiser, richtungsbasierter Sync.
- `src/scripts/sync_mysql.py` (neu)
  - CLI für Sync-Richtung, Dry-Run, Batch-Größe.
- `.env.example`
  - neue Variablen dokumentieren.
- `README.md`, `docs/architecture.md`
  - Betriebsmodi, Schalter und Sync-Ablauf ergänzen.
- Tests:
  - `tests/test_settings.py`
  - neue Sync-Tests unter `tests/`.

## Implementierungsphasen
1. **Konfiguration**
   - Profile und aktive Auswahl in Settings finalisieren.
2. **Wiring**
   - MySQL-Client/Repositories auf Profil-Fabrik umstellen.
3. **Sync-Basis**
   - `MySqlSyncService` mit expliziter Richtung implementieren.
4. **CLI**
   - `sync_mysql.py` mit `--direction`, `--dry-run`, `--batch-size` bereitstellen.
5. **Dokumentation & Tests**
   - `.env.example`, README, Architektur und Tests aktualisieren.

## Sync-Regeln (idempotent)
- Nur Upsert verwenden (`ON DUPLICATE KEY UPDATE`), keine Blind-Inserts.
- Schlüsselfelder:
  - `companies.symbol`
  - `insider_trades.dedupe_key`
- Reihenfolge pro Lauf:
  1. `companies`
  2. `insider_trades`
- Konfliktregel für v1:
  - Quellseite hat Priorität je gewählter Richtung.
- Optional später:
  - inkrementeller Sync über `updated_at`/`fetched_at`.

## Sicherheitsaspekte
- Keine Credentials im Code oder Compose hartcodieren.
- Secrets nur in `.env`/Secret-Store.
- Für Uni-Profil SSL standardmäßig einplanen und validieren.
- `SYNC_DRY_RUN=true` als sicherer Startmodus für erste Runs.
- Logs ohne Passwort-/Secret-Ausgabe.

## Testplan
- **Unit:** Profilauswahl und Env-Parsing (`tests/test_settings.py`).
- **Unit:** Sync-Entscheidung (Richtung, Batch, Konfliktregeln, Idempotenz).
- **Integration (Smoke):** zwei getrennte MySQL-Instanzen (lokal + Uni-ähnlich).
- **Negativtests:** fehlende Variablen, falsche Richtung, SSL-/Netzwerkfehler.

## Offene Risiken
- Uni-MySQL evtl. nur mit VPN/TLS erreichbar.
- Große Datenmengen erfordern Batching/Timeout-Tuning.
- Parallele Schreibzugriffe (Import + Sync) brauchen Betriebsregeln.
- Schema-Drift zwischen local/uni kann Sync brechen.

## Definition of Done
- Umschalten über `DB_PROFILE_ACTIVE` ohne Codeänderung möglich.
- Sync in beide Richtungen läuft reproduzierbar und idempotent.
- Fehler liefern klare Exit-Codes und nutzbare Logs.
- Alle Variablen stehen in `.env.example` und Doku.
- Relevante Tests für Konfig, Richtung und Idempotenz sind grün.

