# Install Windows Task Scheduler entries for the podcast pipeline.
#
# Run this ONCE as the user account (not elevated) after the project is set up.
# Re-running it overwrites the existing tasks (the /F flag).
#
#   powershell -ExecutionPolicy Bypass -File scripts/install_scheduled_tasks.ps1
#
# Notes:
# - Tasks run as the current user so the Claude CLI sees its credentials.
# - Edit the START_HOUR / WEEKLY_DAY values below to taste.
# - Remove tasks with: schtasks /Delete /TN "Podcast - World News" /F

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found at $Python. Create it with: python -m venv .venv"
    exit 1
}

$DailyTime = "06:00"
$WeeklyDay = "MON"
$WeeklyTime = "06:30"

$DailyCmd = "`"$Python`" -m podcastgen run world_news"
$WeeklyCmd = "`"$Python`" -m podcastgen run ai"

Write-Host "Creating 'Podcast - World News' (DAILY at $DailyTime)..."
schtasks /Create /TN "Podcast - World News" `
    /TR $DailyCmd `
    /SC DAILY `
    /ST $DailyTime `
    /RL HIGHEST `
    /F

Write-Host "Creating 'Podcast - AI Weekly' (WEEKLY $WeeklyDay at $WeeklyTime)..."
schtasks /Create /TN "Podcast - AI Weekly" `
    /TR $WeeklyCmd `
    /SC WEEKLY `
    /D $WeeklyDay `
    /ST $WeeklyTime `
    /RL HIGHEST `
    /F

Write-Host ""
Write-Host "Done. Verify with:  schtasks /Query /TN ""Podcast - World News"""
Write-Host "Trigger manually:    schtasks /Run /TN ""Podcast - World News"""
