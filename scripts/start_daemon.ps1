# Start 24/7 live ingestion daemon on this host
$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\muse-sandbox\btc-5m"
Set-Location $ProjectRoot

# Ensure directories exist
New-Item -ItemType Directory -Path "$ProjectRoot\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null

$PythonExe = "$ProjectRoot\.venv\Scripts\python.exe"
$ScriptPath = "$ProjectRoot\scripts\run_collector.py"
$LogFile = "$ProjectRoot\logs\live_collector.log"
$PidFile = "$ProjectRoot\logs\collector.pid"

# Check if already running
if (Test-Path $PidFile) {
    $OldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($OldPid) {
        $Proc = Get-Process -Id $OldPid -ErrorAction SilentlyContinue
        if ($Proc) {
            Write-Host "Collector is already running with PID $OldPid."
            exit 0
        }
    }
}

Write-Host "Starting live 24/7 collector..."
$Proc = Start-Process -FilePath $PythonExe `
                      -ArgumentList $ScriptPath `
                      -WorkingDirectory $ProjectRoot `
                      -RedirectStandardOutput $LogFile `
                      -RedirectStandardError "$ProjectRoot\logs\live_collector_err.log" `
                      -PassThru

$Proc.Id | Out-File -FilePath $PidFile -Encoding ascii
Write-Host "Collector started with PID $($Proc.Id). Logging to $LogFile."

# Wait briefly and check health
Start-Sleep -Seconds 3
if ($Proc.HasExited) {
    Write-Host "ERROR: Process exited immediately. Last error log:"
    Get-Content "$ProjectRoot\logs\live_collector_err.log" -Tail 20
    exit 1
}

Write-Host "Collector is running cleanly."
