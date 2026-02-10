#!/usr/bin/env python3
"""
Build Script - Erstellt eine .exe aus dem Launcher
Verwendet PyInstaller um eine eigenständige .exe zu erstellen.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_pyinstaller():
    """Prüft ob PyInstaller installiert ist."""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Installiert PyInstaller."""
    print("📦 Installiere PyInstaller...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ PyInstaller erfolgreich installiert\n")
        return True
    else:
        print(f"❌ Fehler bei der Installation:\n{result.stderr}")
        return False

def build_exe():
    """Erstellt die .exe Datei."""
    print("🔨 Erstelle ScrapperGringo.exe...\n")
    
    project_dir = Path(__file__).parent
    launcher_script = project_dir / "launch_ui.py"
    icon_path = project_dir / "ui" / "favicon.ico"  # Optional
    
    # PyInstaller Befehl
    cmd = [
        "pyinstaller",
        "--onefile",                    # Einzelne .exe Datei
        "--windowed",                   # Kein Konsolen-Fenster (für GUI)
        "--name=ScrapperGringo",        # Name der .exe
        "--clean",                      # Clean build
        "--noconfirm",                  # Überschreibe ohne Nachfrage
    ]
    
    # Icon hinzufügen wenn vorhanden
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    
    # Add data files (UI directory)
    ui_dir = project_dir / "ui"
    cmd.extend([
        "--add-data", f"{ui_dir};ui"   # Include UI directory
    ])
    
    cmd.append(str(launcher_script))
    
    print(f"Ausführe: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=project_dir)
    
    if result.returncode == 0:
        exe_path = project_dir / "dist" / "ScrapperGringo.exe"
        print("\n" + "=" * 60)
        print("✅ Build erfolgreich!")
        print("=" * 60)
        print(f"\n📁 .exe Datei: {exe_path}")
        print("\nDu kannst jetzt einfach ScrapperGringo.exe doppelklicken!")
        print("\nHinweis: Die .exe ist in ./dist/ScrapperGringo.exe")
        return True
    else:
        print("\n❌ Build fehlgeschlagen")
        return False

def main():
    print("=" * 60)
    print("🌵 Scrapper Gringo - Build Tool")
    print("=" * 60)
    print()
    
    # Check PyInstaller
    if not check_pyinstaller():
        print("⚠️  PyInstaller nicht gefunden\n")
        response = input("Möchtest du PyInstaller jetzt installieren? (j/n): ")
        if response.lower() in ['j', 'ja', 'y', 'yes']:
            if not install_pyinstaller():
                print("\n❌ Abbruch")
                input("Drücke Enter zum Beenden...")
                return
        else:
            print("\n❌ Abbruch - PyInstaller wird benötigt")
            input("Drücke Enter zum Beenden...")
            return
    else:
        print("✅ PyInstaller gefunden\n")
    
    # Build
    success = build_exe()
    
    print()
    input("Drücke Enter zum Beenden...")

if __name__ == "__main__":
    main()
