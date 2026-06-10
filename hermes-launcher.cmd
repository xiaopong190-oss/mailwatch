@echo off
setlocal EnableExtensions
set "ARGS=%*"

if exist "%LOCALAPPDATA%\hermes\bin\hermes.cmd" (
  "%LOCALAPPDATA%\hermes\bin\hermes.cmd" %ARGS%
  exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\hermes\.venv\Scripts\hermes.exe" (
  "%LOCALAPPDATA%\hermes\.venv\Scripts\hermes.exe" %ARGS%
  exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\hermes\.venv\Scripts\python.exe" (
  "%LOCALAPPDATA%\hermes\.venv\Scripts\python.exe" -m hermes_cli.main %ARGS%
  exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\Scripts\hermes.exe" (
  "%LOCALAPPDATA%\Python\pythoncore-3.14-64\Scripts\hermes.exe" %ARGS%
  exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
  "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" -m hermes_cli.main %ARGS%
  exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\hermes\hermes-agent\hermes" (
  if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    pushd "%LOCALAPPDATA%\hermes\hermes-agent"
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" hermes %ARGS%
    set "RC=%ERRORLEVEL%"
    popd
    exit /b %RC%
  )
)

where hermes >nul 2>&1
if not errorlevel 1 (
  hermes %ARGS%
  exit /b %ERRORLEVEL%
)

echo ERROR: hermes not found.
echo Run install-hermes.bat first.
exit /b 1
