# STOCK UNDO! - Tally Connectivity & Diagnostic Script (PowerShell)
# Tests connectivity to PC 1 (127.0.0.1:9000) and PC 2 (Tailscale IP:9000)

param (
    [string]$PC1 = "127.0.0.1:9000",
    [string]$PC2 = "100.101.152.68:9000"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STOCK UNDO! - TallyPrime Connectivity Test" -ForegroundColor Yellow
Write-Host " Tagline: 'Check stock before you call the godown!'" -ForegroundColor DarkYellow
Write-Host "============================================================" -ForegroundColor Cyan

function Test-TallyEndpoint {
    param (
        [string]$Name,
        [string]$Endpoint
    )

    $parts = $Endpoint.Split(":")
    $hostName = $parts[0]
    $port = [int]$parts[1]

    Write-Host "`n[*] Testing $Name ($Endpoint)..." -ForegroundColor White

    # 1. TCP Port Test
    $tcp = Test-NetConnection -ComputerName $hostName -Port $port -WarningAction SilentlyContinue
    if ($tcp.TcpTestSucceeded) {
        Write-Host "  [1] TCP Socket:       [PASS] Port $port is OPEN" -ForegroundColor Green
    } else {
        Write-Host "  [1] TCP Socket:       [FAIL] Port $port is CLOSED / Unreachable" -ForegroundColor Red
        return
    }

    # 2. Read-Only XML HTTP POST Test
    $xmlPayload = @"
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>`$`$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>
"@

    try {
        $startTime = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri "http://$Endpoint/" -Method Post -Body $xmlPayload -ContentType "application/xml; charset=utf-8" -TimeoutSec 5
        $startTime.Stop()
        Write-Host "  [2] Read-Only XML:    [PASS] Responded in $($startTime.ElapsedMilliseconds)ms" -ForegroundColor Green
        Write-Host "  [3] Response status:  TallyPrime responded with valid XML payload." -ForegroundColor Cyan
    } catch {
        Write-Host "  [2] Read-Only XML:    [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
}

Test-TallyEndpoint -Name "PC 1 (Local Tally)" -Endpoint $PC1
Test-TallyEndpoint -Name "PC 2 (Remote Tailscale Tally)" -Endpoint $PC2

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " Diagnostic complete." -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Cyan

