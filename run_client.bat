@echo off
title ClashBot AI - Client Worker
echo ========================================================
echo   CLASHBOT AI - CLIENT WORKER (Cloudflare Tunnel)
echo ========================================================
echo.
echo Make sure your Android emulator (BlueStacks / LDPlayer / MuMu)
echo is RUNNING and has Android Debug Bridge (ADB) enabled!
echo.
set /p SERVER_URL="Enter Server Link: "
if "%SERVER_URL%"=="" (
    echo [!] Link cannot be empty!
    pause
    exit /b
)

echo.
echo Connecting to %SERVER_URL%...
echo.

if exist "%~dp0client_worker.exe" (
    "%~dp0client_worker.exe" --server "%SERVER_URL%" --token clashbot-secret-key-2026
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        py "%~dp0client_worker.py" --server "%SERVER_URL%" --token clashbot-secret-key-2026
    ) else (
        python "%~dp0client_worker.py" --server "%SERVER_URL%" --token clashbot-secret-key-2026
    )
)

pause
