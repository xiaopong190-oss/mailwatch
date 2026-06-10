# MailWatch server - PowerShell (UTF-8 safe)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== MailWatch Start ===" -ForegroundColor Cyan

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) { return @{ Exe = "py"; Args = @("-3") } }
    if (Get-Command python -ErrorAction SilentlyContinue) { return @{ Exe = "python"; Args = @() } }
    $paths = @(
        "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return @{ Exe = $p; Args = @() } }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "ERROR: Python not found. Run setup.ps1 first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env not found. Run setup.ps1 first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "OPENAI_API_KEY=sk-") {
    Write-Host "ERROR: Set OPENAI_API_KEY=sk-... in .env" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Open browser: http://localhost:8000"
Write-Host "Press Ctrl+C to stop`n"

Start-Process "http://localhost:8000"

& $py.Exe @($py.Args + @("main.py"))

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nServer exited with code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
