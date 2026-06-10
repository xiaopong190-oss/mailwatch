@echo off
setlocal EnableExtensions
title MailWatch Daily
cd /d "%~dp0"

set "PYEXE="
if exist "%~dp0runtime\python.exe" (set "PYEXE=%~dp0runtime\python.exe" & goto run)
where py >nul 2>&1 && (set "PYEXE=py" & set "PYARG=-3" & goto run)
where python >nul 2>&1 && (set "PYEXE=python" & set "PYARG=" & goto run)
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" & goto run
)
echo Python not found
pause
exit /b 1

:run
echo MailWatch daily report...
"%PYEXE%" %PYARG% "%~dp0daily_run.py"
if errorlevel 1 (
    echo FAILED
    pause
    exit /b 1
)
echo DONE
pause
