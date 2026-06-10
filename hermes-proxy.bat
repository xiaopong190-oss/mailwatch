@echo off
setlocal EnableExtensions
title Hermes Proxy
cd /d "%~dp0"

echo.
echo MailWatch - Hermes Proxy
echo ========================
echo.
echo Keep this window OPEN while using MailWatch.
echo.

call "%~dp0hermes-launcher.cmd" proxy start
if errorlevel 1 goto failed
goto done

:failed
echo.
echo FAILED. Run hermes-login.bat if not logged in.

:done
echo.
pause
endlocal
