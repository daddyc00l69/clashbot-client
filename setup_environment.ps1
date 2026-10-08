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

function Test-Python310($exePath) {
    if (-not $exePath) { return $false }
    if (-not (Test-Path $exePath)) { return $false }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exePath
        $psi.Arguments = '-c "import sys; print(sys.version_info[0], sys.version_info[1])"'
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $output = $p.StandardOutput.ReadToEnd()
        $p.WaitForExit(5000)
        if ($output -and ($output.Trim() -eq "3 10")) {
            return $true
        }
    } catch {}
    return $false
}

function Find-Python310() {
    # 1. Check LocalAppData Python 3.10 explicitly
    $localPy310 = "$env:LocalAppData\Programs\Python\Python310\python.exe"
    if (Test-Python310 $localPy310) {
        return $localPy310
    }

    # 2. Check Program Files Python 3.10 explicitly
    $progPy310 = "C:\Program Files\Python310\python.exe"
    if (Test-Python310 $progPy310) {
        return $progPy310
    }

    # (Note: We strictly do NOT check generic 'python' in PATH to avoid capturing Python 3.11/3.12)
    return $null
}

function Ensure-VCRedist() {
    $hasVC = $false
    try {
        $key = "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64"
        if (Test-Path $key) {
            $hasVC = $true
        }
    } catch {}

    if (-not $hasVC) {
        Write-Host "[*] Installing required Visual C++ 2015-2022 Runtime..." -ForegroundColor Cyan
        $vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        $vcPath = "$env:TEMP\vc_redist.x64.exe"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($vcUrl, $vcPath)
            Start-Process -FilePath $vcPath -ArgumentList "/passive /norestart" -Wait
            Remove-Item -Force $vcPath -ErrorAction SilentlyContinue
            Write-Host "[+] Visual C++ Runtime installed." -ForegroundColor Green
        } catch {
            Write-Host "[-] Notice: Visual C++ download skipped ($($_.Exception.Message))" -ForegroundColor Yellow
        }
    }
}

$pyBin = Find-Python310

if (-not $pyBin) {
    Write-Host "[!] ClashBot AI requires Python 3.10 (64-bit) for core PyArmor UI runtime compatibility." -ForegroundColor Yellow
    Write-Host "[*] Downloading official Python 3.10.11 (64-bit) from python.org..." -ForegroundColor Green
    
    $installerPath = "$env:TEMP\python-3.10.11-amd64.exe"
    $downloadUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
    $downloaded = $false

    try {
        & curl.exe -sSL -o $installerPath $downloadUrl
        if ((Test-Path $installerPath) -and ((Get-Item $installerPath).Length -gt 10000000)) {
            $downloaded = $true
            Write-Host "[+] Download complete via curl." -ForegroundColor Green
        }
    } catch {}

    if (-not $downloaded) {
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($downloadUrl, $installerPath)
            if ((Test-Path $installerPath) -and ((Get-Item $installerPath).Length -gt 10000000)) {
                $downloaded = $true
                Write-Host "[+] Download complete via WebClient." -ForegroundColor Green
            }
        } catch {}
    }

    if (-not $downloaded) {
        Write-Host "[-] ERROR: Failed to download Python 3.10 installer." -ForegroundColor Red
        Write-Host "[*] Please manually install Python 3.10 from https://www.python.org/downloads/release/python-31011/" -ForegroundColor Yellow
        Write-Host "[*] (Make sure to check 'Add Python to PATH' during installation!)" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "[*] Installing Python 3.10 (this takes ~30-60 seconds)..." -ForegroundColor Cyan
    $installProcess = Start-Process -FilePath $installerPath -ArgumentList "/passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 SimpleInstall=1" -Wait -PassThru
    
    if (Test-Path $installerPath) {
        Remove-Item -Force $installerPath -ErrorAction SilentlyContinue
    }

    # Refresh current process PATH environment variable
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $env:Path = "$userPath;$machinePath"

    $pyBin = Find-Python310
    if (-not $pyBin) {
        $expected = "$env:LocalAppData\Programs\Python\Python310\python.exe"
        if (Test-Path $expected) {
            $pyBin = $expected
        }
    }
}

if (-not $pyBin) {
    Write-Host "[-] ERROR: Could not locate Python 3.10 executable." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Ensure VC++ redistributable is present for PyArmor C-runtime
Ensure-VCRedist

Write-Host "[+] Using Python 3.10 interpreter: $pyBin" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Installing required UI and networking components..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$reqFile = Join-Path $ScriptDir "requirements.txt"
& $pyBin -m pip install --upgrade pip
if (Test-Path $reqFile) {
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
Write-Host "[*] Verifying PyArmor UI runtime compatibility..." -ForegroundColor Cyan
$verifyCode = "import sys; sys.path.insert(0, 'src'); from pyarmor_runtime_015394 import __pyarmor__; print('[+] PyArmor runtime verified successfully!')"
& $pyBin -c $verifyCode

if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] ERROR: PyArmor runtime verification failed on $pyBin." -ForegroundColor Red
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
