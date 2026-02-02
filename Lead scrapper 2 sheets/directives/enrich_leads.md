# Enrich GMB Listings with Website Data

## Goal
Scrape business websites from GMB listings to extract email addresses and social media handles, then rate each company as a potential SEO lead.

## Inputs
- GMB listing file (from `scrape_gmb.py` output)
- OR: Search query + location to fetch fresh listings

## Outputs
Text file containing for each business:
- Business name and website
- Email address (if found)
- Social media handles:
  - Facebook
  - Instagram
  - TikTok
  - LinkedIn
  - X (Twitter)
- Lead score (1-5 points)
- Personalized cold email intro

## Lead Scoring System
| Criteria | Points |
|----------|--------|
| Is a service business | 1 |
| Has an email address | 3 |
| Has one social media handle | 1 |
| **Maximum score** | **5** |

## Tools/Scripts
- `execution/scrape_gmb.py` – Fetch initial listings ✅
- `execution/enrich_leads.py` – Website scraping and enrichment (to be created)

## Usage

```bash
# Enrich from existing GMB file
python execution/enrich_leads.py --input .tmp/tischler_tostedt_*.txt

# Fetch fresh and enrich in one step
python execution/enrich_leads.py --query "Tischler" --location "Tostedt"
```

## Edge Cases & Constraints
- Some websites may block scraping – use appropriate headers
- Email addresses may be obfuscated (e.g., info [at] domain.de)
- Social links may be in footer, header, or contact page
- Respect rate limits (1-2 second delay between requests)

## Cold Email Template
Generate personalized intro for SEO services pitch based on:
- Business name
- Missing online presence elements
- Improvement opportunities

---

*Last updated: 2026-02-02*
*Status: Implementation in progress*
