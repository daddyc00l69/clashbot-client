@echo off
setlocal EnableDelayedExpansion
title ClashBot AI - Automated Installer
echo ==========================================================
echo   ClashBot AI - Automated Environment Installer
echo   Author: Aradhye Tushar (https://github.com/AradhyeTushar)
echo ==========================================================
echo.
cd /d "%~dp0"

set "PY_BIN="

:: Step 1: Detect if working Python is already in PATH
python -c "import sys" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PY_BIN=%%i"
    echo [+] Detected working Python: !PY_BIN!
    goto :PYTHON_READY
)

:: Step 2: Detect py launcher
py -3 -c "import sys" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PY_BIN=py -3"
    echo [+] Detected Python launcher (py -3)
    goto :PYTHON_READY
)

:: Step 3: Check common user local installation paths
for %%V in (Python313 Python312 Python311 Python310 Python39) do (
    if exist "%LocalAppData%\Programs\Python\%%V\python.exe" (
        "%LocalAppData%\Programs\Python\%%V\python.exe" -c "import sys" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PY_BIN=%LocalAppData%\Programs\Python\%%V\python.exe"
            set "PATH=%LocalAppData%\Programs\Python\%%V;%LocalAppData%\Programs\Python\%%V\Scripts;!PATH!"
            echo [+] Detected Python in LocalAppData: !PY_BIN!
            goto :PYTHON_READY
        )
    )
)

:: Step 4: Check Program Files installation paths
for %%V in (Python313 Python312 Python311 Python310 Python39) do (
    if exist "C:\Program Files\Python%%V\python.exe" (
        "C:\Program Files\Python%%V\python.exe" -c "import sys" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PY_BIN=C:\Program Files\Python%%V\python.exe"
            set "PATH=C:\Program Files\Python%%V;C:\Program Files\Python%%V\Scripts;!PATH!"
            echo [+] Detected Python in Program Files: !PY_BIN!
            goto :PYTHON_READY
        )
    )
)

:: Step 5: Python not found - Download and Install Python 3.11 automatically
echo [!] Python is not installed on this system.
echo [*] Downloading official Python 3.11 for Windows (64-bit)...
set "INSTALLER=%TEMP%\python_3.11_installer.exe"
if exist "!INSTALLER!" del /f /q "!INSTALLER!" >nul 2>&1

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $wc = New-Object System.Net.WebClient; $wc.DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%INSTALLER%')" >nul 2>&1
if not exist "!INSTALLER!" (
    curl -sSL -o "!INSTALLER!" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
)

if not exist "!INSTALLER!" (
    echo [-] Failed to download Python automatically.
    echo [*] Please manually download and install Python 3.11 from:
    echo     https://www.python.org/downloads/
    echo [*] IMPORTANT: Make sure to check 'Add Python to PATH' during installation!
    pause
    exit /b 1
)

echo [*] Installing Python 3.11 with PATH configured (this takes ~30 seconds)...
start /wait "" "!INSTALLER!" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 SimpleInstall=1
del /f /q "!INSTALLER!" >nul 2>&1

:: Refresh paths
set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;!PATH!"
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_BIN=%LocalAppData%\Programs\Python\Python311\python.exe"
) else (
    set "PY_BIN=python"
)

:PYTHON_READY
echo.
echo ==========================================================
echo [*] Installing required UI and networking components...
echo ==========================================================
"!PY_BIN!" -m pip install --upgrade pip
if exist requirements.txt (
    "!PY_BIN!" -m pip install -r requirements.txt
) else (
    "!PY_BIN!" -m pip install PySide6 websockets requests psutil cryptography
)

if !ERRORLEVEL! NEQ 0 (
    echo [-] Warning: One or more packages failed to install.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo [+] Installation complete! Everything is ready.
echo ==========================================================
echo.
set /p START_NOW="Do you want to launch ClashBot AI now? (Y/N): "
if /i "!START_NOW!"=="Y" (
    "!PY_BIN!" run.py
)
pause
