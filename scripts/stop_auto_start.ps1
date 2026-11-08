# ==============================================================================
# STOCK UNDO! - Stop & Remove Windows Auto-Start Task
# ==============================================================================

param (
    [string]$TaskName = "StockUndoBackendServer"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Stopping and Removing Auto-Start Service: $TaskName" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Remove from Windows Startup folder
$startupFolder = [Environment]::GetFolderPath("Startup")
$startupFile = Join-Path $startupFolder "StockUndoBackend.vbs"
if (Test-Path $startupFile) {
    Remove-Item $startupFile -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Removed launcher from Windows Startup folder." -ForegroundColor Green
}

# 2. Stop and unregister scheduled task if present
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "[OK] Scheduled Task '$TaskName' removed." -ForegroundColor Green

# 3. Kill any running uvicorn process for Stock Undoo
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*Stock Undoo*uvicorn*" } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Stopped background process PID $($_.ProcessId)" -ForegroundColor Green
}

Write-Host "`nAuto-start has been successfully disabled." -ForegroundColor Green
