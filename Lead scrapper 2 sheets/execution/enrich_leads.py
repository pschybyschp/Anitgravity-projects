#!/usr/bin/env python3
"""
enrich_leads.py - Enrich GMB listings with website data

This script scrapes business websites to extract:
- Email addresses
- Social media handles (Facebook, Instagram, TikTok, LinkedIn, X)
- Generates lead scores and cold email intros

Usage:
    python enrich_leads.py --input .tmp/tischler_tostedt_*.txt
    python enrich_leads.py --query "Tischler" --location "Tostedt"

Requirements:
    pip install requests beautifulsoup4 python-dotenv
"""

import os
import sys
import re
import json
import argparse
import time
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
REQUEST_DELAY = 1.5  # Delay between website requests (seconds)
REQUEST_TIMEOUT = 10  # Timeout for requests

# User agent to appear as a regular browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

# Social media patterns
SOCIAL_PATTERNS = {
    "facebook": r"(?:https?://)?(?:www\.)?facebook\.com/[\w.\-]+/?",
    "instagram": r"(?:https?://)?(?:www\.)?instagram\.com/[\w.\-]+/?",
    "tiktok": r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.\-]+/?",
    "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/[\w.\-]+/?",
    "twitter": r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[\w.\-]+/?",
}

# Email pattern
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# Common obfuscation patterns
EMAIL_OBFUSCATION = [
    (r"\s*\[\s*at\s*\]\s*", "@"),
    (r"\s*\(\s*at\s*\)\s*", "@"),
    (r"\s*\[at\]\s*", "@"),
    (r"\s*\(at\)\s*", "@"),
    (r"\s*\[\s*dot\s*\]\s*", "."),
    (r"\s*\(\s*dot\s*\)\s*", "."),
    (r"\s*\[dot\]\s*", "."),
    (r"\s*\(dot\)\s*", "."),
]


def parse_gmb_file(filepath: str) -> list:
    """
    Parse a GMB listing file to extract business info.
    
    Args:
        filepath: Path to the GMB listing file
        
    Returns:
        List of business dictionaries with name, website, phone, address
    """
    businesses = []
    current_biz = {}
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # New business entry
            if line.startswith("---") and "." in line:
                if current_biz:
                    businesses.append(current_biz)
                # Extract name from "--- 1. Business Name ---"
                match = re.search(r"---\s*\d+\.\s*(.+?)\s*---", line)
                if match:
                    current_biz = {"name": match.group(1)}
            
            # Parse fields
            elif line.startswith("Adresse:"):
                current_biz["address"] = line.replace("Adresse:", "").strip()
            elif line.startswith("Telefon:"):
                current_biz["phone"] = line.replace("Telefon:", "").strip()
            elif line.startswith("Website:"):
                website = line.replace("Website:", "").strip()
                if website != "Nicht verfügbar":
                    current_biz["website"] = website
            elif line.startswith("Bewertung:"):
                current_biz["rating"] = line.replace("Bewertung:", "").strip()
            elif line.startswith("Google Maps:"):
                current_biz["google_maps"] = line.replace("Google Maps:", "").strip()
    
    # Don't forget the last business
    if current_biz:
        businesses.append(current_biz)
    
    return businesses


def deobfuscate_email(text: str) -> str:
    """Remove common email obfuscation patterns."""
    result = text
    for pattern, replacement in EMAIL_OBFUSCATION:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def extract_emails(html: str, soup: BeautifulSoup) -> list:
    """Extract email addresses from HTML content."""
    emails = set()
    
    # Deobfuscate text first
    text = deobfuscate_email(soup.get_text())
    
    # Find emails in text
    found = re.findall(EMAIL_PATTERN, text, re.IGNORECASE)
    emails.update(found)
    
    # Also check href="mailto:..." links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0]
            emails.add(email)
    
    # Filter out common false positives
    filtered = []
    for email in emails:
        email_lower = email.lower()
        # Skip image files, example emails, etc.
        if not any(x in email_lower for x in [".png", ".jpg", ".gif", "example.com", "domain.de", "email.de"]):
            filtered.append(email)
    
    return list(filtered)


