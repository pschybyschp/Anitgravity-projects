#!/usr/bin/env python3
"""
scrape_gmb.py - Google My Business Lead Scraper

This script extracts business listing details from Google Places API
for lead generation purposes.

Usage:
    python scrape_gmb.py --query "Tischler" --location "Tostedt" --limit 10
    python scrape_gmb.py --query "plumbers" --location "New York" --limit 20 --format json

Requirements:
    pip install requests python-dotenv

Environment:
    GOOGLE_PLACES_API_KEY - Your Google Places API key (set in .env)
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Error: Missing dependencies. Run: pip install requests python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Constants
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
REQUEST_DELAY = 0.2  # Delay between API calls (seconds)


def get_api_key():
    """Get Google Places API key from environment."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("Error: GOOGLE_PLACES_API_KEY not found in environment.")
        print("Please add it to your .env file:")
        print("  GOOGLE_PLACES_API_KEY=your_api_key_here")
        print("\nGet an API key at: https://console.cloud.google.com/apis/credentials")
        sys.exit(1)
    return api_key


def search_places(query: str, location: str, api_key: str, limit: int = 10) -> list:
    """
    Search for places using Google Places Text Search API.
    
    Args:
        query: Business type/category (e.g., "Tischler", "plumbers")
        location: Geographic area (e.g., "Tostedt", "New York")
        api_key: Google Places API key
        limit: Maximum number of results to return
        
    Returns:
        List of place dictionaries with basic info
    """
    search_query = f"{query} in {location}"
    places = []
    next_page_token = None
    
    print(f"Searching for: {search_query}")
    
    while len(places) < limit:
        params = {
            "query": search_query,
            "key": api_key,
        }
        
        if next_page_token:
            params["pagetoken"] = next_page_token
            # Google requires a short delay before using next_page_token
            time.sleep(2)
        
        response = requests.get(PLACES_TEXT_SEARCH_URL, params=params)
        data = response.json()
        
        if data.get("status") != "OK":
            error_msg = data.get("error_message", data.get("status", "Unknown error"))
            print(f"API Error: {error_msg}")
            break
        
        results = data.get("results", [])
        places.extend(results)
        
        print(f"  Found {len(results)} results (total: {len(places)})")
        
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
            
        time.sleep(REQUEST_DELAY)
    
    return places[:limit]


def get_place_details(place_id: str, api_key: str) -> dict:
    """
    Get detailed information for a place using Google Places Details API.
    
    Args:
        place_id: Google Place ID
        api_key: Google Places API key
        
    Returns:
        Dictionary with detailed place information
    """
    params = {
        "place_id": place_id,
        "key": api_key,
        "fields": "name,formatted_address,formatted_phone_number,website,opening_hours,rating,user_ratings_total,types,url"
    }
    
    response = requests.get(PLACES_DETAILS_URL, params=params)
    data = response.json()
    
    if data.get("status") != "OK":
        return {}
    
    return data.get("result", {})


def format_opening_hours(hours_data: dict) -> str:
    """Format opening hours into readable string."""
    if not hours_data:
        return "Nicht verfügbar"
    
    weekday_text = hours_data.get("weekday_text", [])
    if weekday_text:
        return " | ".join(weekday_text)
    
    return "Siehe Website"


def extract_business_info(place: dict, details: dict) -> dict:
    """
    Extract and structure business information from API response.
    
    Args:
        place: Basic place data from Text Search
        details: Detailed place data from Details API
        
    Returns:
        Structured business information dictionary
    """
    # Get types/categories
    types = details.get("types", place.get("types", []))
    human_readable_types = [t.replace("_", " ").title() for t in types if not t.startswith("point_of_interest")]
    
    return {
        "name": details.get("name", place.get("name", "Unbekannt")),
        "address": details.get("formatted_address", place.get("formatted_address", "Nicht verfügbar")),
        "phone": details.get("formatted_phone_number", "Nicht verfügbar"),
        "website": details.get("website", "Nicht verfügbar"),
        "google_maps_url": details.get("url", ""),
        "rating": details.get("rating", place.get("rating", "Keine Bewertung")),
        "review_count": details.get("user_ratings_total", place.get("user_ratings_total", 0)),
        "categories": ", ".join(human_readable_types[:3]) if human_readable_types else "Nicht kategorisiert",
        "opening_hours": format_opening_hours(details.get("opening_hours")),
    }


