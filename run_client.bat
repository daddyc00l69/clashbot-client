@echo off
title ClashBot AI - Client Worker
echo ========================================================
echo   CLASHBOT AI - CLIENT WORKER
echo ========================================================
echo.
echo Make sure your Android emulator (BlueStacks / LDPlayer / MuMu)
echo is RUNNING and has Android Debug Bridge (ADB) enabled!
echo.
set /p SERVER_IP="Enter Server IP (Press Enter for default 192.168.0.9): "
if "%SERVER_IP%"=="" set SERVER_IP=192.168.0.9

echo.
echo Connecting to server at %SERVER_IP%:9999...
echo.
python client_worker.py --server %SERVER_IP% --port 9999 --token clashbot-secret-key-2026
pause
