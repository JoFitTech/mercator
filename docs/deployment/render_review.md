# Render Review Deployment

## 1. Ziel
Eine oeffentliche, read-only Review-Instanz von `mercator` auf Render als Docker Web Service bereitstellen.

## 2. Voraussetzungen
- Git-Repository mit `Dockerfile` im Root
- Render-Account
- Externe erreichbare MySQL- und MongoDB-Ziele (oder bewusst leer fuer reine UI-Pruefung)
- Konfigurierter Render Blueprint aus `render.yaml`

## 3. Benoetigte Secrets und Env-Variablen
Pflicht (Review-Betrieb):
- `APP_ENV=review`
- `APP_TITLE=Mercator Review`
- `MERCATOR_REVIEW_MODE=true`
- `MERCATOR_DISABLE_IMPORT=true`
- `MERCATOR_DISABLE_ADMIN_DELETE=true`
- `MERCATOR_UI_TEST_MODE=true`

DB/API (als Render Secret setzen):
- `MYSQL_ACTIVE_TARGET`
- `MONGO_ACTIVE_TARGET`
- `LOCAL_MYSQL_HOST`
- `LOCAL_MYSQL_PORT`
- `LOCAL_MYSQL_DATABASE`
- `LOCAL_MYSQL_USER`
- `LOCAL_MYSQL_PASSWORD`
- `LOCAL_MONGO_URI`
- `LOCAL_MONGO_DATABASE`
- `FMP_API_KEY`

## 4. Render Blueprint anlegen
1. In Render: **New +** -> **Blueprint**.
2. Repository verbinden.
3. `render.yaml` aus dem Root uebernehmen.
4. Nicht im Blueprint gesetzte Variablen als Secrets nachtragen.

## 5. Ersten Deploy ausloesen
1. Blueprint erstellen.
2. Initialen Build/Deploy starten lassen.
3. Logs pruefen, bis `streamlit run streamlit_app.py` aktiv ist.

## 6. Healthcheck pruefen
- Render nutzt `/_stcore/health`.
- Erwartung: HTTP 200.
- Bei Fehlern zuerst Port (8501), dann ENV und DB-Erreichbarkeit pruefen.

## 7. Review Mode validieren
Nach erfolgreichem Deploy in der UI pruefen:
1. Sichtbarer Hinweis `Review Mode`/`Review Instance - Read Only`.
2. Import-Button deaktiviert oder serverseitig blockiert.
3. Admin-Delete-Buttons deaktiviert oder serverseitig blockiert.
4. Explorer/Ticker-Detail rendern ohne `score`/`score_class`-Crash.

## 8. Typische Fehlerbilder
- **KeyError auf Score-Feldern**: alte Version ohne Feldnormalisierung deployt.
- **FK-Delete-Fehler**: erwartbar bei direktem Companies-Delete, wird jetzt fachlich abgefangen.
- **Leere Dashboard-Charts**: DB liefert keine Daten oder Ziel nicht erreichbar.

## 9. DB-Verbindungsprobleme erkennen
- Sidebar `Datenbank-Status` pruefen.
- MySQL/Mongo separat bewerten (App kann degradiert starten).
- ENV-Target (`MYSQL_ACTIVE_TARGET`, `MONGO_ACTIVE_TARGET`) mit gesetzten Host/URI-Werten abgleichen.

## 10. Hinweise fuer GPT-UI-Tests
- Oeffentliche URL ohne Login bereitstellen.
- Review-Mode aktiv lassen.
- Stabile Seitentitel und Navigation nutzen (`Dashboard`, `Explorer`, `Ticker-Detailansicht`, `Admin`).
- Agent-Traffic auf Netzwerkebene nicht blockieren (WAF/CDN Allowlist, falls vorhanden).
- Destruktive Aktionen bleiben deaktiviert; Tests fokusieren auf Lesepfade und UI-Stabilitaet.

