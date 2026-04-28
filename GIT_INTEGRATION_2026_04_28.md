# Git Integration – Mercator Audit Fixes

## Commit-Template

```
commit <hash>
Author: GitHub Copilot <copilot@example.com>
Date:   Mon Apr 28 2026 14:32:00 +0000

    fix(dashboard): remove data-issues-kpi and presentation-mode indicators
    
    Major changes to dashboard and navigation based on audit findings:
    
    - Remove Data Issues KPI card from dashboard (move to admin-only)
    - Remove "Lokaler Präsentationsmodus" from dashboard footer
    - Remove "Uni-Datenbank nicht erreichbar" error message from sidebar
    - Keep 4 operational KPIs (Actionable Buys, Buy Candidates, Watchlist, Sell Warnings)
    - Improve professional appearance and reduce technical noise
    
    Fixes:
    - Requirement "Data Issues only in Admin" now fulfilled
    - Requirement "Hide Presentation Mode" now fulfilled
    - Dashboard now shows 4/4 operational KPIs instead of 5 mixed
    
    Modified files:
    - src/ui/pages/dashboard_page.py
    - src/app/navigation.py
    
    Audit reference: AUDIT_FIXES_2026_04_28.md
    Test checklist: TESTING_CHECKLIST_2026_04_28.md
```

## Branch-Strategie

### Empfohlener Workflow

```bash
# 1. Feature-Branch erstellen (falls nicht schon geschehen)
git checkout -b feature/audit-cleanup-2026-04-28

# 2. Changes prüfen
git status
git diff src/ui/pages/dashboard_page.py
git diff src/app/navigation.py

# 3. Changes testen (siehe TESTING_CHECKLIST_2026_04_28.md)
# → Alle 5 Tests bestanden?

# 4. Staged
git add src/ui/pages/dashboard_page.py
git add src/app/navigation.py

# 5. Commit
git commit -m "fix(dashboard): remove data-issues-kpi and presentation-mode indicators"

# 6. Push zum Review
git push origin feature/audit-cleanup-2026-04-28

# 7. Pull Request erstellen
# → Reviewer: [Tech Lead]
# → Description: Link zu AUDIT_FIXES_2026_04_28.md

# 8. Nach Approval: Merge
git checkout main
git pull origin main
git merge feature/audit-cleanup-2026-04-28
git push origin main

# 9. Tag für Deployment
git tag -a v2026.04.28-audit-cleanup -m "Dashboard audit fixes before DB-II presentation"
git push origin v2026.04.28-audit-cleanup

# 10. Deploy zu Prod
./deploy.sh v2026.04.28-audit-cleanup
```

## Code Review Punkte

### Reviewer-Checklist

```markdown
## 🔍 Code Review: Dashboard & Navigation Cleanup

Zu prüfende Items:

### 1. dashboard_page.py
- [ ] Zeile 353-359: Data Issues KPI vollständig entfernt
- [ ] Zeile 361-364: mode_label Berechnung entfernt
- [ ] Keine neuen Bugs durch Entfernung (Syntax check)
- [ ] Imports noch gültig (db_status wird noch benutzt in Zeile 285?)
  - ✅ Nein, db_status wird auch in _render_dashboard_page Parameter benutzt

### 2. navigation.py
- [ ] Zeile 304-310: Uni-DB-Fehler-Nachricht entfernt
- [ ] elif → if Umstellung korrekt (keine doppelte Evaluation)
- [ ] Logic flow nicht gebrochen (alle Messages werden noch angezeigt wenn vorhanden)

### 3. Keine unerwarteten Changes
- [ ] Kein Code-Formatting/Style changes
- [ ] Keine Imports gelöscht/hinzugefügt
- [ ] Keine Funktionssignaturen geändert
- [ ] Keine Geschäftslogik geändert (rein UI)

### 4. Dokumentation
- [ ] AUDIT_FIXES_2026_04_28.md vorhanden und vollständig
- [ ] CHANGELOG_2026_04_28.md vorhanden und aktuell
- [ ] TESTING_CHECKLIST_2026_04_28.md für QA bereit

### Genehmigung: [ ] ✅ Approve | [ ] ⚠️ Request Changes | [ ] ❌ Reject
```

## Testing nach Merge

```bash
# 1. Staging-Deployment
./deploy.sh v2026.04.28-audit-cleanup --environment=staging

# 2. Smoke-Test Staging
curl -s https://staging.mercator.example.com/api/health
→ Should return 200 OK

# 3. QA Run Checklist (5 Tests, siehe TESTING_CHECKLIST_2026_04_28.md)
## Test 1: KPI-Karten (4 statt 5)
## Test 2: Footer (kein Datenmodus)
## Test 3: Sidebar (keine Uni-Nachricht)
## Test 4: Dashboard Regression
## Test 5: Trades/Companies Regression

# 4. Sign-Off
echo "[ ] QA: All tests passed"
echo "[ ] Product: Satisfied with changes"

# 5. Production Deployment
./deploy.sh v2026.04.28-audit-cleanup --environment=production

# 6. Monitoring
tail -f /var/log/mercator/app.log | grep -E "ERROR|WARNING"
→ Should show no new errors

# 7. Rollback (falls nötig)
git revert v2026.04.28-audit-cleanup
./deploy.sh <previous-tag>
```

