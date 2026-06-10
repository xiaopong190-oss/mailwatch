# 注册 Windows 计划任务：每天 8:30 跑每日报告
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Bat = Join-Path $Root "每日报告-自动.bat"
$TaskName = "MailWatch每日报告"
$LogDir = Join-Path $Root "reports"

if (-not (Test-Path $Bat)) { throw "找不到 每日报告-自动.bat" }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Bat`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "OK: 已注册计划任务 [$TaskName]" -ForegroundColor Green
Write-Host "  每天 08:30 自动运行（分析 3 个邮箱 + 推钉钉）" -ForegroundColor Green
Write-Host "  日志: reports\scheduler.log" -ForegroundColor DarkGray
Write-Host ""
Write-Host "手动测试: 双击 每日报告.bat" -ForegroundColor Yellow
Write-Host "查看任务: Win+R 输入 taskschd.msc" -ForegroundColor DarkGray

if ($Host.Name -eq "ConsoleHost") {
    Read-Host "按回车关闭"
}
