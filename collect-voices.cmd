@echo off
cd /d "%~dp0"
python collect_elevenlabs_catalog.py --ask-key
pause
