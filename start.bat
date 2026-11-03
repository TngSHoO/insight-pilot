@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup.bat first.
  pause
  exit /b 1
)
echo Starting InsightPilot...
echo Keep this window open while using the website.
".venv\Scripts\python.exe" -m streamlit run app.py

