@echo off
title ClashBot AI - Client Setup
cd /d "%~dp0"

echo ==========================================================
echo   ClashBot AI - Client Setup
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
echo.

python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    py -m pip install -r requirements.txt
)

echo.
echo [*] Launching ClashBot AI Client...
call run_bot.bat
