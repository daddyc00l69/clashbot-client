@echo off
cd /d "%~dp0"
title ClashBot Client - Force Update
echo ========================================================
echo         CLASHBOT CLIENT - FORCE UPDATE
echo ========================================================
echo.
if exist "client_config.json" (
    echo [*] Backing up your license and server configuration...
    copy /y "client_config.json" "client_config.json.bak" >nul
)
echo [*] Fetching latest files from GitHub...
git fetch origin main
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to connect to GitHub. Please check your internet connection.
    pause
    exit /b 1
)

echo [*] Forcing local files to match latest official build...
git reset --hard origin/main

if exist "client_config.json.bak" (
    echo [*] Restoring your license key and server connection...
    copy /y "client_config.json.bak" "client_config.json" >nul
    del "client_config.json.bak" >nul
)

echo.
echo ========================================================
echo   [OK] Client updated successfully to latest cloud build!
echo ========================================================
echo.
pause
