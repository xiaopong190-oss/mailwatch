# Install Git for Windows
# Usage: powershell -ExecutionPolicy Bypass -File install-git.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=== 安装 Git for Windows ===" -ForegroundColor Cyan
Write-Host ""

if (Get-Command git -ErrorAction SilentlyContinue) {
    $ver = git --version
    Write-Host "已安装: $ver" -ForegroundColor Green
    Write-Host "无需重复安装。"
    exit 0
}

if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "正在通过 winget 安装 Git.Git ..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "安装完成。请关闭并重新打开 PowerShell / 终端，然后运行: git --version" -ForegroundColor Green
        exit 0
    }
    Write-Host "winget 安装未成功，退出码: $LASTEXITCODE" -ForegroundColor Red
} else {
    Write-Host "未找到 winget。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "请手动下载安装：" -ForegroundColor Yellow
Write-Host "  https://git-scm.com/download/win" -ForegroundColor White
Write-Host ""
Write-Host "安装时保持默认选项即可；装完后重新打开终端，运行 git --version 验证。" -ForegroundColor DarkGray

# Try opening download page
try {
    Start-Process "https://git-scm.com/download/win"
} catch {}
