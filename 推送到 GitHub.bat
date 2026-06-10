@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 正在推送到 GitHub ...
echo 未安装 gh 时会提示输入 GitHub 用户名，并先在网页创建空仓库
echo.
set /p GHUSER=请输入 GitHub 用户名（直接回车则运行时再输入）: 
if "%GHUSER%"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push-github.ps1" -RepoName mailwatch
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push-github.ps1" -RepoName mailwatch -GitHubUser %GHUSER%
)
echo.
pause
