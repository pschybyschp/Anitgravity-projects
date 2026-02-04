#!/usr/bin/env python3
"""
export_to_sheets.py - Export lead data to Google Sheets

This script exports enriched lead data to a Google Sheet with columns:
Name, Website, Phone, Email, Score, Facebook, Instagram, TikTok, X, LinkedIn

Usage:
    python export_to_sheets.py --input .tmp/enriched_*.txt
    python export_to_sheets.py --input .tmp/enriched_*.txt --sheet-id "1abc..."
    python export_to_sheets.py --input .tmp/enriched_*.txt --title "My Leads"

Requirements:
    pip install google-auth google-auth-oauthlib google-api-python-client python-dotenv

Setup:
    1. Enable Google Sheets API in Cloud Console
    2. Create OAuth 2.0 Client ID (Desktop App) and download as client_secret.json
    3. Run script - it will open browser for authentication
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from dotenv import load_dotenv
except ImportError:
    print("Error: Missing dependencies. Run:")
    print("  pip install google-auth google-auth-oauthlib google-api-python-client python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Scopes for Sheets and Drive access
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


def get_credentials():
    """Get Google API credentials using OAuth2 flow."""
    creds = None
    project_root = Path(__file__).parent.parent
    creds_dir = project_root / "credentials"
    token_file = creds_dir / "token.json"
    
    # Look for client secrets file
    secret_paths = [
        creds_dir / "client_secret.json",
        creds_dir / "credentials.json",
        creds_dir / "oauth_credentials.json",
        project_root / "client_secret.json",  # Fallback
    ]
    
    secret_file = None
    for path in secret_paths:
        if path.exists():
            # Check if it's an OAuth client (not service account)
            with open(path) as f:
                data = json.load(f)
                if "installed" in data or "web" in data:
                    secret_file = path
                    break
    
    # Check if we have a saved token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    
    # If no valid credentials, do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secret_file:
                print("Error: OAuth client credentials not found.")
                print("\nTo set up Google Sheets API with OAuth:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Enable 'Google Sheets API'")
                print("3. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
                print("4. Choose 'Desktop app' as application type")
                print("5. Download the JSON and save as 'client_secret.json' in project root")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def parse_json_file(filepath: str) -> list:
    """Parse a JSON file with scraped data."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if 'items' in data:
            return data['items']
        elif 'results' in data:
            return data['results']
        else:
            return [data]
    return []


def parse_enriched_file(filepath: str) -> list:
    """
    Parse an enriched lead file to extract business data.
    Supports both TXT and JSON formats.
    
    Returns list of dicts
    """
    # Check if JSON
    if filepath.endswith('.json'):
        return parse_json_file(filepath)
    
    # Original TXT parsing for lead files
    businesses = []
    current_biz = {}
    in_email_section = False
    in_social_section = False
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # New business entry - look for the name line
        if line.startswith("[") and "]" in line:
            # Save previous business
            if current_biz.get("name"):
                businesses.append(current_biz)
            
            # Extract name from "[1] Business Name"
            match = re.search(r"\[\d+\]\s*(.+)", line)
            if match:
                current_biz = {
                    "name": match.group(1).strip(),
                    "website": "",
                    "phone": "",
                    "email": "",
                    "score": 0,
                    "facebook": "",
                    "instagram": "",
                    "tiktok": "",
                    "twitter": "",
                    "linkedin": "",
                }
            in_email_section = False
            in_social_section = False
        
        # Parse score from "LEAD-SCORE: ★★★★☆ (4/5 Punkte)"
        elif "LEAD-SCORE:" in line:
            match = re.search(r"\((\d+)/5", line)
            if match:
                current_biz["score"] = int(match.group(1))
        
        # Parse contact details
        elif line.startswith("Adresse:"):
            current_biz["address"] = line.replace("Adresse:", "").strip()
        elif line.startswith("Telefon:"):
            current_biz["phone"] = line.replace("Telefon:", "").strip()
        elif line.startswith("Website:"):
            website = line.replace("Website:", "").strip()
            if website != "Nicht verfügbar":
                current_biz["website"] = website
        
        # Email section
        elif "E-MAIL:" in line:
            in_email_section = True
            in_social_section = False
        elif in_email_section and line.startswith("✓"):
            email = line.replace("✓", "").strip()
            current_biz["email"] = email
            in_email_section = False
        elif in_email_section and "✗" in line:
            in_email_section = False
        
        # Social media section
        elif "SOCIAL MEDIA:" in line:
            in_social_section = True
            in_email_section = False
        elif in_social_section and line.startswith("✓"):
            # Parse social links like "✓ Facebook: https://..."
            parts = line.replace("✓", "").strip().split(":", 1)
            if len(parts) == 2:
                platform = parts[0].strip().lower()
                link = parts[1].strip()
                
                if platform in current_biz:
                    current_biz[platform] = link
        elif in_social_section and ("✗" in line or "COLD-EMAIL" in line):
            in_social_section = False
    
    # Don't forget the last business
    if current_biz.get("name"):
        businesses.append(current_biz)
    
    return businesses


