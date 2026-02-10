# Scrapper Gringo 🌵

Ein universeller Web-Scraper mit Google Sheets Integration.

## Features

- 🌐 **URL-Scraping** - Beliebige Websites nach Inhalten durchsuchen
- 📍 **Places API** - Google My Business Listings abrufen
- 📊 **Sheets Export** - Direkt in Google Spreadsheets exportieren
- 🎨 **Web UI** - Modernes Interface für einfache Bedienung

## Modi

### 1. URL-Modus
Scrape beliebige Websites basierend auf deiner Beschreibung:
- Headlines, Links, Texte
- Produkte, Preise
- Kontaktdaten
- Und mehr...

### 2. Places-Modus
Google Places API für Geschäftsdaten:
- Name, Adresse, Telefon
- Website, E-Mail
- Bewertungen
- Social Media Links

## Struktur

```
Scrapper Gringo/
├── ui/                     # Web Interface
│   ├── index.html
│   ├── style.css
│   └── app.js
├── execution/              # Python Scripts
│   ├── scrape_url.py       # URL-Scraper
│   ├── scrape_gmb.py       # Places API
│   ├── enrich_leads.py     # Lead Enrichment
│   └── export_to_sheets.py # Sheets Export
├── directives/             # SOPs
├── credentials/            # Google OAuth (gitignored)
├── .tmp/                   # Temporäre Dateien
└── .env                    # API Keys
```

## Quick Start

### 🚀 Einfachster Start (Empfohlen)

**Option 1: .bat Datei (Kein Kommando nötig)**
```bash
# Einfach doppelklicken:
Start UI.bat
```

**Option 2: Python Launcher**
```bash
python launch_ui.py
```

**Option 3: Als .exe kompilieren (einmalig)**
```bash
# .exe erstellen:
python build_exe.py

# Danach einfach doppelklicken:
dist/ScrapperGringo.exe
```

### Klassischer Start (Web UI manuell)
```bash
cd "Scrapper Gringo/ui"
python -m http.server 8080
# Öffne http://localhost:8080
```

### CLI Nutzung
```bash
# URL scrapen
python execution/scrape_url.py --url "https://example.com" --extract "headlines"

# PDF Export (NEU!)
python execution/export_to_pdf.py --url "https://docs.site.com" --browser --output "docs.pdf"

# Places suchen
python execution/scrape_gmb.py -q "Tischler" -l "Tostedt" -n 10

# Nach Sheets exportieren
python execution/export_to_sheets.py --input ".tmp/*.txt" --title "Meine Daten"
```

## Setup

### 1. Dependencies
```bash
pip install requests beautifulsoup4 python-dotenv google-auth google-auth-oauthlib google-api-python-client
```

### 2. API Keys (.env)
```
GOOGLE_PLACES_API_KEY=your_key_here
```

### 3. Google Sheets OAuth
- OAuth Client ID erstellen (Desktop App)
- Als `credentials/client_secret.json` speichern

## Lizenz

Privates Projekt
