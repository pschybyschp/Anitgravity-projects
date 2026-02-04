# Scrape Google My Business Listings

## Goal
Extract business listing details from Google My Business (GMB) profiles for lead generation purposes.

## Inputs
- **Search query**: Business type/category (e.g., "Tischler", "plumbers", "dentists")
- **Location**: Geographic area to search (e.g., "Tostedt", "New York", "Berlin")
- **Limit**: Maximum number of listings to retrieve (default: 10)
- **Format**: Output format - text, json, or csv (default: text)

## Outputs
- Structured file containing business information:
  - Business name
  - Address
  - Phone number
  - Website URL
  - Google Maps URL
  - Business hours
  - Rating and review count
  - Business category

## Tools/Scripts
- `execution/scrape_gmb.py` – Main scraping script ✅

### Usage

```bash
# Basic usage
python execution/scrape_gmb.py --query "Tischler" --location "Tostedt" --limit 10

# JSON output
python execution/scrape_gmb.py -q "plumbers" -l "New York" -n 20 -f json

# CSV output
python execution/scrape_gmb.py -q "dentists" -l "Berlin" -f csv

# Fast mode (skip detailed info)
python execution/scrape_gmb.py -q "Tischler" -l "Tostedt" --no-details
```

### Arguments
| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| --query | -q | Yes | Business type to search |
| --location | -l | Yes | Geographic area |
| --limit | -n | No | Max results (default: 10) |
| --format | -f | No | text/json/csv (default: text) |
| --no-details | | No | Skip fetching detailed info |
| --output | -o | No | Custom output path |

## Setup Requirements

### 1. Install Dependencies
```bash
pip install requests python-dotenv
```

### 2. Get Google Places API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Places API" under APIs & Services
4. Create credentials (API Key)
5. Add to `.env` file:
```
GOOGLE_PLACES_API_KEY=your_api_key_here
```

### 3. API Costs
- Text Search: $32 per 1000 requests
- Place Details: $17 per 1000 requests
- Free tier: $200/month credit

## Edge Cases & Constraints
- ✅ Rate limiting implemented (0.2s delay between requests)
- ✅ Missing fields handled gracefully ("Nicht verfügbar")
- ✅ Pagination supported for large result sets
- API key required - will exit with instructions if missing
- Maximum ~60 results per query (Google API limit)

## Output Location
- Files saved to `.tmp/` directory
- Filename format: `{query}_{location}_{timestamp}.{ext}`

---

*Last updated: 2026-02-02*
*Status: Ready for use*
