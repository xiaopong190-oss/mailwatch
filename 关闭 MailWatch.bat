@echo off
chcp 65001 >nul
title Stop MailWatch
cd /d "%~dp0"

echo Stopping MailWatch on port 8000...
set FOUND=0

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set FOUND=1
    echo Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

if %FOUND%==0 (
    echo No process found on port 8000.
) else (
    echo Done. You can start MailWatch again.
)
pause
