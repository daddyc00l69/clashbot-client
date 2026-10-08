@echo off
title ClashBot AI - Automated Installer
cd /d "%~dp0"

echo ==========================================================
echo   ClashBot AI - Automated Environment Installer
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_environment.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [-] Installation encountered an error.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] Launching ClashBot AI...
call run_bot.bat
