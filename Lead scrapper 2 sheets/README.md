# Lead Scrapper 2 Sheets

Ein DOE-basiertes (Directive-Observation-Experiment) Automatisierungssystem für Lead-Generierung.

## Features

- 🔍 **GMB Scraping** - Google My Business Listings abrufen
- 📧 **Lead Enrichment** - Email & Social Media von Websites extrahieren
- ⭐ **Lead Scoring** - Automatische Bewertung (1-5 Punkte)
- 📊 **Google Sheets Export** - Direkt in Spreadsheets exportieren
- ✉️ **Cold Email Generation** - Personalisierte SEO-Pitches

## Struktur

```
Lead scrapper 2 sheets/
├── .env                    # API Keys (GOOGLE_PLACES_API_KEY)
├── .tmp/                   # Temporäre Output-Dateien
├── credentials/            # Google OAuth Credentials
│   ├── client_secret.json
│   └── token.json
├── directives/             # SOP-Dokumentation
│   ├── scrape_gmb_listings.md
│   ├── enrich_leads.md
│   └── export_to_sheets.md
└── execution/              # Python Skripte
    ├── scrape_gmb.py
    ├── enrich_leads.py
    └── export_to_sheets.py
```

## Quick Start

```bash
# 1. GMB-Listings holen (z.B. 10 Tischler in Tostedt)
python execution/scrape_gmb.py -q "Tischler" -l "Tostedt" -n 10

# 2. Leads anreichern (Email, Social Media, Score, Cold-Email)
python execution/enrich_leads.py --input ".tmp/tischler_*.txt"

# 3. Nach Google Sheets exportieren
python execution/export_to_sheets.py --input ".tmp/enriched_*.txt" --title "Meine Leads"
```

## Setup

### 1. Dependencies installieren
```bash
pip install requests beautifulsoup4 python-dotenv google-auth google-auth-oauthlib google-api-python-client
```

### 2. Google Places API Key
1. [Google Cloud Console](https://console.cloud.google.com/) öffnen
2. Places API aktivieren
3. API Key erstellen
4. In `.env` eintragen:
```
GOOGLE_PLACES_API_KEY=dein_key_hier
```

### 3. Google Sheets OAuth
1. Google Sheets API aktivieren
2. OAuth Client ID erstellen (Desktop App)
3. JSON als `credentials/client_secret.json` speichern
4. Beim ersten Export: Browser-Authentifizierung durchführen

## Lead Scoring System

| Kriterium | Punkte |
|-----------|--------|
| Dienstleistungsunternehmen | 1 |
| Hat E-Mail-Adresse | 3 |
| Hat Social-Media-Präsenz | 1 |
| **Maximum** | **5** |

## Lizenz

Privates Projekt