def format_as_text(businesses: list, query: str, location: str) -> str:
    """Format business list as plain text."""
    lines = [
        "=" * 80,
        f"  LEAD-LISTE: {query.upper()} IN {location.upper()}",
        f"  Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "=" * 80,
        ""
    ]
    
    for i, biz in enumerate(businesses, 1):
        lines.append(f"--- {i}. {biz['name']} ---")
        lines.append(f"Adresse:      {biz['address']}")
        lines.append(f"Telefon:      {biz['phone']}")
        lines.append(f"Website:      {biz['website']}")
        lines.append(f"Bewertung:    {biz['rating']} ({biz['review_count']} Bewertungen)")
        lines.append(f"Kategorie:    {biz['categories']}")
        lines.append(f"Öffnungszeiten: {biz['opening_hours']}")
        if biz['google_maps_url']:
            lines.append(f"Google Maps:  {biz['google_maps_url']}")
        lines.append("")
    
    lines.extend([
        "=" * 80,
        f"  Gesamt: {len(businesses)} Einträge",
        "=" * 80,
    ])
    
    return "\n".join(lines)


def format_as_json(businesses: list, query: str, location: str) -> str:
    """Format business list as JSON."""
    output = {
        "meta": {
            "query": query,
            "location": location,
            "count": len(businesses),
            "generated_at": datetime.now().isoformat()
        },
        "businesses": businesses
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def format_as_csv(businesses: list) -> str:
    """Format business list as CSV."""
    headers = ["Name", "Adresse", "Telefon", "Website", "Bewertung", "Anzahl Bewertungen", "Kategorie"]
    lines = [",".join(headers)]
    
    for biz in businesses:
        row = [
            f'"{biz["name"]}"',
            f'"{biz["address"]}"',
            f'"{biz["phone"]}"',
            f'"{biz["website"]}"',
            str(biz["rating"]),
            str(biz["review_count"]),
            f'"{biz["categories"]}"'
        ]
        lines.append(",".join(row))
    
    return "\n".join(lines)


def save_output(content: str, query: str, location: str, format_type: str) -> str:
    """Save output to .tmp directory."""
    # Create safe filename
    safe_query = query.lower().replace(" ", "_")[:20]
    safe_location = location.lower().replace(" ", "_")[:20]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    extensions = {"text": "txt", "json": "json", "csv": "csv"}
    ext = extensions.get(format_type, "txt")
    
    filename = f"{safe_query}_{safe_location}_{timestamp}.{ext}"
    
    # Ensure .tmp directory exists
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    filepath = tmp_dir / filename
    filepath.write_text(content, encoding="utf-8")
    
    return str(filepath)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape Google My Business listings for lead generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_gmb.py --query "Tischler" --location "Tostedt" --limit 10
  python scrape_gmb.py --query "plumbers" --location "New York" --format json
  python scrape_gmb.py -q "dentists" -l "Berlin" -n 20 -f csv
        """
    )
    
    parser.add_argument("-q", "--query", required=True,
                        help="Business type/category to search for (e.g., 'Tischler', 'plumbers')")
    parser.add_argument("-l", "--location", required=True,
                        help="Geographic area to search (e.g., 'Tostedt', 'New York')")
    parser.add_argument("-n", "--limit", type=int, default=10,
                        help="Maximum number of results (default: 10)")
    parser.add_argument("-f", "--format", choices=["text", "json", "csv"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--no-details", action="store_true",
                        help="Skip fetching detailed info (faster, but less data)")
    parser.add_argument("--output", "-o",
                        help="Custom output file path (default: .tmp/<auto-generated>)")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = get_api_key()
    
    # Search for places
    print(f"\n🔍 Suche nach '{args.query}' in '{args.location}'...\n")
    places = search_places(args.query, args.location, api_key, args.limit)
    
    if not places:
        print("Keine Ergebnisse gefunden.")
        sys.exit(0)
    
    # Fetch details for each place
    businesses = []
    print(f"\n📋 Hole Details für {len(places)} Einträge...")
    
    for i, place in enumerate(places, 1):
        place_id = place.get("place_id")
        
        if args.no_details:
            details = {}
        else:
            print(f"  [{i}/{len(places)}] {place.get('name', 'Unknown')}")
            details = get_place_details(place_id, api_key)
            time.sleep(REQUEST_DELAY)
        
        business_info = extract_business_info(place, details)
        businesses.append(business_info)
    
    # Format output
    if args.format == "json":
        content = format_as_json(businesses, args.query, args.location)
    elif args.format == "csv":
        content = format_as_csv(businesses)
    else:
        content = format_as_text(businesses, args.query, args.location)
    
    # Save output
    if args.output:
        output_path = args.output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
    else:
        output_path = save_output(content, args.query, args.location, args.format)
    
    print(f"\n✅ Fertig! {len(businesses)} Einträge gefunden.")
    print(f"📁 Gespeichert unter: {output_path}\n")
    
    # Also print to stdout for convenience
    if args.format == "text":
        print(content)


if __name__ == "__main__":
    main()
