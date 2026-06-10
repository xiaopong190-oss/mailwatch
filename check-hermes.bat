@echo off
cd /d "%~dp0"
echo Checking hermes ...
echo.
call "%~dp0hermes-launcher.cmd" --version
echo exit code: %ERRORLEVEL%
echo.
pause
