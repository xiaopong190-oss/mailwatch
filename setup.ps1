# MailWatch setup - PowerShell (UTF-8 safe)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== MailWatch Install ===" -ForegroundColor Cyan
Write-Host "Folder: $PSScriptRoot"

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
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/ and check Add to PATH"
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Python: $($py.Exe) $($py.Args -join ' ')"
& $py.Exe @($py.Args + @("--version"))

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env"
}

Write-Host "`nInstalling packages..."
& $py.Exe @($py.Args + @("-m", "pip", "install", "-r", "requirements.txt"))
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip install FAILED" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "`n=== INSTALL OK ===" -ForegroundColor Green
Write-Host "1. Edit .env - set OPENAI_API_KEY=sk-..."
Write-Host "2. Run start.bat or run.ps1"
Read-Host "Press Enter to close"
