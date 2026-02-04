#!/usr/bin/env python3
"""
scrape_url.py - Universal URL Scraper

Scrapes any website based on user-defined extraction rules.

Usage:
    python scrape_url.py --url "https://example.com" --extract "headlines"
    python scrape_url.py --url "https://snipki.de/alle-snipki-videos/" --extract "tutorial titles and links"

Requirements:
    pip install requests beautifulsoup4 python-dotenv
"""

import os
import sys
import re
import json
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
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def fetch_page(url: str) -> tuple:
    """
    Fetch a webpage and return HTML content and soup object.
    
    Returns:
        Tuple of (html_content, BeautifulSoup object, error_message)
    """
    try:
        if not url.startswith("http"):
            url = "https://" + url
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        return html, soup, None
    
    except requests.exceptions.RequestException as e:
        return None, None, str(e)


def extract_headlines(soup: BeautifulSoup) -> list:
    """Extract all headlines (h1-h6) from page."""
    headlines = []
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        for element in soup.find_all(tag):
            text = element.get_text(strip=True)
            if text:
                headlines.append({
                    'type': tag,
                    'text': text,
                    'link': element.find('a')['href'] if element.find('a') else None
                })
    return headlines


def extract_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract all links from page."""
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        
        # Make absolute URL
        if href.startswith('/'):
            href = urljoin(base_url, href)
        elif not href.startswith('http'):
            continue
        
        if text and len(text) > 2:
            links.append({
                'text': text,
                'url': href
            })
    
    return links


def extract_articles(soup: BeautifulSoup) -> list:
    """Extract article-like content blocks."""
    articles = []
    
    # Look for common article containers
    for selector in ['article', '.post', '.entry', '.card', '.item', '[class*="tutorial"]', '[class*="video"]']:
        elements = soup.select(selector)
        for el in elements:
            title = None
            link = None
            description = None
            
            # Find title
            title_el = el.find(['h1', 'h2', 'h3', 'h4'])
            if title_el:
                title = title_el.get_text(strip=True)
                link_el = title_el.find('a') or el.find('a')
                if link_el and link_el.get('href'):
                    link = link_el['href']
            
            # Find description
            desc_el = el.find(['p', '.description', '.excerpt', '.summary'])
            if desc_el:
                description = desc_el.get_text(strip=True)[:200]
            
            if title:
                articles.append({
                    'title': title,
                    'link': link,
                    'description': description
                })
    
    return articles


def extract_by_pattern(soup: BeautifulSoup, pattern: str) -> list:
    """Extract content based on user description."""
    results = []
    pattern_lower = pattern.lower()
    
    # Detect what user wants
    if any(word in pattern_lower for word in ['headline', 'überschrift', 'title', 'titel']):
        results = extract_headlines(soup)
    
    elif any(word in pattern_lower for word in ['link', 'url', 'href']):
        results = extract_links(soup, '')
    
    elif any(word in pattern_lower for word in ['tutorial', 'video', 'artikel', 'article', 'post', 'beitrag']):
        results = extract_articles(soup)
    
    elif any(word in pattern_lower for word in ['email', 'e-mail', 'mail']):
        # Extract emails
        text = soup.get_text()
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        results = [{'email': e} for e in set(emails)]
    
    elif any(word in pattern_lower for word in ['telefon', 'phone', 'nummer']):
        # Extract phone numbers
        text = soup.get_text()
        phones = re.findall(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,}', text)
        results = [{'phone': p.strip()} for p in set(phones) if len(p) > 8]
    
    else:
        # Default: extract headlines and links
        results = extract_headlines(soup) + extract_articles(soup)
    
    return results


def scrape_url(url: str, extract_pattern: str) -> dict:
    """
    Main scraping function.
    
    Args:
        url: URL to scrape
        extract_pattern: Description of what to extract
        
    Returns:
        Dictionary with results
    """
    print(f"\n🌐 Scraping: {url}")
    print(f"📋 Extrahiere: {extract_pattern}\n")
    
    html, soup, error = fetch_page(url)
    
    if error:
        return {
            'success': False,
            'error': error,
            'items': []
        }
    
    # Extract based on pattern
    items = extract_by_pattern(soup, extract_pattern)
    
    # Deduplicate
    seen = set()
    unique_items = []
    for item in items:
        key = str(item.get('title') or item.get('text') or item.get('email') or item)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    print(f"✅ Gefunden: {len(unique_items)} Einträge")
    
    return {
        'success': True,
        'url': url,
        'pattern': extract_pattern,
        'count': len(unique_items),
        'items': unique_items
    }


def save_results(results: dict, output_format: str = 'json') -> str:
    """Save results to .tmp directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    # Create safe filename from URL
    url_part = urlparse(results.get('url', '')).netloc.replace('.', '_')[:20]
    
    if output_format == 'json':
        filename = f"scrape_{url_part}_{timestamp}.json"
        filepath = tmp_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        filename = f"scrape_{url_part}_{timestamp}.txt"
        filepath = tmp_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"URL: {results.get('url')}\n")
            f.write(f"Pattern: {results.get('pattern')}\n")
            f.write(f"Count: {results.get('count')}\n")
            f.write("=" * 60 + "\n\n")
            for i, item in enumerate(results.get('items', []), 1):
                f.write(f"[{i}] ")
                for key, value in item.items():
                    if value:
                        f.write(f"{key}: {value}\n     ")
                f.write("\n")
    
    return str(filepath)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape websites based on extraction patterns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_url.py --url "https://snipki.de/alle-snipki-videos/" --extract "tutorial titles"
  python scrape_url.py --url "https://example.com" --extract "all links"
  python scrape_url.py --url "https://example.com/contact" --extract "email addresses"
        """
    )
    
    parser.add_argument("-u", "--url", required=True,
                        help="URL to scrape")
    parser.add_argument("-e", "--extract", required=True,
                        help="What to extract (e.g., 'headlines', 'links', 'tutorials')")
    parser.add_argument("-f", "--format", choices=["json", "text"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("-o", "--output",
                        help="Custom output file path")
    
    args = parser.parse_args()
    
    # Scrape
    results = scrape_url(args.url, args.extract)
    
    if not results['success']:
        print(f"\n❌ Fehler: {results['error']}")
        sys.exit(1)
    
    # Save
    if args.output:
        output_path = args.output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        output_path = save_results(results, args.format)
    
    print(f"\n📁 Gespeichert: {output_path}")
    
    # Preview
    print("\n📋 Vorschau (erste 5):")
    for i, item in enumerate(results['items'][:5], 1):
        title = item.get('title') or item.get('text') or item.get('email') or str(item)
        print(f"  {i}. {title[:60]}{'...' if len(str(title)) > 60 else ''}")


if __name__ == "__main__":
    main()
