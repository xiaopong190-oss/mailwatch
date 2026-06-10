@echo off
setlocal EnableExtensions
title Install Hermes
cd /d "%~dp0"

echo.
echo MailWatch - Install Hermes
echo ==========================
echo.

set "PY="
if exist "%LOCALAPPDATA%\hermes\.venv\Scripts\python.exe" set "PY=%LOCALAPPDATA%\hermes\.venv\Scripts\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not defined PY where py >nul 2>&1 && set "PY=py" && set "PYARG=-3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY goto no_python

echo Using Python: %PY% %PYARG%
echo.

call "%~dp0hermes-launcher.cmd" --version >nul 2>&1
if not errorlevel 1 goto already

if exist "%LOCALAPPDATA%\hermes\hermes-agent\hermes_cli\main.py" (
  echo Found hermes-agent source, trying pip install in place ...
  pushd "%LOCALAPPDATA%\hermes\hermes-agent"
  "%PY%" %PYARG% -m pip install -e .
  popd
  call "%~dp0hermes-launcher.cmd" --version >nul 2>&1
  if not errorlevel 1 goto ok
)

echo Installing hermes-agent from PyPI ...
"%PY%" %PYARG% -m pip install hermes-agent
if errorlevel 1 goto fail

call "%~dp0hermes-launcher.cmd" --version >nul 2>&1
if errorlevel 1 goto fail
goto ok

:already
echo Hermes already works.
call "%~dp0hermes-launcher.cmd" --version
goto done

:no_python
echo ERROR: Python not found.
goto done

:fail
echo.
echo ERROR: Install failed.
echo Try PowerShell install manually:
echo   iex (irm https://hermes-agent.nousresearch.com/install.ps1)
goto done

:ok
echo.
echo OK - Hermes installed.
call "%~dp0hermes-launcher.cmd" --version
echo.
echo Next: double-click hermes-login.bat

:done
echo.
pause
endlocal
