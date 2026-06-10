@echo off
setlocal EnableExtensions
title Test DeepSeek API
cd /d "%~dp0"

set "PY="
set "PYARG="
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
  set "PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
  goto run
)
where py >nul 2>&1 && set "PY=py" && set "PYARG=-3" && goto run
where python >nul 2>&1 && set "PY=python" && goto run

echo Python not found
pause
exit /b 1

:run
echo Testing DeepSeek from .env ...
echo.
"%PY%" %PYARG% "%~dp0test_deepseek.py"
if errorlevel 1 (
  echo.
  echo FAILED - check key, balance, base_url in Settings
) else (
  echo.
  echo SUCCESS - DeepSeek API works
)
echo.
pause
