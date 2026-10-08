@echo off
title ClashBot AI - Autonomous Game Intelligence Suite
echo ==========================================================
echo   ClashBot AI - Autonomous Game Intelligence Suite
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

set "PY_CMD="

if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    goto :RUN_BOT
)

if exist "C:\Program Files\Python310\python.exe" (
    set "PY_CMD=C:\Program Files\Python310\python.exe"
    goto :RUN_BOT
)

:: Python 3.10 is not yet installed on this PC
echo [!] ClashBot AI requires Python 3.10 (64-bit) for binary UI compatibility.
echo [*] Launching automated installer to configure Python 3.10...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_environment.ps1"

if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    goto :RUN_BOT
)

if exist "C:\Program Files\Python310\python.exe" (
    set "PY_CMD=C:\Program Files\Python310\python.exe"
    goto :RUN_BOT
)

echo [-] ERROR: Python 3.10 was not installed.
pause
exit /b 1

:RUN_BOT
"%PY_CMD%" -c "import PySide6, websockets, cv2, numpy, PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required components: PySide6, opencv-python, numpy, pillow...
    "%PY_CMD%" -m pip install -r requirements.txt
)

"%PY_CMD%" run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [-] ClashBot AI exited with code %ERRORLEVEL%.
    pause
)
