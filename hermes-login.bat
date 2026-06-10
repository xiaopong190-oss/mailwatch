@echo off
setlocal EnableExtensions
title Hermes Login
cd /d "%~dp0"

echo.
echo MailWatch - Hermes Portal Login
echo ===============================
echo.
echo Browser will open for Nous Portal login.
echo.

call "%~dp0hermes-launcher.cmd" portal
if errorlevel 1 goto failed

echo.
echo OK - login done.
echo Next: double-click hermes-proxy.bat
goto done

:failed
echo.
echo FAILED. Run install-hermes.bat first.

:done
echo.
pause
endlocal
