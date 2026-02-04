# Directive: Export to Google Sheets

## Purpose
Export scraped data to Google Sheets for easy access, sharing, and collaboration.

## When to Use
- After any scraping operation (URL, Deep Scrape, Places)
- When user wants cloud-accessible deliverables

## Input
| Parameter | Required | Description |
|-----------|----------|-------------|
| `input` | Yes | Path to data file (.txt or .json) |
| `sheet-id` | No | Existing Sheet ID (creates new if omitted) |
| `title` | No | Title for new sheet |

## Execution
```bash
# Export JSON (from scrape_url or deep_scrape)
python execution/export_to_sheets.py --input ".tmp/scrape_*.json" --title "My Export"

# Export enriched leads
python execution/export_to_sheets.py --input ".tmp/enriched_*.txt" --title "Leads Export"

# Update existing sheet
python execution/export_to_sheets.py --input ".tmp/*.json" --sheet-id "1abc..."
```

## Output
- Google Sheet URL
- Formatted table with:
  - Bold header row
  - Frozen header
  - Auto-sized columns

## Authentication

### OAuth 2.0 Setup (Recommended)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable "Google Sheets API" and "Google Drive API"
3. Create OAuth 2.0 Client ID (Desktop App)
4. Download JSON → save as `credentials/client_secret.json`
5. First run opens browser for authentication
6. Token saved to `credentials/token.json`

### Add Test User
If OAuth consent screen is in testing mode:
1. Go to OAuth Consent Screen → Test users
2. Add your Google email

## Supported Input Formats
| Format | Description |
|--------|-------------|
| `.json` | Auto-detects columns from data keys |
| `.txt` | Parses enriched lead format (Name, Website, etc.) |

## Learnings
- **Service Account limitation**: Cannot create new Sheets without additional Drive delegation
- **OAuth recommended**: Uses user's own Drive, no sharing needed
- **JSON flexible**: Columns auto-detected from first item's keys

## Error Handling
- Missing credentials → Instructions printed
- Token expired → Auto-refresh or re-authenticate
- API quota exceeded → Wait and retry

## Related
- `scrape_url.md` for URL scraping
- `deep_scrape.md` for two-stage scraping
- `enrich_leads.md` for lead enrichment

---

*Last updated: 2026-02-04*
*Status: ✅ Implemented with OAuth*
