# Run by the task "Claude tracker update". schedule.ps1 copies this file into the person's settings folder
# (~\.claude\tracker-update), so it keeps working when a plugin update installs the skill in a new folder.
# It finds the installed skill (the itg-tracker plugin first, else a hand copy in ~\.claude\skills), and opens a
# Claude window on it only when a work project has something not yet posted. Logs counts only.
$ErrorActionPreference = 'Stop'
$settings = Join-Path $env:USERPROFILE '.claude\tracker-update'
New-Item -ItemType Directory -Force -Path $settings | Out-Null
$log = Join-Path $settings 'scheduled.log'
function Write-Log([string]$text) { Add-Content -Path $log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $text) }

$fromPlugin = Get-ChildItem -Path (Join-Path $env:USERPROFILE '.claude\plugins\cache\*\itg-tracker\*\skills\tracker-update\tracker.py') -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$handCopy = Join-Path $env:USERPROFILE '.claude\skills\tracker-update\tracker.py'
if ($fromPlugin) { $tracker = $fromPlugin.FullName; $prompt = '/itg-tracker:tracker-update' }
elseif (Test-Path $handCopy) { $tracker = $handCopy; $prompt = '/tracker-update' }
else { Write-Log 'tracker-update skill not found'; exit 1 }

$pending = & python $tracker pending 2>$null
if ($LASTEXITCODE -ne 0) { Write-Log "tracker.py pending failed (exit $LASTEXITCODE)"; exit 1 }
$count = [int]($pending | Select-Object -Last 1)
if ($count -eq 0) { Write-Log 'nothing pending'; exit 0 }

$terminal = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
$claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
if (-not (Test-Path $claude)) { $claude = (Get-Command claude -ErrorAction SilentlyContinue).Source }
if (-not $claude) { Write-Log 'claude not found'; exit 1 }
Start-Process -FilePath $terminal -ArgumentList @('-d', $env:USERPROFILE, $claude, $prompt)
Write-Log "$count pending: opened Claude"
