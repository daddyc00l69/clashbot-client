@echo off
setlocal EnableDelayedExpansion
title ClashBot AI - Autonomous Game Intelligence Suite
echo ==========================================================
echo   ClashBot AI - Autonomous Game Intelligence Suite
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
cd /d "%~dp0"

set "PY_BIN="

:: 1. Check if python is working in PATH
python -c "import sys" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PY_BIN=python"
    goto :RUN_APP
)

:: 2. Check py launcher
py -3 -c "import sys" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PY_BIN=py -3"
    goto :RUN_APP
)

:: 3. Check LocalAppData Python installations
for %%V in (Python313 Python312 Python311 Python310 Python39) do (
    if exist "%LocalAppData%\Programs\Python\%%V\python.exe" (
        "%LocalAppData%\Programs\Python\%%V\python.exe" -c "import sys" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PY_BIN=%LocalAppData%\Programs\Python\%%V\python.exe"
            set "PATH=%LocalAppData%\Programs\Python\%%V;%LocalAppData%\Programs\Python\%%V\Scripts;!PATH!"
            goto :RUN_APP
        )
    )
)

:: 4. Check Program Files Python installations
for %%V in (Python313 Python312 Python311 Python310 Python39) do (
    if exist "C:\Program Files\Python%%V\python.exe" (
        "C:\Program Files\Python%%V\python.exe" -c "import sys" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PY_BIN=C:\Program Files\Python%%V\python.exe"
            set "PATH=C:\Program Files\Python%%V;C:\Program Files\Python%%V\Scripts;!PATH!"
            goto :RUN_APP
        )
    )
)

:: 5. If Python is not working, automatically launch the installer
echo [!] Python is not installed or configured on this computer.
echo [*] Launching automated installer...
echo.
call install.bat
exit /b %ERRORLEVEL%

:RUN_APP
:: Ensure required dependencies are present
!PY_BIN! -c "import PySide6, websockets" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [*] Installing required UI and networking components: PySide6, websockets...
    if exist requirements.txt (
        !PY_BIN! -m pip install -r requirements.txt
    ) else (
        !PY_BIN! -m pip install PySide6 websockets requests psutil cryptography
    )
)

!PY_BIN! run.py
pause
