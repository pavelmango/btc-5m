# Check status of 24/7 live ingestion daemon
$ProjectRoot = "C:\Users\muse-sandbox\btc-5m"
$PidFile = "$ProjectRoot\logs\collector.pid"
$LogFile = "$ProjectRoot\logs\live_collector.log"

if (-not (Test-Path $PidFile)) {
    Write-Host "Collector is NOT running (no PID file)."
    exit 1
}

$PidVal = Get-Content $PidFile
$Proc = Get-Process -Id $PidVal -ErrorAction SilentlyContinue

if (-not $Proc) {
    Write-Host "Collector process (PID $PidVal) is NOT running."
    exit 1
}

Write-Host "Collector is ACTIVE (PID $PidVal, CPU: $($Proc.CPU)s, WorkingSet: $([math]::Round($Proc.WorkingSet64 / 1MB, 2)) MB)."

# Probe health endpoint
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:9102/health" -TimeoutSec 2
    Write-Host "Health endpoint (:9102/health): OK"
    Write-Host "Telemetry:"
    $resp | ConvertTo-Json -Depth 4
} catch {
    Write-Host "Health endpoint check failed: $_"
}

Write-Host "`nRecent logs:"
if (Test-Path $LogFile) {
    Get-Content $LogFile -Tail 15
}
