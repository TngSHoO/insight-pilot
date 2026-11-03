@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo InsightPilot - First-time setup
echo ========================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.12 first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating a private Python environment...
  python -m venv .venv
)
echo Installing project packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Setup failed. Copy the error message and send it to your assistant.
  pause
  exit /b 1
)
echo.
echo Setup completed. You can now double-click start.bat.
pause

