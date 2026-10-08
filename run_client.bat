@echo off
title ClashBot AI - Client Bridge
cd /d "%~dp0"

if exist "ClashBotClient.exe" (
    start "" "ClashBotClient.exe"
    exit /b
)

if exist "client_worker.exe" (
    start "" "client_worker.exe"
    exit /b
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    start "" py client_gui.py
    exit /b
)

python client_gui.py
