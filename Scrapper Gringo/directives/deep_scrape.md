# Directive: Deep Scrape (Two-Stage)

## Purpose
Perform cascading web scraping:
1. **Stage 1**: Extract list of URLs from an overview page
2. **Stage 2**: Visit each URL and extract detailed information

## When to Use
- Scraping a list page that links to detail pages
- Tutorial listings → individual tutorial details
- Product catalogs → individual product specs
- Places search → business website enrichment

## Input
| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes* | Overview page URL |
| `places` | Yes* | Alternative: Places API query |
| `location` | If places | Location for Places search |
| `stage1` | No | What to extract in Stage 1 (default: "links") |
| `stage2` | No | What to extract from each page |
| `filter` | No | URL pattern to filter (e.g., "/videos/") |
| `limit` | No | Max URLs to deep-scrape (default: 20) |
| `delay` | No | Delay between requests (default: 1.5s) |

*One of `url` or `places` is required

## Execution
```bash
# From URL
python execution/deep_scrape.py \
    --url "https://snipki.de/alle-snipki-videos/" \
    --stage1 "links" \
    --stage2 "description, tools" \
    --filter "/videos/" \
    --limit 10 \
    --export

# From Places
python execution/deep_scrape.py \
    --places "Zahnarzt" \
    --location "Berlin" \
    --stage2 "services, contact" \
    --limit 5
```

## Output
- JSON file in `.tmp/deep_*.json`
- Contains: timestamp, count, items[] with merged Stage 1 + Stage 2 data

## Stage 2 Extraction Features
- **Title**: H1 or page title
- **Description**: Meta description or OG description
- **Key Learnings**: Numbered lists (1. 2. 3...)
- **Tools**: Auto-detected AI/tech tools mentioned
- **Duration**: Video/course duration if found
- **Tags**: Categories and tags
- **Paywall Detection**: Flags login-required pages

## Edge Cases
- **Paywall pages**: Extracts public teaser content only
- **Large lists**: Use `--limit` to control volume
- **Slow sites**: Increase `--delay` to avoid rate limiting

## Learnings
- snipKI.de: Video content behind paywall, but titles, descriptions, and key learnings are public
- Always use `--filter` for sites with many navigation links

## Error Handling
- Stage 1 failure → Abort with error
- Individual Stage 2 failure → Log error, continue with next URL
- Export failure → Save JSON locally, report Sheets error

## Related
- `scrape_url.md` for single-page scraping
- `export_to_sheets.md` for Google Sheets export
