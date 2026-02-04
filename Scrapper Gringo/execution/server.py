#!/usr/bin/env python3
"""
server.py - Backend API für Scrapper Gringo Web UI

Stellt REST-Endpoints bereit für:
- URL Scraping (single + deep)
- Places API Scraping
- Google Sheets Export

Usage:
    python server.py
    # Server läuft auf http://localhost:5000

Requirements:
    pip install flask flask-cors
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add execution folder to path
sys.path.insert(0, str(Path(__file__).parent))

from scrape_url import scrape_url, save_results as save_url_results
from deep_scrape import stage1_scrape, stage2_scrape, save_results as save_deep_results
from export_to_sheets import export_generic_data, parse_enriched_file

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Main scraping endpoint.
    
    Request body:
    {
        "mode": "url" | "places" | "deep",
        "url": "https://...",           # for url/deep mode
        "extract": "what to extract",   # for url mode
        "query": "business type",       # for places mode
        "location": "city",             # for places mode
        "limit": 10,                    # optional
        "stage2": "pattern",            # for deep mode
        "filter": "/videos/",           # optional URL filter
        "sheetTitle": "My Export",      # optional
        "exportToSheets": true          # optional
    }
    """
    try:
        data = request.get_json()
        
        mode = data.get('mode', 'url')
        export_to_sheets = data.get('exportToSheets', True)
        sheet_title = data.get('sheetTitle', f'Scrapper Export {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        results = []
        
        if mode == 'url':
            # Simple URL scraping
            url = data.get('url')
            extract = data.get('extract', 'all content')
            
            if not url:
                return jsonify({'success': False, 'error': 'URL is required'}), 400
            
            result = scrape_url(url, extract)
            
            if not result.get('success'):
                return jsonify({'success': False, 'error': result.get('error', 'Scraping failed')}), 500
            
            results = result.get('items', [])
            save_url_results(result)
            
        elif mode == 'places':
            # Places API scraping
            query = data.get('query')
            location = data.get('location')
            limit = data.get('limit', 10)
            
            if not query or not location:
                return jsonify({'success': False, 'error': 'Query and location are required'}), 400
            
            # Import here to avoid dependency issues
            try:
                from scrape_gmb import search_places
                api_key = os.getenv('GOOGLE_PLACES_API_KEY')
                if not api_key:
                    return jsonify({'success': False, 'error': 'GOOGLE_PLACES_API_KEY not configured'}), 500
                
                results = search_places(query, location, api_key, limit)
            except ImportError:
                return jsonify({'success': False, 'error': 'Places scraping not available'}), 500
            
        elif mode == 'deep':
            # Two-stage deep scraping
            url = data.get('url')
            places_query = data.get('query')
            location = data.get('location')
            stage2_pattern = data.get('stage2', 'description, tools')
            url_filter = data.get('filter')
            limit = data.get('limit', 10)
            
            if not url and not places_query:
                return jsonify({'success': False, 'error': 'URL or query+location required'}), 400
            
            # Stage 1
            stage1_results = stage1_scrape(
                url=url,
                places_query=places_query,
                location=location,
                pattern='links',
                limit=limit * 3 if url_filter else limit
            )
            
            # Apply filter
            if url_filter and stage1_results:
                stage1_results = [item for item in stage1_results 
                                  if url_filter.lower() in item.get('url', '').lower()][:limit]
            
            if not stage1_results:
                return jsonify({'success': False, 'error': 'No results from Stage 1'}), 404
            
            # Stage 2
            results = stage2_scrape(stage1_results, stage2_pattern, delay=1.0)
            save_deep_results(results, 'api_deep')
            
        else:
            return jsonify({'success': False, 'error': f'Unknown mode: {mode}'}), 400
        
        # Export to Sheets if requested
        sheet_url = None
        if export_to_sheets and results:
            try:
                sheet_url = export_generic_data(results, title=sheet_title)
            except Exception as e:
                print(f"Sheets export failed: {e}")
        
        # Build response
        response = {
            'success': True,
            'count': len(results),
            'mode': mode,
            'items': results[:50],  # Limit response size
            'sheetUrl': sheet_url,
            'preview': format_preview(results[:3])
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def format_preview(items):
    """Format items for preview display."""
    lines = []
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            title = item.get('title') or item.get('text') or item.get('name') or 'No title'
            desc = item.get('description', '')[:80]
            lines.append(f"{i}. {title[:60]}")
            if desc:
                lines.append(f"   {desc}...")
        else:
            lines.append(f"{i}. {str(item)[:80]}")
    return '\n'.join(lines)


@app.route('/export', methods=['POST'])
def export():
    """
    Export existing data to Google Sheets.
    
    Request body:
    {
        "items": [...],           # Data to export
        "title": "Sheet Title"    # Optional
    }
    """
    try:
        data = request.get_json()
        items = data.get('items', [])
        title = data.get('title', f'Scrapper Export {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        if not items:
            return jsonify({'success': False, 'error': 'No items to export'}), 400
        
        sheet_url = export_generic_data(items, title=title)
        
        return jsonify({
            'success': True,
            'sheetUrl': sheet_url
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/files', methods=['GET'])
def list_files():
    """List scraped files in .tmp directory."""
    tmp_dir = Path(__file__).parent.parent / '.tmp'
    
    if not tmp_dir.exists():
        return jsonify({'files': []})
    
    files = []
    for f in sorted(tmp_dir.glob('*.json'), reverse=True)[:20]:
        files.append({
            'name': f.name,
            'size': f.stat().st_size,
            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    
    return jsonify({'files': files})


@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    """Get contents of a scraped file."""
    tmp_dir = Path(__file__).parent.parent / '.tmp'
    filepath = tmp_dir / filename
    
    if not filepath.exists() or not filepath.suffix == '.json':
        return jsonify({'error': 'File not found'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return jsonify(data)


if __name__ == '__main__':
    print("\n🌵 Scrapper Gringo Backend Server")
    print("=" * 40)
    print("📡 Starting on http://localhost:5000")
    print("📝 Endpoints:")
    print("   POST /scrape  - Run scraping")
    print("   POST /export  - Export to Sheets")
    print("   GET  /files   - List scraped files")
    print("   GET  /health  - Health check")
    print("=" * 40 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
