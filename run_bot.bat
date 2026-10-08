@echo off
title ClashBot AI - Autonomous Game Intelligence Suite
echo ==========================================================
echo   ClashBot AI - Autonomous Game Intelligence Suite
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

:: 1. Verify working Python
python -c "import sys; sys.exit(42)" >nul 2>&1
if %ERRORLEVEL% EQU 42 (
    set "PY_CMD=python"
    goto :VERIFY_PACKAGES
)

py -3 -c "import sys; sys.exit(42)" >nul 2>&1
if %ERRORLEVEL% EQU 42 (
    set "PY_CMD=py -3"
    goto :VERIFY_PACKAGES
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    "%LocalAppData%\Programs\Python\Python311\python.exe" -c "import sys; sys.exit(42)" >nul 2>&1
    if %ERRORLEVEL% EQU 42 (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
        goto :VERIFY_PACKAGES
    )
)

if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    "%LocalAppData%\Programs\Python\Python310\python.exe" -c "import sys; sys.exit(42)" >nul 2>&1
    if %ERRORLEVEL% EQU 42 (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
        goto :VERIFY_PACKAGES
    )
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" -c "import sys; sys.exit(42)" >nul 2>&1
    if %ERRORLEVEL% EQU 42 (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
        goto :VERIFY_PACKAGES
    )
)

:: Python not installed or Microsoft Store stub detected - Run automated installer
echo [!] Python is not installed or configured on this computer.
echo [*] Launching automated installer...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_environment.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [-] Setup failed.
    pause
    exit /b 1
)

:: Re-check after installation
python -c "import sys; sys.exit(42)" >nul 2>&1
if %ERRORLEVEL% EQU 42 (
    set "PY_CMD=python"
    goto :VERIFY_PACKAGES
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto :VERIFY_PACKAGES
)
set "PY_CMD=python"

:VERIFY_PACKAGES
%PY_CMD% -c "import PySide6, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required UI and networking components: PySide6, websockets...
    %PY_CMD% -m pip install -r requirements.txt
)

echo [+] Starting ClashBot AI Engine...
%PY_CMD% run.py
pause
