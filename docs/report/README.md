# Berichtsvorlage Modul Datenbanken 2

## Zweck
Dieser Ordner enthält die LaTeX-Grundstruktur für den wissenschaftlichen Projektbericht zu Mercator im Modul **Datenbanken 2** (geplanter Umfang: 5 bis 10 Textseiten).

## Benötigte Tools
- MiKTeX (stellt `lualatex` und `biber` bereit)
- Optional: Perl (nur für `latexmk` nötig, **nicht** für den Standard-Build unter Windows)
- Optional: IntelliJ IDEA + TeXiFy IDEA

## Build
Der empfohlene Standardweg unter Windows ist das Skript `build.ps1`. Es ruft die vollständige Build-Kette (`lualatex` → `biber` → `lualatex` → `lualatex`) automatisch auf und benötigt **kein** Perl.

### Empfohlen unter Windows (ohne Perl)
```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

### Manueller Build ohne `latexmk`
```bash
lualatex main.tex
biber main
lualatex main.tex
lualatex main.tex
```

### Optionaler Build mit `latexmk` (nur wenn Perl installiert ist)
```bash
latexmk -lualatex main.tex
```

Wenn `latexmk` wegen fehlendem Perl nicht startet, verwenden Sie stattdessen einfach `build.ps1` oder die manuellen Befehle oben.

## Hinweise
- Die Fehlermeldung `MiKTeX could not find the script engine 'perl'` betrifft nur `latexmk`. Sie bedeutet **nicht**, dass `main.tex` fehlerhaft ist, sondern nur, dass die optionale `latexmk`-Variante auf diesem System nicht verfügbar ist.
- Falls Pakete fehlen, in MiKTeX die automatische Paketinstallation erlauben.
- Die PDF wird lokal erzeugt, aber nicht ins Repository committed.
- LaTeX-Build-Artefakte werden nicht ins Repository committed.
- Deckblattdaten, KI-Erklärung und ehrenwörtliche Erklärung müssen vor Abgabe manuell geprüft und ausgefüllt werden.
- Keine KI-generierten Inhalte ohne fachliche Prüfung und klare Kennzeichnung übernehmen.
