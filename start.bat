@echo off
setlocal EnableExtensions
if /i not "%~1"=="run" (
    start "MailWatch Server" cmd /k call "%~f0" run
    exit /b 0
)

cd /d "%~dp0"
set "LOG=%~dp0start.log"

echo === MailWatch Start ===
echo Folder: %~dp0
echo Log: %LOG%
echo.

set "PYEXE="
set "PYARG="

where py >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYARG=-3"
    goto do_start
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    set "PYARG="
    goto do_start
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    set "PYARG="
    goto do_start
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    set "PYARG="
    goto do_start
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PYARG="
    goto do_start
)

echo ERROR: Python not found. Run install.bat first.
goto failed

:do_start
echo Python: %PYEXE% %PYARG%
"%PYEXE%" %PYARG% --version
if errorlevel 1 goto failed

if not exist ".env" (
    echo ERROR: .env not found. Run install.bat first.
    goto failed
)

findstr /C:"OPENAI_API_KEY=sk-" .env >nul
if errorlevel 1 (
    echo ERROR: Set OPENAI_API_KEY in .env file
    echo Example: OPENAI_API_KEY=sk-xxxxxxxx
    goto failed
)

echo.
echo Starting server...
echo Open browser: http://localhost:8000
echo Press Ctrl+C to stop
echo.

"%PYEXE%" %PYARG% main.py
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo.
    echo ERROR: Server exited with code %EXITCODE%
    goto failed
)

goto ok

:failed
echo.
echo === START FAILED - window stays open ===
pause
exit /b 1

:ok
pause
exit /b 0
