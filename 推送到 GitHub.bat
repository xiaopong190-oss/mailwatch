@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 正在推送到 GitHub ...
echo 首次运行会提示登录 GitHub（需已安装 Git 和 gh）
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push-github.ps1" -RepoName mailwatch
echo.
pause
