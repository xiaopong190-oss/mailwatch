@echo off
cd /d "%~dp0"
echo.
echo Installing MailWatch daily task at 08:30 ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-schedule.ps1"
echo.
pause
