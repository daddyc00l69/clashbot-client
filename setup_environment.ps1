# ClashBot AI - Automated Environment Setup
# Author: Aradhye Tushar (https://github.com/AradhyeTushar)
[CmdletBinding()]
param(
    [switch]$LaunchAfterInstall
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ClashBot AI - Automated Environment Installer" -ForegroundColor Cyan
Write-Host "  Author: Aradhye Tushar (https://github.com/AradhyeTushar)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Test-PythonExecutable($exePath) {
    if (-not $exePath) { return $false }
    try {
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = $exePath
        $pinfo.Arguments = '-c "import sys; sys.exit(42)"'
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($pinfo)
        $p.WaitForExit(5000)
        return ($p.ExitCode -eq 42)
    } catch {
        return $false
    }
}

function Find-Python() {
    # 1. Test 'python' in PATH
    if (Test-PythonExecutable "python") {
        try {
            $cmd = (Get-Command python -ErrorAction SilentlyContinue).Source
            if ($cmd -and ($cmd -notmatch "WindowsApps")) {
                return $cmd
            }
        } catch {}
    }

    # 2. Test 'py' launcher
    if (Test-PythonExecutable "py") {
        return "py"
    }

    # 3. Check known directories
    $commonPaths = @(
        "$env:LocalAppData\Programs\Python\Python313\python.exe",
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:LocalAppData\Programs\Python\Python310\python.exe",
        "$env:LocalAppData\Programs\Python\Python39\python.exe",
        "C:\Program Files\Python313\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python310\python.exe",
        "C:\Program Files\Python39\python.exe"
    )

    foreach ($path in $commonPaths) {
        if ((Test-Path $path) -and (Test-PythonExecutable $path)) {
            return $path
        }
    }

    return $null
}

$pyBin = Find-Python

if (-not $pyBin) {
    Write-Host "[!] Working Python 3.10+ not detected on this system." -ForegroundColor Yellow
    Write-Host "[*] Downloading official Python 3.11 (64-bit) from python.org..." -ForegroundColor Green
    
    $installerPath = "$env:TEMP\python-3.11.9-amd64.exe"
    $downloadUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($downloadUrl, $installerPath)
        Write-Host "[+] Download complete." -ForegroundColor Green
    } catch {
        Write-Host "[-] Download failed via WebClient, trying curl..." -ForegroundColor Yellow
        & curl.exe -sSL -o $installerPath $downloadUrl
    }

    if (-not (Test-Path $installerPath)) {
        Write-Host "[-] ERROR: Failed to download Python installer." -ForegroundColor Red
        Write-Host "[*] Please manually install Python 3.11 from https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "[*] (Make sure to check 'Add Python to PATH' during installation!)" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "[*] Installing Python 3.11 (this takes ~30-60 seconds)..." -ForegroundColor Cyan
    $installProcess = Start-Process -FilePath $installerPath -ArgumentList "/passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 SimpleInstall=1" -Wait -PassThru
    
    if (Test-Path $installerPath) {
        Remove-Item -Force $installerPath -ErrorAction SilentlyContinue
    }

    # Refresh current process PATH environment variable
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $env:Path = "$userPath;$machinePath"

    $pyBin = Find-Python
    if (-not $pyBin) {
        $expected = "$env:LocalAppData\Programs\Python\Python311\python.exe"
        if (Test-Path $expected) {
            $pyBin = $expected
        }
    }
}

if (-not $pyBin) {
    Write-Host "[-] ERROR: Could not locate a working Python executable." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[+] Using Python interpreter: $pyBin" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Installing required UI and networking components..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$reqFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $reqFile) {
    & $pyBin -m pip install --upgrade pip
    & $pyBin -m pip install -r $reqFile
} else {
    & $pyBin -m pip install PySide6 websockets requests psutil cryptography
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Warning: Failed to install one or more dependencies." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[+] Installation complete! All components are ready." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

if ($LaunchAfterInstall) {
    Write-Host "[*] Starting ClashBot AI..." -ForegroundColor Cyan
    & $pyBin (Join-Path $ScriptDir "run.py")
}