def export_generic_data(items: list, sheet_id: str = None, title: str = None) -> str:
    """
    Export any list of dicts to Google Sheets.
    Automatically detects columns from data.
    """
    if not items:
        return None
    
    credentials = get_credentials()
    service = build('sheets', 'v4', credentials=credentials)
    
    # Create new sheet if no ID provided
    if not sheet_id:
        if not title:
            title = f"Scrapper Export {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"📊 Erstelle neues Sheet: {title}")
        sheet_id = create_new_sheet(service, title)
    
    # Auto-detect headers from data
    all_keys = set()
    for item in items:
        if isinstance(item, dict):
            all_keys.update(item.keys())
    
    # Prioritize common columns
    priority = ['text', 'title', 'name', 'link', 'url', 'type', 'description', 'email', 'phone']
    headers = [k for k in priority if k in all_keys]
    headers += [k for k in sorted(all_keys) if k not in headers]
    
    # Build rows
    rows = [headers]
    for item in items:
        if isinstance(item, dict):
            row = [str(item.get(h, '')) for h in headers]
        else:
            row = [str(item)]
        rows.append(row)
    
    # Write data
    print(f"📝 Schreibe {len(items)} Einträge...")
    
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()
    
    # Format
    print("🎨 Formatiere Sheet...")
    format_sheet(service, sheet_id)
    
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def create_new_sheet(service, title: str) -> str:
    """Create a new Google Sheet and return its ID."""
    spreadsheet = {
        'properties': {
            'title': title
        }
    }
    
    result = service.spreadsheets().create(
        body=spreadsheet,
        fields='spreadsheetId'
    ).execute()
    
    return result.get('spreadsheetId')


def format_sheet(service, sheet_id: str):
    """Apply formatting to the sheet (header styling, column widths)."""
    requests = [
        # Bold header row
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6},
                        'textFormat': {
                            'bold': True,
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                        }
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        # Freeze header row
        {
            'updateSheetProperties': {
                'properties': {
                    'sheetId': 0,
                    'gridProperties': {
                        'frozenRowCount': 1
                    }
                },
                'fields': 'gridProperties.frozenRowCount'
            }
        },
        # Auto-resize columns
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 10
                }
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()


def export_to_sheet(businesses: list, sheet_id: str = None, title: str = None) -> str:
    """
    Export business data to Google Sheets.
    
    Args:
        businesses: List of business dictionaries
        sheet_id: Existing sheet ID (optional)
        title: Title for new sheet (optional)
    
    Returns:
        URL of the Google Sheet
    """
    credentials = get_credentials()
    service = build('sheets', 'v4', credentials=credentials)
    
    # Create new sheet if no ID provided
    if not sheet_id:
        if not title:
            title = f"Lead Export {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"📊 Erstelle neues Sheet: {title}")
        sheet_id = create_new_sheet(service, title)
    
    # Prepare data
    headers = [
        "Name", "Website", "Phone", "Email", "Score",
        "Facebook", "Instagram", "TikTok", "X (Twitter)", "LinkedIn"
    ]
    
    rows = [headers]
    
    for biz in businesses:
        row = [
            biz.get("name", ""),
            biz.get("website", ""),
            biz.get("phone", ""),
            biz.get("email", ""),
            biz.get("score", 0),
            biz.get("facebook", ""),
            biz.get("instagram", ""),
            biz.get("tiktok", ""),
            biz.get("twitter", ""),
            biz.get("linkedin", ""),
        ]
        rows.append(row)
    
    # Write data to sheet
    print(f"📝 Schreibe {len(businesses)} Einträge...")
    
    body = {'values': rows}
    
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='A1',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    # Apply formatting
    print("🎨 Formatiere Sheet...")
    format_sheet(service, sheet_id)
    
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    
    return sheet_url


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export enriched lead data to Google Sheets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_to_sheets.py --input .tmp/enriched_*.txt
  python export_to_sheets.py --input .tmp/enriched_*.txt --title "Tischler Leads"
  python export_to_sheets.py --input .tmp/enriched_*.txt --sheet-id "1abc..."
        """
    )
    
    parser.add_argument("-i", "--input", required=True,
                        help="Path to enriched lead file")
    parser.add_argument("-s", "--sheet-id",
                        help="Existing Google Sheet ID (creates new if not provided)")
    parser.add_argument("-t", "--title",
                        help="Title for new sheet (default: auto-generated)")
    
    args = parser.parse_args()
    
    # Handle glob patterns
    input_path = args.input
    if "*" in input_path:
        import glob
        matches = glob.glob(input_path)
        if not matches:
            print(f"Error: No files matching '{input_path}'")
            sys.exit(1)
        input_path = sorted(matches)[-1]  # Use most recent
    
    print(f"\n📂 Lese Datei: {input_path}")
    
    # Parse the file
    items = parse_enriched_file(input_path)
    
    if not items:
        print("Keine Daten zum Exportieren gefunden.")
        sys.exit(0)
    
    print(f"   Gefunden: {len(items)} Einträge\n")
    
    # Export to Google Sheets - use generic export for JSON, specific for enriched TXT
    try:
        if input_path.endswith('.json'):
            sheet_url = export_generic_data(
                items,
                sheet_id=args.sheet_id,
                title=args.title
            )
        else:
            sheet_url = export_to_sheet(
                items,
                sheet_id=args.sheet_id,
                title=args.title
            )
        
        print(f"\n✅ Export erfolgreich!")
        print(f"📊 Google Sheet: {sheet_url}\n")
        
    except HttpError as e:
        print(f"\n❌ Google API Fehler: {e}")
        if "403" in str(e):
            print("\nMögliche Ursachen:")
            print("- Google Sheets API ist nicht aktiviert")
            print("- Authentifizierung fehlgeschlagen")
        sys.exit(1)


if __name__ == "__main__":
    main()
