$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bat = Join-Path $Root "daily_auto.bat"
$TaskName = "MailWatch-Daily"
$LogDir = Join-Path $Root "reports"

if (-not (Test-Path $Bat)) {
    Write-Host "ERROR: daily_auto.bat not found" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Bat`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host ""
Write-Host "OK: Scheduled task registered [$TaskName]" -ForegroundColor Green
Write-Host "    Runs daily at 08:30 - analyze emails and push DingTalk" -ForegroundColor Green
Write-Host "    Log: reports\scheduler.log" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Test now: double-click daily report bat or run daily_auto.bat" -ForegroundColor Yellow
Write-Host "View task: Win+R -> taskschd.msc" -ForegroundColor DarkGray
Write-Host ""
