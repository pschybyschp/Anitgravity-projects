# 🌵 Scrapper Gringo - Anleitung

## 🚀 3 Wege um die UI zu starten:

### ⭐ Option 1: .bat Datei (AM EINFACHSTEN)
```
Einfach doppelklicken: "Start UI.bat"
✅ Kein Terminal nötig
✅ Browser öffnet automatisch
✅ Sofort einsatzbereit
```

### Option 2: Python Launcher
```bash
python launch_ui.py
```
✅ Startet Server automatisch
✅ Öffnet Browser automatisch

### Option 3: Als .exe (Für Weitergabe)
```bash
# Einmalig ausführen:
python build_exe.py

# Danach:
Doppelklick auf: dist/ScrapperGringo.exe
```
✅ Keine Python-Installation nötig
✅ Kann an andere weitergegeben werden

---

## 📊 Export-Optionen in der UI

Die UI bietet jetzt **2 Export-Formate**:

### 1. Google Sheets Export
- Automatischer Upload
- Kollaborativ bearbeitbar
- Direkt teilbar

### 2. PDF Export
- Offline verfügbar
- Professionelle Dokumentation
- **Browser-Modus** für JavaScript-Seiten (SPAs)

**Neu:** Bei PDF-Export kannst du "Browser-Modus" aktivieren für:
- Angular/React/Vue Apps
- JavaScript-basierte Dokumentationen
- Dynamische Websites

---

## 🔧 CLI Tools (für Fortgeschrittene)

### PDF Export
```bash
# Einfach
python execution/export_to_pdf.py --url "https://docs.site.com" --output "docs.pdf"

# Mit Browser-Modus (für SPAs)
python execution/export_to_pdf.py \
    --url "https://antigravity.google/docs" \
    --browser \
    --filter "/docs/" \
    --depth 3 \
    --limit 50 \
    --output "antigravity_docs.pdf"

# URLs aus Datei
python execution/export_to_pdf.py \
    --urls-file "urls.txt" \
    --browser \
    --output "custom.pdf"
```

### URL Scraping
```bash
python execution/scrape_url.py \
    --url "https://example.com" \
    --extract "headlines"
```

### Deep Scrape (2-Stufen)
```bash
python execution/deep_scrape.py \
    --url "https://snipki.de/videos/" \
    --filter "/videos/" \
    --stage2 "Titel, Beschreibung" \
    --limit 20
```

### Google Places
```bash
python execution/scrape_gmb.py \
    -q "Tischler" \
    -l "Tostedt" \
    -n 10
```

### Google Sheets Export
```bash
python execution/export_to_sheets.py \
    --input ".tmp/*.txt" \
    --title "Meine Daten"
```

---

## 📁 Projekt-Struktur

```
Scrapper Gringo/
├── Start UI.bat            ← Doppelklick zum Starten!
├── launch_ui.py           ← Python Launcher
├── build_exe.py           ← .exe Builder
│
├── ui/                    ← Web Interface
│   ├── index.html         │  - PDF/Sheets Toggle
│   ├── style.css          │  - 3 Modi: URL/Deep/Places
│   └── app.js             │  - Modern Design
│
├── execution/             ← Backend Scripts
│   ├── scrape_url.py      │  - Einzelne URLs
│   ├── deep_scrape.py     │  - Zwei-Stufen
│   ├── scrape_gmb.py      │  - Places API
│   ├── enrich_leads.py    │  - Lead Enrichment
│   ├── export_to_sheets.py│  - Sheets Export
│   └── export_to_pdf.py   │  - PDF Export (NEU!)
│
├── directives/            ← Dokumentation
│   ├── scrape_url.md
│   ├── deep_scrape.md
│   ├── scrape_gmb_listings.md
│   ├── enrich_leads.md
│   ├── export_to_sheets.md
│   └── export_to_pdf.md   ← NEU!
│
└── .tmp/                  ← Temporäre Dateien
    ├── pdf_output/        │  - Generierte PDFs
    └── pdf_parts/         │  - Temp PDFs
```

---

## 💡 Tipps & Tricks

### PDF Export von antigravity.google
```bash
# Komplette Doku (ca. 10-15 Min)
python execution/export_to_pdf.py \
    --url "https://antigravity.google/docs/get-started" \
    --browser \
    --filter "/docs/" \
    --depth 3 \
    --limit 50 \
    --output "antigravity_complete.pdf"

# Schneller Test
python execution/export_to_pdf.py \
    --url "https://antigravity.google/docs/get-started" \
    --browser \
    --limit 5 \
    --output "antigravity_test.pdf"
```

### Browser-Modus wann nutzen?
- ✅ Angular, React, Vue Apps
- ✅ JavaScript-basierte Doku-Sites
- ✅ SPAs (Single Page Apps)
- ❌ Statische HTML-Seiten (nicht nötig)

---

## 🐛 Probleme lösen

### "python nicht gefunden"
- Python installieren: https://python.org
- Bei Installation "Add to PATH" aktivieren

### Port 8080 bereits belegt
- Anderen Port in `launch_ui.py` ändern (Zeile 18)

### PyInstaller Fehler beim .exe Build
```bash
pip install --upgrade pyinstaller
```

---

## 📝 Nächste Schritte

1. **UI testen**: `Start UI.bat` doppelklicken
2. **PDF Export testen**: Kleine Website als PDF
3. **.exe erstellen**: `python build_exe.py` ausführen
4. **Produktiv nutzen**: Sheets oder PDF - je nach Bedarf!
