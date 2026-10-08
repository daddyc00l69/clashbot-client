@echo off
title ClashBot AI - Autonomous Game Intelligence Suite
echo ==========================================================
echo   ClashBot AI - Autonomous Game Intelligence Suite
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

set "PY_CMD="

:: 1. Check direct LocalAppData Python 3.10 installation
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    "%LocalAppData%\Programs\Python\Python310\python.exe" -c "import sys; sys.exit(42 if sys.version_info[:2] == (3, 10) else 1)" >nul 2>&1
    if %ERRORLEVEL% EQU 42 (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
        goto :VERIFY_RUNTIME
    )
)

:: 2. Check direct Program Files Python 3.10 installation
if exist "C:\Program Files\Python310\python.exe" (
    "C:\Program Files\Python310\python.exe" -c "import sys; sys.exit(42 if sys.version_info[:2] == (3, 10) else 1)" >nul 2>&1
    if %ERRORLEVEL% EQU 42 (
        set "PY_CMD=C:\Program Files\Python310\python.exe"
        goto :VERIFY_RUNTIME
    )
)

:: 3. Check python in PATH if it is genuinely Python 3.10
python -c "import sys; sys.exit(42 if sys.version_info[:2] == (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 42 (
    set "PY_CMD=python"
    goto :VERIFY_RUNTIME
)

:: Python 3.10 is not installed (e.g. system only has Python 3.11/3.12 or no Python)
echo [!] ClashBot AI requires Python 3.10 (64-bit) for binary UI compatibility.
echo [*] Launching automated installer to configure Python 3.10...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_environment.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [-] Setup failed.
    pause
    exit /b 1
)

:: Re-check after installer completes
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    goto :VERIFY_RUNTIME
)

if exist "C:\Program Files\Python310\python.exe" (
    set "PY_CMD=C:\Program Files\Python310\python.exe"
    goto :VERIFY_RUNTIME
)

set "PY_CMD=python"

:VERIFY_RUNTIME
"%PY_CMD%" -c "import PySide6, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required UI and networking components: PySide6, websockets...
    "%PY_CMD%" -m pip install -r requirements.txt
)

echo [+] Starting ClashBot AI Engine...
"%PY_CMD%" run.py
pause
