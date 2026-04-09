# Produktionsreife Checkliste (Mercator v1.0 Roadmap)

Diese Liste enthält die notwendigen Schritte, um den aktuellen Prototyp (MVP) in einen stabilen, sicheren und wartbaren Produktionszustand zu überführen.

## 1. Sicherheit (Security)
- [ ] **SSL/TLS Verschlüsselung**:
  - Einsatz eines Reverse Proxies (z.B. Nginx, Traefik oder Cloudflare) mit Let's Encrypt Zertifikaten für die Streamlit-UI (Port 8501).
  - Erzwingen von SSL für alle Datenbankverbindungen (MySQL und MongoDB), insbesondere zur Uni-Infrastruktur.
- [ ] **Secrets Management**:
  - Entfernen aller Default-Passwörter aus `.env`.
  - Nutzung von Docker Secrets oder Umgebungsvariablen-Injektion via CI/CD (z.B. GitHub Actions Secrets) statt lokaler `.env` Dateien im Deployment.
- [ ] **Netzwerksicherheit**:
  - Datenbank-Ports (3306, 27017) im Deployment **nicht** nach außen mappen (nur internes Docker-Netzwerk).
  - Zugriff auf die Uni-Infrastruktur über gesicherte VPN-Tunnel oder IP-Allowlisting einschränken.

## 2. Infrastruktur & Betrieb (Ops)
- [ ] **Abhängigkeiten (Dependencies)**:
  - Regelmäßige Scans auf Schwachstellen (z.B. mit `snyk` oder `pip-audit`).
  - [x] Versionen in `requirements.txt` pinnen (Erledigt).
- [ ] **Monitoring & Health Checks**:
  - [x] Docker Healthchecks für alle Services implementieren (Erledigt).
  - Integration eines Error-Trackings (z.B. **Sentry**) für Echtzeit-Fehlermeldungen in der App.
  - Performance-Monitoring (z.B. Prometheus/Grafana) für DB-Last und Container-Ressourcen.
- [ ] **Backup-Strategie**:
  - Automatisierte tägliche Backups für die MySQL- (Dumps) und MongoDB-Daten (mongodump) einrichten.
  - Test der Wiederherstellung (Restore-Procedure) dokumentieren.

## 3. Datenmanagement & Persistenz
- [ ] **Datenbank-Migrationen**:
  - Einführung eines Migrationstools wie **Alembic** für MySQL, um Schemaänderungen versioniert und reproduzierbar durchzuführen (statt manueller Skripte).
- [ ] **Hintergrund-Jobs (Scheduler)**:
  - Ablösung des ad-hoc Imports durch einen robusten Scheduler (z.B. `APScheduler` innerhalb der App oder ein dedizierter Cron-Container/Service).
  - Logging und Alerting für fehlgeschlagene Import-Jobs.

## 4. Qualitätssicherung (QA)
- [ ] **Automatisierte Tests**:
  - Ausbau der Unit-Tests auf eine Abdeckung von >80%.
  - Integrationstests, die den gesamten Workflow (Fetch -> Mongo -> Process -> MySQL) mit Testdaten durchlaufen.
- [ ] **CI/CD Pipeline**:
  - Einrichtung einer automatisierten Pipeline (z.B. GitHub Actions), die bei jedem Push:
    1. Linter (flake8/black) ausführt.
    2. Alle Tests gegen eine Test-DB startet.
    3. Das Docker-Image baut und in eine Registry pusht.

## 5. App-Logik & UX
- [ ] **Fehlerbehandlung**:
  - Verbesserung der Benutzerführung bei Datenbankausfällen (klare Fehlermeldungen in der UI statt Stacktraces).
- [ ] **Skalierbarkeit**:
  - Optimierung der Datenbank-Indizes für wachsende Datensätze in MongoDB (`insider_trades_raw`).
  - Caching-Strategien für teure API-Anfragen oder komplexe Dashboards.

---
*Stand: April 2026 - Generiert für Projekt Mercator*
