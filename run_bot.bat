@echo off
title ClashBot AI - Client Dashboard
echo ==========================================================
echo   ClashBot AI - Client Dashboard
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

set "PY_CMD=python"
where %PY_CMD% >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
        set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    ) else if exist "C:\Program Files\Python310\python.exe" (
        set "PY_CMD=C:\Program Files\Python310\python.exe"
    ) else (
        set "PY_CMD=py"
    )
)

%PY_CMD% run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [-] ClashBot AI exited with code %ERRORLEVEL%.
    pause
)
