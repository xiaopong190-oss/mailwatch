# MailWatch - push to GitHub
# Usage:
#   powershell -ExecutionPolicy Bypass -File push-github.ps1
#   powershell -ExecutionPolicy Bypass -File push-github.ps1 -GitHubUser 你的用户名
#   powershell -ExecutionPolicy Bypass -File push-github.ps1 -RepoName mailwatch -Private

param(
    [string]$RepoName = "mailwatch",
    [string]$GitHubUser = "",
    [switch]$Private
)

Set-Location $PSScriptRoot

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host ">> $msg" -ForegroundColor Cyan
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 git，请先安装 Git for Windows: https://git-scm.com"
}

if (-not (Test-Path .git)) {
    Write-Step "初始化 Git 仓库"
    git init
    git branch -M main
}

if (-not (Test-Path .gitignore)) {
    Write-Error "缺少 .gitignore"
}

Write-Step "提交本地文件"
git add -A
$status = git status --porcelain
if ($status) {
    git commit -m @"
Initial MailWatch release.

Amazon seller email analysis with IMAP, DeepSeek/OpenAI, web UI, and daily reports.
"@
} else {
    Write-Host "没有新的变更需要提交（使用已有 commit）"
}

$hasOrigin = $false
$prevErr = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$null = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) { $hasOrigin = $true }
$ErrorActionPreference = $prevErr

if (-not $hasOrigin) {
    $hasGh = [bool](Get-Command gh -ErrorAction SilentlyContinue)

    if ($hasGh) {
        Write-Step "使用 GitHub CLI 创建远程仓库并推送"
        gh auth status
        if ($LASTEXITCODE -ne 0) {
            Write-Host "请先登录 GitHub：" -ForegroundColor Yellow
            gh auth login
        }
        $visibility = if ($Private) { "--private" } else { "--public" }
        gh repo create $RepoName $visibility --source=. --remote=origin --push
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host ""
        Write-Host "完成！仓库已创建并推送。" -ForegroundColor Green
        gh repo view --web 2>$null
        exit 0
    }

    Write-Host ""
    Write-Host "未安装 GitHub CLI (gh)，改用手动方式推送。" -ForegroundColor Yellow
    Write-Host "（可选）安装 gh 后重跑本脚本可自动建仓库： winget install GitHub.cli" -ForegroundColor DarkGray
    Write-Host ""

    if (-not $GitHubUser) {
        $GitHubUser = Read-Host "请输入你的 GitHub 用户名（例如 zhangsan）"
    }
    if (-not $GitHubUser) {
        Write-Error "需要 GitHub 用户名才能添加远程地址"
    }

    $remote = "https://github.com/$GitHubUser/$RepoName.git"
    Write-Step "添加远程 origin: $remote"
    git remote add origin $remote
    if ($LASTEXITCODE -ne 0) {
        Write-Error "添加远程失败，可能 origin 已存在。可运行: git remote -v 查看"
    }

    Write-Host ""
    Write-Host "请先在浏览器创建空仓库（不要勾选 README / .gitignore）：" -ForegroundColor Yellow
    Write-Host "  https://github.com/new?name=$RepoName" -ForegroundColor White
    Write-Host ""
    $ready = Read-Host "创建好后按回车继续推送"
    $null = $ready
}

Write-Step "推送到 GitHub (main)"
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "推送失败。常见原因：" -ForegroundColor Red
    Write-Host "  1. GitHub 上还没创建同名空仓库"
    Write-Host "  2. 未登录 GitHub（首次 push 会弹出浏览器或要求 Personal Access Token）"
    Write-Host "  3. 仓库名或用户名不对"
    Write-Host ""
    Write-Host "手动推送命令：" -ForegroundColor Yellow
    Write-Host "  git push -u origin main"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "完成！代码已推送到 GitHub。" -ForegroundColor Green
if ($GitHubUser) {
    Write-Host "  https://github.com/$GitHubUser/$RepoName" -ForegroundColor White
} else {
    git remote get-url origin
}