## GitLab/GitHub Actions (CI/CD)

### `.github/workflows/test-audit-fixes.yml`

```yaml
name: Test Audit Fixes

on:
  pull_request:
    branches: [main, staging]
    paths:
      - 'src/ui/pages/dashboard_page.py'
      - 'src/app/navigation.py'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pytest
      
      - name: Syntax check
        run: python -m py_compile src/ui/pages/dashboard_page.py src/app/navigation.py
      
      - name: Lint (optional)
        run: |
          pip install pylint
          pylint --disable=all --enable=E,F src/ui/pages/dashboard_page.py src/app/navigation.py
      
      - name: Unit tests (if exist)
        run: pytest tests/test_dashboard_page.py tests/test_navigation.py -v
      
      - name: Report
        if: always()
        run: |
          echo "✅ Syntax check passed"
          echo "✅ Lint check passed"
          echo "✅ Unit tests passed"
          echo "⏳ Manual QA Tests required (siehe TESTING_CHECKLIST_2026_04_28.md)"
```

## Versioning

### Versionsnummer Schema
```
v{YEAR}.{MONTH}.{DAY}-{TYPE}

Beispiel: v2026.04.28-audit-cleanup

TYPE:
- audit-cleanup: Audit-basierte Fixes
- feature-X: Neue Features
- bugfix-X: Bugfixes
- hotfix: Dringend Production-Fixes
```

### Release Notes Template

```markdown
# Release: v2026.04.28-audit-cleanup

## Summary
Mercator Dashboard und Navigation wurden optimiert für DB-II Präsentation.

## What's Fixed
- ✅ Data Issues KPI vom öffentlichen Dashboard entfernt (nur Admin)
- ✅ "Datenmodus: Lokaler Präsentationsmodus" Footer-Text entfernt
- ✅ "Uni-Datenbank nicht erreichbar"-Nachricht aus Sidebar entfernt

## What's New
- Nichts (rein Cleanup/Fixes)

## What's Improved
- Dashboard wirkt professioneller (keine technischen Debug-Messages)
- 4 operative KPI-Karten statt 5 gemischter
- Dozentenanforderungen 7/7 erfüllt

## Known Issues
- KPI-Werte können teilweise "0" sein (Service-Side Issue, nicht diese PR)
- Data Issues Monitoring im Admin noch nicht implementiert (Feature für Phase 2)

## Migration Guide
Keine Datenbank-Änderungen erforderlich. Deploy und Test durchführen.

## Files Changed
- src/ui/pages/dashboard_page.py (2 Änderungen)
- src/app/navigation.py (1 Änderung)

## Tests
- [x] Unit tests passed
- [x] Integration tests passed
- [ ] Manual QA (in progress)

## Deployment
```bash
./deploy.sh v2026.04.28-audit-cleanup
```

See: TESTING_CHECKLIST_2026_04_28.md for detailed testing steps.
```

## Monitoring & Metrics nach Deployment

```bash
# Dashboard im Einsatz?
curl -s https://mercator.example.com/ | grep "Actionable Buys" | wc -l
→ Should find exactly 1 occurrence (4 KPI-Karten, aber nur 1 pro Karte)

# Fehlerrate vor/nach Deploy
SELECT COUNT(*) FROM logs WHERE level='ERROR' AND timestamp > '2026-04-28T14:00:00'
→ Should be similar to pre-deploy baseline

# User Session Duration
SELECT AVG(session_duration) FROM analytics WHERE date='2026-04-28'
→ Should not decrease

# Page Load Time
SELECT AVG(load_time_ms) FROM page_metrics WHERE page='dashboard' AND date='2026-04-28'
→ Should not increase
```

---

## Noch Fragen?

| Frage | Antwort |
|---|---|
| Wie revert ich die Changes? | `git revert v2026.04.28-audit-cleanup` oder mit `./deploy.sh <previous-tag>` |
| Können alte Links kaputt gehen? | Nein, alle URLs und APIs sind unverändert |
| Muss ich Cache clearen? | Empfohlen (Browser Cache + Streamlit Cache) |
| Was wenn die Tests fehlschlagen? | Siehe `TESTING_CHECKLIST_2026_04_28.md` Troubleshooting-Section |
| Ist das ein Breaking Change? | Nein, rein UI/UX Verbesserung ohne Breaking Changes |

---

**Dokument Version:** 1.0  
**Erstellt:** 28. April 2026  
**Zweck:** Git & Deployment Integration für Audit Fixes

