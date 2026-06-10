@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYEXE="
if exist "%~dp0runtime\python.exe" (set "PYEXE=%~dp0runtime\python.exe" & goto run)
where py >nul 2>&1 && (set "PYEXE=py" & set "PYARG=-3" & goto run)
where python >nul 2>&1 && (set "PYEXE=python" & set "PYARG=" & goto run)
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" & goto run
)
echo [%date% %time%] Python not found >> "%~dp0reports\scheduler.log"
exit /b 1

:run
if not exist "%~dp0reports" mkdir "%~dp0reports"
"%PYEXE%" %PYARG% "%~dp0daily_run.py" >> "%~dp0reports\scheduler.log" 2>&1
exit /b %ERRORLEVEL%
