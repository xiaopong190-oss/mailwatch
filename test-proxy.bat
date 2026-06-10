@echo off
title Test Hermes Proxy
echo.
echo Testing http://127.0.0.1:8645/v1 ...
echo.

powershell -NoProfile -Command "$ErrorActionPreference='Stop'; try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8645/v1/models' -TimeoutSec 5 -UseBasicParsing; Write-Host 'OK - Proxy is running. HTTP' $r.StatusCode; Write-Host $r.Content.Substring(0, [Math]::Min(200, $r.Content.Length)) } catch { Write-Host 'FAIL - Proxy NOT reachable on port 8645'; Write-Host $_.Exception.Message }"

echo.
netstat -an | findstr ":8645"
echo.
echo If FAIL: run hermes-proxy.bat and keep window open.
echo If OK but MailWatch still 502: run hermes-login.bat first.
echo.
pause
