# ==============================================================================
# STOCK UNDO! - Windows Auto-Start on Power-On Installer
# Configures the FastAPI backend to run automatically at system boot
# ==============================================================================

param (
    [string]$Port = "8080",
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

# 1. Verify or Create Python Virtual Environment
if (-not (Test-Path $VenvPython)) {
    Write-Host "[*] Virtual environment not found. Creating .venv and installing dependencies..." -ForegroundColor Yellow
    $sysPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $sysPython) {
        $sysPython = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
    if (-not $sysPython) {
        Write-Error "Python is not installed or not in PATH! Please install Python 3.10+ first."
        exit 1
    }
    Push-Location $BackendDir
    & $sysPython -m venv .venv
    if (-not (Test-Path $VenvPython)) {
        Pop-Location
        Write-Error "Failed to create Python virtual environment at '$VenvPython'."
        exit 1
    }
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    Pop-Location
    Write-Host "[OK] Virtual environment created and packages installed!" -ForegroundColor Green
}

# 2. Check for Port Conflicts with Other Existing Servers (Never claim port 8000 or any foreign server port)
$escapedRoot = [System.Management.Automation.WildcardPattern]::Escape($ProjectRoot)
$candidatePorts = @($Port, "8080", "8090", "8095", "8100", "8105", "8110") | Where-Object { $_ -ne "8000" } | Select-Object -Unique
$selectedPort = $null
foreach ($tryPort in $candidatePorts) {
    $portInUse = Get-NetTCPConnection -LocalPort $tryPort -State Listen -ErrorAction SilentlyContinue
    if (-not $portInUse) {
        $selectedPort = $tryPort
        break
    }
    $owningPid = $portInUse.OwningProcess | Select-Object -First 1
    $proc = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
    $procCmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue).CommandLine

    if ($procCmd -and ($procCmd -like "*$escapedRoot*")) {
        Write-Host "[*] Port $tryPort is currently running STOCK UNDO!. Keeping port $tryPort." -ForegroundColor Green
        $selectedPort = $tryPort
        break
    } else {
        Write-Host "[!] Port $tryPort is in use by another server ('$($proc.ProcessName)', PID $owningPid). Checking next port..." -ForegroundColor Yellow
    }
}
if (-not $selectedPort) {
    Write-Error "No free port found among: $($candidatePorts -join ', '). Pass -Port <free_port> manually."
    exit 1
}
$Port = $selectedPort
Write-Host "[+] Selected safe backend port: $Port" -ForegroundColor Cyan

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
    $legacyStartup = Join-Path ([Environment]::GetFolderPath("Startup")) "StockUndoBackend.vbs"
    if (Test-Path $legacyStartup) {
        Remove-Item $legacyStartup -Force -ErrorAction SilentlyContinue
    }
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

# 5. Start the background service right now (if not already listening)
$alreadyListening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $alreadyListening) {
    Write-Host "[*] Starting the background service now..." -ForegroundColor Cyan
    Start-Process "wscript.exe" -ArgumentList "`"$VbsScript`""
    Start-Sleep -Seconds 5
} else {
    Write-Host "[*] Service already running on port $Port." -ForegroundColor Cyan
}

# 6. Verify Health Probe
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] Backend is ONLINE on http://127.0.0.1:$Port (Status: $($health.status))" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Backend started. It is initializing on http://127.0.0.1:$Port" -ForegroundColor Cyan
}

# 7. Inspect existing Tailscale Funnel ports read-only so we NEVER recommend overwriting port 443
$funnelStatusText = ""
try {
    $funnelStatusText = (tailscale serve status 2>&1 | Out-String)
} catch {
    $funnelStatusText = ""
}
$has443Funnel = $funnelStatusText -match "https://[^\s:/]+(\s|\()"
$has8443Funnel = $funnelStatusText -match ":8443(\s|\()"

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Setup complete! The backend will now start automatically" -ForegroundColor Green
Write-Host " every time this computer is powered on or restarted." -ForegroundColor Green
Write-Host " Running on local port: $Port (port 8000 is untouched)" -ForegroundColor Yellow
Write-Host ""
if ($has443Funnel) {
    $safeFunnelPort = if ($has8443Funnel) { "10000" } else { "8443" }
    Write-Host " [IMPORTANT] Tailscale Funnel port 443 is ALREADY used by another server!" -ForegroundColor Yellow
    Write-Host " Run ONLY this command so you do NOT affect your existing server:" -ForegroundColor Cyan
    Write-Host "   tailscale funnel --https=$safeFunnelPort --bg --yes $Port" -ForegroundColor White
} else {
    Write-Host " Next step (expose publicly via Tailscale Funnel):" -ForegroundColor Cyan
    Write-Host "   tailscale funnel --https=8443 --bg --yes $Port" -ForegroundColor White
    Write-Host " (Or on default HTTPS 443 only if no other Funnel app runs on this PC:)" -ForegroundColor DarkGray
    Write-Host "   tailscale funnel --bg --yes $Port" -ForegroundColor DarkGray
}
Write-Host "==========================================================`n" -ForegroundColor Cyan
