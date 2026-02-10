@echo off
REM Scrapper Gringo UI Launcher
REM Doppelklicken um die UI zu starten

cls
echo ===============================================
echo    Scrapper Gringo - Web Interface
echo ===============================================
echo.
echo Starte Server...
echo.

cd /d "%~dp0"
python launch_ui.py

pause
