#!/usr/bin/env python3
"""
deep_scrape.py - Two-Stage Deep Scraping

Stage 1: Scrape initial URL/Places to get a list of links
Stage 2: Scrape each link to get detailed information
Export: Save enriched data to Google Sheets

Usage:
    # Two-stage URL scraping
    python deep_scrape.py --url "https://snipki.de/alle-snipki-videos/" \\
        --stage1 "tutorial titles and links" \\
        --stage2 "tutorial description, tools mentioned, key learnings"

    # Two-stage with Places
    python deep_scrape.py --places "Tischler" --location "Hamburg" \\
        --stage2 "contact details, services offered"

Requirements:
    pip install requests beautifulsoup4 python-dotenv
"""

import os
import sys
import re
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
except ImportError:
    print("Error: Missing dependencies. Run:")
    print("  pip install requests beautifulsoup4 python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Constants
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 1.5  # Delay between requests to be polite
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def fetch_page(url: str) -> tuple:
    """Fetch a webpage and return soup object."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup, None
    except Exception as e:
        return None, str(e)


def extract_links_from_page(soup: BeautifulSoup, base_url: str, pattern: str) -> list:
    """Extract links based on pattern description."""
    results = []
    pattern_lower = pattern.lower()
    
    # Find all links
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        
        # Skip empty or navigation links
        if not text or len(text) < 3:
            continue
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        
        # Make absolute URL
        if href.startswith('/'):
            href = urljoin(base_url, href)
        elif not href.startswith('http'):
            href = urljoin(base_url, href)
        
        # Check if it matches common content patterns
        parent = a.find_parent(['article', 'div', 'li', 'section'])
        is_content_link = False
        
        # Look for content indicators
        if parent:
            parent_class = ' '.join(parent.get('class', []))
            if any(word in parent_class.lower() for word in ['post', 'article', 'card', 'item', 'video', 'tutorial']):
                is_content_link = True
        
        # Check URL patterns
        if any(word in href.lower() for word in ['video', 'tutorial', 'article', 'post', 'blog']):
            is_content_link = True
        
        # Check if headline link
        if a.find_parent(['h1', 'h2', 'h3', 'h4']):
            is_content_link = True
        
        if is_content_link or 'link' in pattern_lower:
            results.append({
                'title': text[:200],
                'url': href,
            })
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for item in results:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    
    return unique


def extract_details_from_page(soup: BeautifulSoup, url: str, pattern: str) -> dict:
    """Extract detailed information from a single page, including paywall teaser content."""
    details = {
        'url': url,
        'title': '',
        'description': '',
        'content_preview': '',
        'key_learnings': '',
        'has_paywall': False,
    }
    
    # Get title
    title_tag = soup.find('h1') or soup.find('title')
    if title_tag:
        details['title'] = title_tag.get_text(strip=True)[:200]
    
    # Get meta description
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc:
        details['description'] = meta_desc.get('content', '')[:500]
    
    # Get OG description if no meta
    if not details['description']:
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc:
            details['description'] = og_desc.get('content', '')[:500]
    
    # Detect paywall
    page_text = soup.get_text().lower()
    paywall_indicators = ['einloggen', 'login', 'jetzt beitreten', 'subscribe', 'premium', 
                          'mitgliedschaft', 'registrieren', 'sign up', 'unlock']
    if any(indicator in page_text for indicator in paywall_indicators):
        details['has_paywall'] = True
    
    # Extract based on pattern
    pattern_lower = pattern.lower()
    
    # Look for main content - try multiple selectors
    main_content = None
    for selector in ['article', 'main', '.content', '.post-content', '.video-content', '.entry-content', 'body']:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    if main_content:
        # Get first paragraphs as preview
        paragraphs = main_content.find_all('p', limit=5)
        details['content_preview'] = ' '.join([p.get_text(strip=True) for p in paragraphs])[:500]
    
    # Extract numbered lists (often contain key learnings/steps)
    numbered_items = []
    for ol in soup.find_all('ol'):
        for li in ol.find_all('li', limit=10):
            text = li.get_text(strip=True)
            if text and len(text) > 10:
                numbered_items.append(text[:150])
    
    # Also look for text that starts with numbers (like "1. Something")
    all_text = soup.get_text()
    number_pattern = re.findall(r'^\s*\d+\.\s+([^\n]{15,150})', all_text, re.MULTILINE)
    numbered_items.extend(number_pattern[:10])
    
    if numbered_items:
        # Deduplicate and join
        unique_items = list(dict.fromkeys(numbered_items))[:5]
        details['key_learnings'] = ' | '.join(unique_items)
    
    # Extract tools/technologies mentioned (always do this)
    text = soup.get_text()
    tools = []
    tool_patterns = [
        'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Midjourney', 'DALL-E',
        'n8n', 'Zapier', 'Make', 'Notion', 'Airtable', 'Google Sheets',
        'Python', 'JavaScript', 'API', 'GPT-4', 'GPT-3', 'LLM',
        'HeyGen', 'Descript', 'Canva', 'Figma', 'Perplexity',
        'Kling', 'Remotion', 'NotebookLM', 'Microsoft Teams',
    ]
    for tool in tool_patterns:
        if tool.lower() in text.lower():
            tools.append(tool)
    if tools:
        details['tools'] = ', '.join(list(dict.fromkeys(tools)))
    
    # Extract duration if video
    duration_patterns = [
        r'(\d+)\s*min',
        r'(\d+:\d+)',
        r'Dauer[:\s]*(\d+)',
    ]
    for dp in duration_patterns:
        match = re.search(dp, text, re.IGNORECASE)
        if match:
            details['duration'] = match.group(0)
            break
    
    # Extract categories/tags
    tags = []
    for tag_container in soup.select('.tags, .categories, [class*="tag"], [class*="category"]'):
        for tag in tag_container.find_all(['a', 'span']):
            tag_text = tag.get_text(strip=True)
            if tag_text and len(tag_text) < 50:
                tags.append(tag_text)
    if tags:
        details['tags'] = ', '.join(list(dict.fromkeys(tags))[:5])
    
    return details


def stage1_scrape(url: str = None, places_query: str = None, location: str = None, 
                  pattern: str = "links", limit: int = 20) -> list:
    """
    Stage 1: Get list of URLs to deep-scrape.
    Either from a URL or from Places API.
    """
    results = []
    
    if url:
        print(f"\n📍 Stage 1: Scraping {url}")
        print(f"   Pattern: {pattern}\n")
        
        soup, error = fetch_page(url)
        if error:
            print(f"❌ Error: {error}")
            return []
        
        # Get base URL for relative links
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        results = extract_links_from_page(soup, base_url, pattern)
        
    elif places_query:
        print(f"\n📍 Stage 1: Places search for '{places_query}' in {location}")
        
        # Use scrape_gmb.py
        from scrape_gmb import search_places, extract_business_info
        
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            print("❌ Error: GOOGLE_PLACES_API_KEY not set")
            return []
        
        places = search_places(places_query, location, api_key, limit)
        
        for place in places:
            if place.get('website'):
                results.append({
                    'title': place.get('name', ''),
                    'url': place.get('website', ''),
                    'phone': place.get('phone', ''),
                    'address': place.get('address', ''),
                    'rating': place.get('rating', ''),
                })
    
    print(f"✅ Stage 1 complete: {len(results)} items found")
    return results[:limit]


def stage2_scrape(items: list, pattern: str, delay: float = REQUEST_DELAY) -> list:
    """
    Stage 2: Deep-scrape each URL from Stage 1 results.
    """
    print(f"\n🔍 Stage 2: Deep-scraping {len(items)} URLs")
    print(f"   Pattern: {pattern}")
    print(f"   Delay: {delay}s between requests\n")
    
    enriched = []
    
    for i, item in enumerate(items, 1):
        url = item.get('url') or item.get('link')
        if not url:
            continue
        
        print(f"   [{i}/{len(items)}] {url[:60]}...")
        
        soup, error = fetch_page(url)
        if error:
            print(f"      ⚠️ Skipped: {error[:50]}")
            item['scrape_error'] = error
            enriched.append(item)
            continue
        
        # Extract details
        details = extract_details_from_page(soup, url, pattern)
        
        # Merge with original item
        merged = {**item, **details}
        enriched.append(merged)
        
        print(f"      ✓ {details.get('title', 'No title')[:50]}")
        
        # Polite delay
        if i < len(items):
            time.sleep(delay)
    
    print(f"\n✅ Stage 2 complete: {len(enriched)} items enriched")
    return enriched


def save_results(results: list, name: str) -> str:
    """Save results to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    filename = f"deep_{name}_{timestamp}.json"
    filepath = tmp_dir / filename
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'count': len(results),
        'items': results
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Two-stage deep scraping with enrichment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape tutorials from snipKI, then get details from each
  python deep_scrape.py --url "https://snipki.de/alle-snipki-videos/" \\
      --stage1 "tutorial links" \\
      --stage2 "description, tools mentioned"

  # Scrape businesses, then visit their websites
  python deep_scrape.py --places "Zahnarzt" --location "Berlin" \\
      --stage2 "services, contact info"
        """
    )
    
    # Stage 1 source
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-u", "--url", help="URL to scrape for links")
    source.add_argument("-p", "--places", help="Places API search query")
    
    parser.add_argument("-l", "--location", help="Location for Places search")
    parser.add_argument("-n", "--limit", type=int, default=20,
                        help="Max items to scrape (default: 20)")
    
    # Patterns
    parser.add_argument("--stage1", default="links",
                        help="What to extract in Stage 1 (default: links)")
    parser.add_argument("--stage2", default="description, content",
                        help="What to extract in Stage 2")
    
    # Options
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY,
                        help=f"Delay between requests (default: {REQUEST_DELAY}s)")
    parser.add_argument("-t", "--title", help="Title for export")
    parser.add_argument("--export", action="store_true",
                        help="Export to Google Sheets after scraping")
    parser.add_argument("--filter", 
                        help="Only include URLs containing this pattern (e.g., '/videos/')")
    
    args = parser.parse_args()
    
    # Validate
    if args.places and not args.location:
        print("Error: --location required with --places")
        sys.exit(1)
    
    # Stage 1
    stage1_results = stage1_scrape(
        url=args.url,
        places_query=args.places,
        location=args.location,
        pattern=args.stage1,
        limit=args.limit * 3 if args.filter else args.limit  # Get more if filtering
    )
    
    # Apply URL filter if specified
    if args.filter and stage1_results:
        original_count = len(stage1_results)
        stage1_results = [item for item in stage1_results 
                          if args.filter.lower() in item.get('url', '').lower()]
        print(f"   📎 Filter '{args.filter}': {original_count} → {len(stage1_results)} items")
        stage1_results = stage1_results[:args.limit]
    
    if not stage1_results:
        print("No results from Stage 1")
        sys.exit(0)
    
    # Stage 2
    enriched = stage2_scrape(
        stage1_results,
        pattern=args.stage2,
        delay=args.delay
    )
    
    # Save results
    name = urlparse(args.url).netloc.replace('.', '_')[:15] if args.url else args.places
    output_path = save_results(enriched, name)
    print(f"\n📁 Saved: {output_path}")
    
    # Export to Sheets if requested
    if args.export:
        print("\n📊 Exporting to Google Sheets...")
        from export_to_sheets import export_generic_data
        
        title = args.title or f"Deep Scrape {name}"
        sheet_url = export_generic_data(enriched, title=title)
        print(f"✅ Sheet: {sheet_url}")
    
    # Preview
    print("\n📋 Preview (first 3):")
    for i, item in enumerate(enriched[:3], 1):
        title = item.get('title', 'No title')[:50]
        desc = item.get('description', '')[:80]
        print(f"\n  {i}. {title}")
        if desc:
            print(f"     {desc}...")


if __name__ == "__main__":
    main()
