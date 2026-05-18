@echo off
cd /d "%~dp0"
echo ====================================================
echo  💻 Starting Daily Laptop Scraper Pipeline
echo ====================================================

:: Проверяем наличие виртуального окружения
if exist .venv\Scripts\python.exe (
    set PYTHON_BIN=.venv\Scripts\python.exe
) else (
    set PYTHON_BIN=python
)

echo [1/2] Fetching latest ads from 999.md (All Moldova)...
%PYTHON_BIN% lappars.py --once --region all

echo [2/2] Running spec extraction and price analysis...
%PYTHON_BIN% laptop_analyzer_v3.py

echo ====================================================
echo  ✅ Scraping and analysis finished successfully!
echo ====================================================
pause
