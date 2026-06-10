# 注册 Windows 计划任务：每天 8:30 跑每日报告
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bat = Join-Path $Root "每日报告.bat"
$TaskName = "MailWatch每日报告"

if (-not (Test-Path $Bat)) { throw "找不到 每日报告.bat" }

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Bat`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "OK: 已注册计划任务 [$TaskName] 每天 8:30 运行" -ForegroundColor Green
Write-Host "请先配置: .env  accounts.json"
Write-Host "手动测试: 双击 每日报告.bat"
Read-Host "Press Enter"
