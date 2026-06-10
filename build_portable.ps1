# Build portable MailWatch with embedded Python (run once before sharing)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Runtime = Join-Path $Root "runtime"
$PyZip = Join-Path $env:TEMP "python-3.12.8-embed-amd64.zip"
$PyUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"

Write-Host "=== Build Portable MailWatch ===" -ForegroundColor Cyan

if (-not (Test-Path $Runtime)) { New-Item -ItemType Directory -Path $Runtime | Out-Null }

if (-not (Test-Path (Join-Path $Runtime "python.exe"))) {
    Write-Host "Downloading Python embeddable..."
    Invoke-WebRequest -Uri $PyUrl -OutFile $PyZip
    Expand-Archive -Path $PyZip -DestinationPath $Runtime -Force
    Remove-Item $PyZip -Force

    $pth = Get-ChildItem $Runtime -Filter "python*._pth" | Select-Object -First 1
    if ($pth) {
        $content = Get-Content $pth.FullName
        $content = $content -replace "#import site", "import site"
        $content += "`nLib\site-packages"
        Set-Content $pth.FullName $content
    }

    New-Item -ItemType Directory -Path (Join-Path $Runtime "Lib\site-packages") -Force | Out-Null

    $getPip = Join-Path $env:TEMP "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
    & (Join-Path $Runtime "python.exe") $getPip --no-warn-script-location
    Remove-Item $getPip -Force
}

Write-Host "Installing packages into runtime..."
& (Join-Path $Runtime "python.exe") -m pip install -r (Join-Path $Root "requirements.txt") --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

"" | Out-File (Join-Path $Root ".installed") -Encoding ascii

Write-Host ""
Write-Host "DONE. Portable build ready." -ForegroundColor Green
Write-Host "Zip folder and send: $Root"
Write-Host "User only needs to double-click: 启动 MailWatch.bat"
Read-Host "Press Enter to close"
