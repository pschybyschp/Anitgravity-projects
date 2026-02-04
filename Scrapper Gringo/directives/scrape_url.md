# Directive: URL Scraping

## Purpose
Scrape any public website and extract structured data based on user-defined patterns.

## When to Use
- User provides a URL and describes what to extract
- Single-page extraction (not multi-page deep scraping)
- Examples: Headlines, links, contact info, product data

## Input
| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes | Full URL to scrape |
| `extract` | Yes | Description of what to extract (natural language) |
| `format` | No | Output format: `json` (default) or `text` |

## Execution
```bash
python execution/scrape_url.py --url "https://example.com" --extract "headlines and links"
```

## Output
- JSON file in `.tmp/scrape_*.json`
- Contains: success, url, pattern, count, items[]

## Supported Extraction Patterns
- **headlines/titles**: h1-h6 tags
- **links/urls**: anchor tags with href
- **articles/posts**: content containers
- **emails**: regex extraction from page text
- **phone numbers**: regex extraction

## Edge Cases
- **Paywall pages**: Only public content is extracted
- **JavaScript-rendered content**: Not supported (static HTML only)
- **Rate limiting**: Automatic 1.5s delay between requests

## Error Handling
- Invalid URL → Returns error message
- Network timeout → 15s timeout, returns error
- Empty results → Returns empty items array

## Related
- `deep_scrape.md` for multi-page scraping
- `export_to_sheets.md` for Google Sheets export
