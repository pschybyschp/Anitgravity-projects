# Directive: Export to PDF

## Purpose
Crawl a website and all its subpages, extract content, and generate a consolidated PDF document for offline reading or documentation purposes.

## When to Use
- Creating offline documentation from online resources
- Archiving website content as PDF
- Generating readable PDFs from multi-page tutorials or documentation
- Building a PDF book from scattered web content

## Input
| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | Yes* | Starting URL to crawl |
| `urls-file` | Yes* | File with URLs (one per line) |
| `filter` | No | URL pattern filter (e.g., `/docs/`, `/blog/`) |
| `depth` | No | Max crawl depth (default: 2) |
| `limit` | No | Max pages to include (default: 50) |
| `output` | No | Output filename (default: auto-generated) |
| `keep-parts` | No | Keep individual page PDFs |
| `browser` | No | Use browser for JavaScript sites |
| `wait` | No | Wait time in ms for JS (default: 3000) |

*One of `url` or `urls-file` is required

## Execution
```bash
# Basic usage - crawl site and create PDF
python execution/export_to_pdf.py --url "https://docs.example.com"

# With filters for specific sections
python execution/export_to_pdf.py \
    --url "https://snipki.de" \
    --filter "/videos/" \
    --depth 2 \
    --limit 30 \
    --output "snipki_tutorials.pdf"

# For JavaScript SPAs - use browser mode
python execution/export_to_pdf.py \
    --url "https://antigravity.google/docs/get-started" \
    --browser \
    --depth 1 \
    --limit 20 \
    --output "antigravity_docs.pdf"

# Provide URLs directly from a file
python execution/export_to_pdf.py \
    --urls-file "my_urls.txt" \
    --browser \
    --output "docs.pdf"

# Keep individual PDFs for each page
python execution/export_to_pdf.py \
    --url "https://example.com/docs/" \
    --keep-parts
```


## Output
- Final PDF in `.tmp/pdf_output/`
- Contains:
  - Table of Contents (auto-generated)
  - One section per page with:
    - Page title as header
    - Source URL as footer
    - Formatted content (headings, paragraphs, lists)
  - Page numbers

## Workflow Stages

### Stage 1: URL Discovery
1. Fetch starting URL
2. Extract all internal links (same domain)
3. Apply filter pattern if specified
4. Respect depth limit
5. Deduplicate URLs

### Stage 2: Content Extraction
For each discovered URL:
1. Fetch page content
2. Extract:
   - Title (h1 or page title)
   - Main content (article, main, .content)
   - Headings hierarchy
   - Paragraphs and lists
3. Save as individual PDF in `.tmp/pdf_parts/`

### Stage 3: PDF Merge
1. Sort PDFs by URL/title
2. Generate Table of Contents
3. Merge all PDFs into single document
4. Add page numbers
5. Save final PDF

## PDF Layout
- **Paper size**: A4
- **Margins**: 2.5cm
- **Font**: Helvetica (headings), Times (body)
- **Header**: Page title
- **Footer**: Source URL + page number

## Edge Cases
- **Very long pages**: Automatic page breaks
- **Images**: Scaled to fit page width (if enabled)
- **Paywall content**: Only public teaser extracted
- **Non-HTML pages**: Skipped with warning
- **Large sites**: Use `--limit` to control volume

## Error Handling
- URL not accessible → Skip, continue with others
- PDF generation fails → Log error, continue
- Merge fails → Individual PDFs preserved in `.tmp/pdf_parts/`

## Dependencies
```bash
pip install reportlab pypdf requests beautifulsoup4
```

## Related
- `scrape_url.md` for single-page scraping
- `deep_scrape.md` for two-stage scraping
- `export_to_sheets.md` for Google Sheets export

---

*Last updated: 2026-02-09*
*Status: ✅ Implemented*
