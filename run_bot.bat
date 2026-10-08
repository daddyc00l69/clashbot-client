@echo off
title ClashBot AI - Autonomous Game Intelligence Suite
echo ==========================================================
echo   ClashBot AI - Autonomous Game Intelligence Suite
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not installed or not in PATH.
    echo [*] Please install Python 3.10+ from https://www.python.org/
    echo [*] Ensure you check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python -c "import PySide6, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required UI and networking components (PySide6, websockets)...
    python -m pip install PySide6 websockets
)

python run.py
pause
