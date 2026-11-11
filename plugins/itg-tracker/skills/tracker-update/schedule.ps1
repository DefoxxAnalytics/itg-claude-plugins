# Optional, per person. Registers the Windows task "Claude tracker update": weekdays at 17:30 (or -At), only while
# you are logged on, and at your next logon when a run was missed. It copies scheduled.ps1 into your settings
# folder (~\.claude\tracker-update) and runs it from there, so plugin updates don't break the task.
# -Remove deletes the task.
param([switch]$Remove, [string]$At = '17:30')

$ErrorActionPreference = 'Stop'
$name = 'Claude tracker update'
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    "Removed the task '$name'."
    return
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$settings = Join-Path $env:USERPROFILE '.claude\tracker-update'
New-Item -ItemType Directory -Force -Path $settings | Out-Null
$launcher = Join-Path $settings 'scheduled.ps1'
Copy-Item -Path (Join-Path $here 'scheduled.ps1') -Destination $launcher -Force

$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwsh) { $pwsh = (Get-Command powershell).Source }
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arguments -WorkingDirectory $settings
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $At
$options = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $options -Principal $principal -Force `
    -Description 'Opens Claude on the tracker-update skill when a work project has something to post to the ITG progress tracker.' | Out-Null
"Registered '$name': weekdays at $At, running $launcher."
