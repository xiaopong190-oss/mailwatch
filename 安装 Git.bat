@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 正在安装 Git for Windows ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-git.ps1"
echo.
pause
