# MailWatch - push to GitHub
# Usage: powershell -ExecutionPolicy Bypass -File push-github.ps1
# Optional: powershell -ExecutionPolicy Bypass -File push-github.ps1 -RepoName mailwatch -Private

param(
    [string]$RepoName = "mailwatch",
    [switch]$Private
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 git，请先安装 Git for Windows"
}

if (-not (Test-Path .git)) {
    git init
    git branch -M main
}

if (-not (Test-Path .gitignore)) {
    Write-Error "缺少 .gitignore"
}

git add -A
$status = git status --porcelain
if ($status) {
    git commit -m @"
Initial MailWatch release.

Amazon seller email analysis with IMAP, DeepSeek/OpenAI, web UI, and daily reports.
"@
} else {
    Write-Host "没有新的变更需要提交"
}

$remoteUrl = git remote get-url origin 2>$null
if (-not $remoteUrl) {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Error "未配置 GitHub 远程仓库，且未安装 GitHub CLI (gh)。请先运行: gh auth login"
    }
    gh auth status
    $visibility = if ($Private) { "--private" } else { "--public" }
    gh repo create $RepoName $visibility --source=. --remote=origin --push
    Write-Host "已创建并推送到 GitHub: $RepoName"
    gh repo view --web
    exit 0
}

git push -u origin main
Write-Host "已推送到 GitHub"
gh repo view --web 2>$null
