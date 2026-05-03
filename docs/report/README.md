# Berichtsvorlage Modul Datenbanken 2

## Zweck
Dieser Ordner enthält die LaTeX-Grundstruktur für den wissenschaftlichen Projektbericht zu Mercator im Modul **Datenbanken 2** (geplanter Umfang: 5 bis 10 Textseiten).

## Benötigte Tools
- MiKTeX (stellt `lualatex` und `biber` bereit)
- Optional: Perl (nur für `latexmk` nötig)
- Optional: IntelliJ IDEA + TeXiFy IDEA

## Build
### Primär empfohlen unter Windows (ohne Perl)
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

## Hinweise
- Die Fehlermeldung `MiKTeX could not find the script engine 'perl'` betrifft nur `latexmk` und bedeutet **nicht**, dass `main.tex` fehlerhaft ist.
- Falls Pakete fehlen, in MiKTeX die automatische Paketinstallation erlauben.
- Die PDF wird lokal erzeugt, aber nicht ins Repository committed.
- LaTeX-Build-Artefakte werden nicht ins Repository committed.
- Deckblattdaten, KI-Erklärung und ehrenwörtliche Erklärung müssen vor Abgabe manuell geprüft und ausgefüllt werden.
- Keine KI-generierten Inhalte ohne fachliche Prüfung und klare Kennzeichnung übernehmen.
