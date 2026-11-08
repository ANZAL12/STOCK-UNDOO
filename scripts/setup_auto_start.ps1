# ==============================================================================
# STOCK UNDO! - Windows Auto-Start on Power-On Installer
# Configures the FastAPI backend to run automatically at system boot
# ==============================================================================

param (
    [string]$Port = "8000",
    [string]$TaskName = "StockUndoBackendServer"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$VbsScript = Join-Path $ScriptDir "run_backend_silent.vbs"
$LogDir = Join-Path $BackendDir "logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " STOCK UNDO! - Auto-Start at System Boot Setup" -ForegroundColor Yellow
Write-Host " Tagline: 'Check stock before you call the godown!'" -ForegroundColor DarkYellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project Root : $ProjectRoot"
Write-Host "Backend Dir  : $BackendDir"
Write-Host "Python Path  : $VenvPython"
Write-Host "Target Port  : $Port"
Write-Host ""

# 1. Verify Python Virtual Environment
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at '$VenvPython'. Please run setup first!"
    exit 1
}

# 2. Check for Port Conflicts with Other Existing Servers
$portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    $owningPid = $portInUse.OwningProcess | Select-Object -First 1
    $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
    $procCmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue).CommandLine

    if ($procCmd -and ($procCmd -like "*Stock Undoo*")) {
        Write-Host "[*] Port $Port is currently running STOCK UNDO!. It will auto-start on boot." -ForegroundColor Green
    } elseif ($proc) {
        Write-Host "[!] Port $Port is currently in use by another server: '$($proc.ProcessName)' (PID $owningPid)!" -ForegroundColor Red
        Write-Host "    Changing STOCK UNDO! auto-start port to 8080 to prevent conflicts..." -ForegroundColor Cyan
        $Port = "8080"
    }
}

# 3. Create Silent Launcher VBScript (Runs hidden in background with 0 window popup)
$vbsContent = @"
' STOCK UNDO! Silent Windows Background Launcher
WScript.Sleep 3000
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$BackendDir"
WshShell.Run """$VenvPython"" -m uvicorn app.main:app --host 0.0.0.0 --port $Port", 0, False
"@

$vbsContent | Set-Content -Path $VbsScript -Encoding ASCII -Force
Write-Host "[+] Created silent background launcher: $VbsScript" -ForegroundColor Green

# 4. Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "[*] Running as Administrator: Registering System Startup Boot Task..." -ForegroundColor Green
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    $Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsScript`""
    $Trigger = New-ScheduledTaskTrigger -AtStartup
    $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings | Out-Null
    Write-Host "[OK] Registered Windows Scheduled Task: '$TaskName' (Starts automatically at Power-On)!" -ForegroundColor Green

    # Add Windows Firewall Rule
    $fwRule = Get-NetFirewallRule -DisplayName "STOCK UNDO Backend Port $Port" -ErrorAction SilentlyContinue
    if (-not $fwRule) {
        New-NetFirewallRule -DisplayName "STOCK UNDO Backend Port $Port" -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow | Out-Null
        Write-Host "[OK] Added Windows Firewall rule for Port $Port." -ForegroundColor Green
    }
} else {
    Write-Host "[*] Registering User Startup & Startup Folder Shortcut..." -ForegroundColor Yellow
    
    # Method A: Windows Startup Folder Shortcut (100% reliable, zero admin required)
    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "StockUndoBackend.vbs"
    Copy-Item $VbsScript $shortcutPath -Force
    Write-Host "[OK] Placed startup launcher in Windows Startup folder: $shortcutPath" -ForegroundColor Green

    # Method B: Scheduled Task at Logon
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    $Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsScript`""
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings | Out-Null
    Write-Host "[OK] Registered Scheduled Task: '$TaskName' (Starts at User Logon)!" -ForegroundColor Green
}

# 5. Start the background service right now
Write-Host "[*] Starting the background service now..." -ForegroundColor Cyan
Start-Process "wscript.exe" -ArgumentList "`"$VbsScript`""
Start-Sleep -Seconds 4

# 6. Verify Health Probe
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 4
    Write-Host "[SUCCESS] Backend is ONLINE on http://127.0.0.1:$Port (Status: $($health.status))" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Backend started. It is initializing on http://127.0.0.1:$Port" -ForegroundColor Cyan
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Setup complete! The backend will now start automatically" -ForegroundColor Green
Write-Host " every time this computer is powered on or restarted." -ForegroundColor Green
Write-Host "==========================================================`n" -ForegroundColor Cyan
