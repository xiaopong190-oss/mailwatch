@echo off
setlocal EnableExtensions
if /i not "%~1"=="run" (
    start "MailWatch Install" cmd /k call "%~f0" run
    exit /b 0
)

cd /d "%~dp0"
set "LOG=%~dp0install.log"

echo === MailWatch Install ===
echo Folder: %~dp0
echo Log: %LOG%
echo.

set "PYEXE="
set "PYARG="

where py >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py"
    set "PYARG=-3"
    goto do_install
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    set "PYARG="
    goto do_install
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    set "PYARG="
    goto do_install
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    set "PYARG="
    goto do_install
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PYARG="
    goto do_install
)

echo ERROR: Python not found in PATH.
echo.
echo Fix options:
echo   1. Reinstall Python and check "Add python.exe to PATH"
echo   2. Or double-click setup.ps1 instead
echo.
goto failed

:do_install
echo Python: %PYEXE% %PYARG%
"%PYEXE%" %PYARG% --version
if errorlevel 1 goto failed

if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example
)

echo.
echo Installing packages...
"%PYEXE%" %PYARG% -m pip install -r requirements.txt > "%LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo pip install FAILED. See log:
    type "%LOG%"
    goto failed
)

echo.
echo === INSTALL OK ===
echo Next:
echo   1. Edit .env - set OPENAI_API_KEY=sk-your-key
echo   2. Double-click start.bat
echo.
goto ok

:failed
echo.
echo === INSTALL FAILED - window stays open ===
pause
exit /b 1

:ok
pause
exit /b 0
