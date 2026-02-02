# Export Leads to Google Sheets

## Goal
Export enriched lead data to a Google Sheet for easy access and sharing.

## Inputs
- Enriched lead data (from `enrich_leads.py` or JSON format)
- Google Sheet ID (existing) or create new sheet

## Outputs
Google Sheet with columns:
- Name
- Website
- Phone
- Email
- Score
- Facebook link
- Instagram link
- TikTok link
- X link
- LinkedIn link

## Tools/Scripts
- `execution/enrich_leads.py` – Generate enriched data ✅
- `execution/export_to_sheets.py` – Export to Google Sheets (to be created)

## Setup Requirements

### 1. Enable Google Sheets API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (same as Places API)
3. Enable "Google Sheets API"
4. Enable "Google Drive API"

### 2. Create Service Account
1. Go to "Credentials" → "Create Credentials" → "Service Account"
2. Name it (e.g., "lead-exporter")
3. Download the JSON key file
4. Save as `credentials.json` in project root

### 3. Share Sheet with Service Account
- Share your Google Sheet with the service account email
- (e.g., lead-exporter@your-project.iam.gserviceaccount.com)

## Usage

```bash
# Export to new sheet
python execution/export_to_sheets.py --input .tmp/enriched_*.txt

# Export to existing sheet
python execution/export_to_sheets.py --input .tmp/enriched_*.txt --sheet-id "1abc..."

# Export with custom title
python execution/export_to_sheets.py --input .tmp/enriched_*.txt --title "Tischler Leads Tostedt"
```

---

*Last updated: 2026-02-02*
*Status: Implementation in progress*