def extract_social_links(html: str, soup: BeautifulSoup) -> dict:
    """Extract social media links from HTML content."""
    social = {
        "facebook": None,
        "instagram": None,
        "tiktok": None,
        "linkedin": None,
        "twitter": None,
    }
    
    # Search in all links
    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        
        for platform, pattern in SOCIAL_PATTERNS.items():
            if social[platform] is None:
                match = re.search(pattern, href, re.IGNORECASE)
                if match:
                    social[platform] = match.group(0)
    
    # Also search in full HTML text (sometimes links are in JavaScript)
    html_lower = html.lower()
    for platform, pattern in SOCIAL_PATTERNS.items():
        if social[platform] is None:
            match = re.search(pattern, html_lower, re.IGNORECASE)
            if match:
                social[platform] = match.group(0)
    
    return social


def scrape_website(url: str) -> dict:
    """
    Scrape a website for email and social media info.
    
    Args:
        url: Website URL to scrape
        
    Returns:
        Dictionary with emails and social links
    """
    result = {
        "emails": [],
        "social": {
            "facebook": None,
            "instagram": None,
            "tiktok": None,
            "linkedin": None,
            "twitter": None,
        },
        "error": None,
    }
    
    try:
        # Ensure URL has protocol
        if not url.startswith("http"):
            url = "http://" + url
        
        # Fetch main page
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract from main page
        result["emails"] = extract_emails(html, soup)
        result["social"] = extract_social_links(html, soup)
        
        # Also check common pages for contact info
        contact_pages = ["/kontakt", "/contact", "/impressum", "/about", "/ueber-uns"]
        
        for page in contact_pages:
            # Only fetch if we're still missing email
            if not result["emails"]:
                try:
                    contact_url = urljoin(url, page)
                    resp = requests.get(contact_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                    if resp.status_code == 200:
                        contact_soup = BeautifulSoup(resp.text, "html.parser")
                        result["emails"].extend(extract_emails(resp.text, contact_soup))
                        
                        # Update social links if still missing
                        new_social = extract_social_links(resp.text, contact_soup)
                        for platform, link in new_social.items():
                            if result["social"][platform] is None and link:
                                result["social"][platform] = link
                    
                    time.sleep(0.5)  # Small delay between pages
                except:
                    pass
        
        # Deduplicate emails
        result["emails"] = list(set(result["emails"]))
        
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result


def calculate_lead_score(business: dict, website_data: dict) -> int:
    """
    Calculate lead score based on criteria.
    
    Scoring:
    - 1 point: Is a service business (assumed for Tischler)
    - 3 points: Has an email address
    - 1 point: Has at least one social media handle
    
    Returns:
        Score from 0-5
    """
    score = 0
    
    # 1 point for service business (Tischler = yes)
    score += 1
    
    # 3 points for having email
    if website_data.get("emails"):
        score += 3
    
    # 1 point for having any social media
    social = website_data.get("social", {})
    if any(social.values()):
        score += 1
    
    return score


def generate_cold_email(business: dict, website_data: dict, score: int) -> str:
    """
    Generate a personalized cold email intro for SEO services.
    
    Args:
        business: Business info dictionary
        website_data: Scraped website data
        score: Lead score
        
    Returns:
        Cold email intro text
    """
    name = business.get("name", "Ihr Unternehmen")
    
    # Identify weaknesses for personalization
    weaknesses = []
    
    if not website_data.get("emails"):
        weaknesses.append("keine sichtbare E-Mail-Adresse auf Ihrer Website")
    
    social = website_data.get("social", {})
    missing_social = [p for p, v in social.items() if v is None]
    
    if len(missing_social) >= 4:
        weaknesses.append("kaum Social-Media-Präsenz")
    elif len(missing_social) >= 2:
        weaknesses.append(f"fehlende Präsenz auf {', '.join(missing_social[:2])}")
    
    if not business.get("website"):
        weaknesses.append("keine eigene Website")
    
    # Build personalized intro
    if weaknesses:
        weakness_text = " und ".join(weaknesses[:2])
        intro = f"""Betreff: Mehr Kunden für {name} – durch bessere Online-Sichtbarkeit

Guten Tag,

ich bin auf {name} aufmerksam geworden und habe mir Ihre Online-Präsenz angeschaut. 

Mir ist aufgefallen, dass Sie {weakness_text} haben. In der heutigen Zeit suchen viele Kunden online nach Tischlereien in ihrer Nähe – und genau hier sehe ich großes Potenzial für Ihr Unternehmen.

Mit gezielter Suchmaschinenoptimierung (SEO) könnten Sie:
• Bei Google für "Tischler + Ihre Region" auf Seite 1 erscheinen
• Mehr Kundenanfragen über Ihre Website erhalten
• Sich von der Konkurrenz abheben

Hätten Sie Interesse an einem kurzen, unverbindlichen Gespräch, um zu besprechen, wie wir Ihre Online-Sichtbarkeit verbessern können?

Mit freundlichen Grüßen"""
    else:
        intro = f"""Betreff: Noch mehr Reichweite für {name}?

Guten Tag,

ich bin auf {name} aufmerksam geworden und war beeindruckt von Ihrer professionellen Online-Präsenz.

Dennoch gibt es immer Möglichkeiten zur Optimierung. Mit gezielter SEO-Strategie könnten Sie:
• Ihre Google-Rankings weiter verbessern
• Mehr qualifizierte Kundenanfragen generieren
• Ihre Marke in der Region stärken

Hätten Sie Interesse an einem kurzen, unverbindlichen Gespräch?

Mit freundlichen Grüßen"""
    
    return intro


def format_output(enriched_businesses: list, query: str, location: str) -> str:
    """Format enriched business data as text output."""
    lines = [
        "=" * 80,
        f"  LEAD-ENRICHMENT: {query.upper()} IN {location.upper()}",
        f"  Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "=" * 80,
        "",
        "  BEWERTUNGSSYSTEM:",
        "  • 1 Punkt: Dienstleistungsunternehmen",
        "  • 3 Punkte: Hat E-Mail-Adresse", 
        "  • 1 Punkt: Hat Social-Media-Präsenz",
        "  • Maximum: 5 Punkte",
        "",
        "=" * 80,
        "",
    ]
    
    for i, biz in enumerate(enriched_businesses, 1):
        score = biz.get("lead_score", 0)
        score_stars = "★" * score + "☆" * (5 - score)
        
        lines.append(f"{'─' * 80}")
        lines.append(f"  [{i}] {biz['name']}")
        lines.append(f"      LEAD-SCORE: {score_stars} ({score}/5 Punkte)")
        lines.append(f"{'─' * 80}")
        lines.append("")
        
        # Contact info
        lines.append("  📍 KONTAKTDATEN:")
        lines.append(f"      Adresse:  {biz.get('address', 'Nicht verfügbar')}")
        lines.append(f"      Telefon:  {biz.get('phone', 'Nicht verfügbar')}")
        lines.append(f"      Website:  {biz.get('website', 'Nicht verfügbar')}")
        lines.append(f"      Bewertung: {biz.get('rating', 'Nicht verfügbar')}")
        lines.append("")
        
        # Scraped data
        website_data = biz.get("website_data", {})
        
        lines.append("  📧 E-MAIL:")
        emails = website_data.get("emails", [])
        if emails:
            for email in emails:
                lines.append(f"      ✓ {email}")
        else:
            lines.append("      ✗ Keine E-Mail gefunden")
        lines.append("")
        
        lines.append("  📱 SOCIAL MEDIA:")
        social = website_data.get("social", {})
        has_social = False
        for platform, link in social.items():
            if link:
                lines.append(f"      ✓ {platform.capitalize()}: {link}")
                has_social = True
        if not has_social:
            lines.append("      ✗ Keine Social-Media-Profile gefunden")
        lines.append("")
        
        # Error if any
        if website_data.get("error"):
            lines.append(f"  ⚠️  FEHLER: {website_data['error']}")
            lines.append("")
        
        # Cold email
        lines.append("  ✉️  COLD-EMAIL INTRO:")
        lines.append("  " + "-" * 76)
        cold_email = biz.get("cold_email", "")
        for email_line in cold_email.split("\n"):
            lines.append(f"      {email_line}")
        lines.append("  " + "-" * 76)
        lines.append("")
        lines.append("")
    
    # Summary
    lines.append("=" * 80)
    lines.append("  ZUSAMMENFASSUNG")
    lines.append("=" * 80)
    
    total = len(enriched_businesses)
    high_score = sum(1 for b in enriched_businesses if b.get("lead_score", 0) >= 4)
    with_email = sum(1 for b in enriched_businesses if b.get("website_data", {}).get("emails"))
    with_social = sum(1 for b in enriched_businesses if any(b.get("website_data", {}).get("social", {}).values()))
    
    lines.append(f"  Gesamt analysiert:     {total}")
    lines.append(f"  High-Score Leads (4+): {high_score}")
    lines.append(f"  Mit E-Mail:            {with_email}")
    lines.append(f"  Mit Social Media:      {with_social}")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def save_output(content: str, query: str, location: str) -> str:
    """Save output to .tmp directory."""
    safe_query = query.lower().replace(" ", "_")[:20]
    safe_location = location.lower().replace(" ", "_")[:20]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"enriched_{safe_query}_{safe_location}_{timestamp}.txt"
    
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    filepath = tmp_dir / filename
    filepath.write_text(content, encoding="utf-8")
    
    return str(filepath)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich GMB listings with email and social media data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enrich_leads.py --input .tmp/tischler_tostedt_*.txt
  python enrich_leads.py --query "Tischler" --location "Tostedt"
        """
    )
    
    parser.add_argument("-i", "--input",
                        help="Path to GMB listing file to enrich")
    parser.add_argument("-q", "--query",
                        help="Business type (used with --location to fetch fresh)")
    parser.add_argument("-l", "--location",
                        help="Location (used with --query to fetch fresh)")
    parser.add_argument("-o", "--output",
                        help="Custom output file path")
    
    args = parser.parse_args()
    
    # Determine source of data
    if args.input:
        # Parse existing file
        input_path = args.input
        
        # Handle glob patterns
        if "*" in input_path:
            import glob
            matches = glob.glob(input_path)
            if not matches:
                print(f"Error: No files matching '{input_path}'")
                sys.exit(1)
            input_path = sorted(matches)[-1]  # Use most recent
        
        print(f"\n📂 Lese GMB-Datei: {input_path}")
        businesses = parse_gmb_file(input_path)
        
        # Extract query/location from filename if not provided
        fname = Path(input_path).stem
        parts = fname.replace("_", " ").split()
        query = args.query or parts[0] if parts else "Business"
        location = args.location or parts[1] if len(parts) > 1 else "Unknown"
        
    elif args.query and args.location:
        # Fetch fresh using scrape_gmb.py
        print(f"\n🔍 Hole frische Daten für '{args.query}' in '{args.location}'...")
        
        # Import and run scrape_gmb
        import subprocess
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent / "scrape_gmb.py"),
            "-q", args.query,
            "-l", args.location,
            "-f", "json"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error running scrape_gmb.py: {result.stderr}")
            sys.exit(1)
        
        # Find the generated JSON file
        import glob
        json_files = sorted(glob.glob(str(Path(__file__).parent.parent / ".tmp" / "*.json")))
        if not json_files:
            print("Error: No JSON output found from scrape_gmb.py")
            sys.exit(1)
        
        with open(json_files[-1], "r", encoding="utf-8") as f:
            data = json.load(f)
        
        businesses = data.get("businesses", [])
        query = args.query
        location = args.location
    else:
        parser.print_help()
        print("\nError: Provide either --input or both --query and --location")
        sys.exit(1)
    
    if not businesses:
        print("Keine Geschäfte zum Analysieren gefunden.")
        sys.exit(0)
    
    print(f"\n📋 Analysiere {len(businesses)} Geschäfte...\n")
    
    # Enrich each business
    enriched = []
    
    for i, biz in enumerate(businesses, 1):
        name = biz.get("name", "Unknown")
        website = biz.get("website")
        
        print(f"  [{i}/{len(businesses)}] {name}")
        
        if website:
            print(f"      → Scrape {website}")
            website_data = scrape_website(website)
            time.sleep(REQUEST_DELAY)
        else:
            print("      → Keine Website vorhanden")
            website_data = {"emails": [], "social": {}, "error": "Keine Website"}
        
        # Calculate score
        score = calculate_lead_score(biz, website_data)
        print(f"      → Score: {score}/5")
        
        # Generate cold email
        cold_email = generate_cold_email(biz, website_data, score)
        
        # Add to enriched list
        enriched_biz = {**biz}
        enriched_biz["website_data"] = website_data
        enriched_biz["lead_score"] = score
        enriched_biz["cold_email"] = cold_email
        enriched.append(enriched_biz)
    
    # Sort by lead score (highest first)
    enriched.sort(key=lambda x: x.get("lead_score", 0), reverse=True)
    
    # Format output
    output = format_output(enriched, query, location)
    
    # Save
    if args.output:
        output_path = args.output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output, encoding="utf-8")
    else:
        output_path = save_output(output, query, location)
    
    print(f"\n✅ Fertig! {len(enriched)} Leads analysiert.")
    print(f"📁 Gespeichert unter: {output_path}\n")
    
    # Print summary
    high_score = sum(1 for b in enriched if b.get("lead_score", 0) >= 4)
    print(f"   🎯 High-Score Leads (4+): {high_score}/{len(enriched)}")


if __name__ == "__main__":
    main()
