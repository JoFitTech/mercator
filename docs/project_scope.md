# Projekt-Scope (Mercator)

## Akademischer Kern
Mercator demonstriert eine durchgängige Datenpipeline vom öffentlichen Finanzfeed bis zur interaktiven Analyseoberfläche.

## Verbindlicher MVP-Scope
- Nur zwei FMP-Endpunkte:
  1. `GET /insider-trading/latest?page={page}&limit={limit}`
  2. `GET /profile?symbol={SYMBOL}`
- Feed-Polling 1x pro Stunde, Standard `page=0`, `limit=100`
- Keine zusätzliche Seitennavigation im Feed im MVP
- Profile nur für Gate-Pass-Kandidaten
- Profil-Cache mit 7 Tagen TTL
- Deduplizierung über technischen Schlüssel

## Nicht-Ziele
- Kein Trading und keine Broker-Anbindung
- Kein Login-/Rollenmodell
- Kein Mail-Versand
- Keine zusätzlichen FMP-Endpunkte
- Keine unnötige Enterprise-Komplexität
