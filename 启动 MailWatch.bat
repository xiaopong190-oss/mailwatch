@echo off
setlocal EnableExtensions
title MailWatch
cd /d "%~dp0"

echo.
echo  MailWatch - Amazon Email Analyzer
echo  =================================
echo.

set "PYEXE="
set "PYARG="

if exist "%~dp0runtime\python.exe" (
    set "PYEXE=%~dp0runtime\python.exe"
    set "PYARG="
    goto found
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYARG=-3"
    goto found
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    set "PYARG="
    goto found
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto found
)

echo ERROR: Python not found.
echo.
echo Option 1: Install Python from https://www.python.org/downloads/
echo           Check "Add python.exe to PATH" during install.
echo Option 2: Ask sender for the "portable" version with runtime folder.
echo.
pause
exit /b 1

:found
echo Using: %PYEXE% %PYARG%
"%PYEXE%" %PYARG% --version
if errorlevel 1 goto failed

if not exist "%~dp0.installed" (
    echo.
    echo First run - installing dependencies, please wait...
    "%PYEXE%" %PYARG% -m pip install -r "%~dp0requirements.txt" -q
    if errorlevel 1 (
        echo pip install failed. Retrying with log...
        "%PYEXE%" %PYARG% -m pip install -r "%~dp0requirements.txt"
        if errorlevel 1 goto failed
    )
    echo. > "%~dp0.installed"
    echo Dependencies OK.
    echo.
)

echo Checking port 8000...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo.
    echo MailWatch is ALREADY running on port 8000.
    echo Opening browser...
    start http://127.0.0.1:8000
    echo.
    echo Tip: close the OLD black window to stop the app.
    echo      Do not start a second copy.
    pause
    exit /b 0
)

echo Starting MailWatch...
echo Browser will open automatically.
echo Keep this window open. Close it to stop the app.
echo.

"%PYEXE%" %PYARG% "%~dp0main.py"
if errorlevel 1 goto failed
pause
exit /b 0

:failed
echo.
echo START FAILED - see errors above
pause
exit /b 1
