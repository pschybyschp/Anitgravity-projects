#!/usr/bin/env python3
"""
Scrapper Gringo UI Launcher
Startet den Webserver und öffnet automatisch den Browser.
"""

import os
import sys
import time
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

# Port Configuration
PORT = 8080
UI_DIR = Path(__file__).parent / "ui"

class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler ohne Logging."""
    
    def log_message(self, format, *args):
        """Unterdrücke Log-Nachrichten."""
        pass

def start_server():
    """Startet den HTTP Server."""
    os.chdir(UI_DIR)
    server = HTTPServer(('', PORT), QuietHTTPRequestHandler)
    print(f"🌵 Server läuft auf http://localhost:{PORT}")
    print("   Drücke Strg+C zum Beenden\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server beendet")
        sys.exit(0)

def main():
    """Hauptfunktion."""
    print("=" * 50)
    print("🌵 Scrapper Gringo - UI Launcher")
    print("=" * 50)
    print()
    
    # Check if UI directory exists
    if not UI_DIR.exists():
        print(f"❌ UI-Verzeichnis nicht gefunden: {UI_DIR}")
        input("Drücke Enter zum Beenden...")
        sys.exit(1)
    
    # Start server in background thread
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    # Open browser
    url = f"http://localhost:{PORT}"
    print(f"🌐 Öffne Browser: {url}\n")
    webbrowser.open(url)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Scrapper Gringo beendet")
        sys.exit(0)

if __name__ == "__main__":
    main()
