<#
Starts the local PGER dashboard and opens it in the Windows default browser.
Run from PowerShell: .\LAUNCH_DASHBOARD.ps1
#>

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# Works both from the source tree (this script at the project root, dashboard
# at app\dashboard.py) and from the submission package (this script and
# dashboard.py copied side by side into the same folder).
$candidatePaths = @(
    (Join-Path $projectRoot 'app\dashboard.py'),
    (Join-Path $projectRoot 'dashboard.py')
)
$dashboardPath = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $dashboardPath) {
    throw "dashboard.py was not found next to this script or under app\. Checked: $($candidatePaths -join ', ')"
}
$dashboardPath = (Resolve-Path -LiteralPath $dashboardPath).Path
$dashboardPort = $null
$ports = 8501..8510

foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listener) {
        continue
    }
    $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue).CommandLine
    if ($commandLine -and $commandLine.IndexOf($dashboardPath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
        $dashboardPort = $port
        break
    }
}

if (-not $dashboardPort) {
    $dashboardPort = $ports | Where-Object {
        -not (Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue)
    } | Select-Object -First 1
}

if (-not $dashboardPort) {
    throw "Ports 8501 to 8510 are in use. Close one local service and run this launcher again."
}

$dashboardUrl = "http://localhost:$dashboardPort"
$listener = Get-NetTCPConnection -LocalPort $dashboardPort -State Listen -ErrorAction SilentlyContinue

if (-not $listener) {
    try {
        $pythonPath = (Get-Command python -ErrorAction Stop).Source
    }
    catch {
        throw "Python was not found on PATH. Install Python 3.11+ and 'pip install -r requirements.txt' from the project folder, then run this script again."
    }
    $process = Start-Process -FilePath $pythonPath `
        -ArgumentList @('-m', 'streamlit', 'run', ('"{0}"' -f $dashboardPath), '--server.headless=true', ("--server.port={0}" -f $dashboardPort)) `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $dashboardUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        if ($process.HasExited) {
            throw "The dashboard process stopped before it became available. Run 'python -m streamlit run dashboard/dashboard.py' from the project folder to see the error."
        }
        throw "The dashboard did not start within 30 seconds. Check that Python and Streamlit are available."
    }
}

Write-Host "Dashboard link: $dashboardUrl"
Start-Process $dashboardUrl
