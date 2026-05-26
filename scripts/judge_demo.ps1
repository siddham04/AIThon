# Helix — Judge Mode launcher (Windows / PowerShell)
#
# One-command, offline-safe demo. See docs/JUDGE_MODE.md.
#
# What this does:
#   1. Verifies prerequisites (python, node, npm).
#   2. Starts the backend on :8765 in demo mode (HELIX_DEMO_FAST=true).
#   3. Starts the frontend dev server on :5173.
#   4. Polls /api/health until green, then opens the seeded project
#      Delivery Package in the default browser.
#   5. Prints a single status line per gate; exits non-zero on any failure.
#
# Stop both servers: Ctrl+C in this window (closes the launched windows too).

[CmdletBinding()]
param(
    [int]$BackendPort = 8765,
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Write-Step($msg) { Write-Host "[judge_demo] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[judge_demo] OK   $msg" -ForegroundColor Green }
function Write-Bad($msg)  { Write-Host "[judge_demo] FAIL $msg" -ForegroundColor Red }

# 1. Prereqs ------------------------------------------------------------
Write-Step "Checking prerequisites..."
foreach ($cmd in @("python", "node", "npm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Bad "$cmd not found on PATH. Install it, then retry."
        exit 2
    }
}
Write-Ok "python, node, npm available"

# 2. Free target ports --------------------------------------------------
function Test-PortFree([int]$port) {
    $busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return -not $busy
}
foreach ($p in @($BackendPort, $FrontendPort)) {
    if (-not (Test-PortFree $p)) {
        Write-Bad "Port $p is already in use. Run: Get-NetTCPConnection -LocalPort $p -State Listen | Select OwningProcess"
        exit 3
    }
}
Write-Ok "Ports $BackendPort and $FrontendPort are free"

# 3. Launch backend in a new window -------------------------------------
Write-Step "Starting backend (helix-backend\run.ps1) on :$BackendPort ..."
$backendCmd = "cd `"$repoRoot\helix-backend`"; `$env:HELIX_DEMO_FAST='true'; `$env:HELIX_USE_AI='false'; .\run.ps1"
$backendProc = Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $backendCmd) -PassThru -WindowStyle Normal

# 4. Launch frontend in a new window ------------------------------------
Write-Step "Starting frontend (helix-frontend\npm run dev) on :$FrontendPort ..."
$frontendCmd = "cd `"$repoRoot\helix-frontend`"; if (-not (Test-Path node_modules)) { npm ci }; npm run dev -- --port $FrontendPort"
$frontendProc = Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-Command", $frontendCmd) -PassThru -WindowStyle Normal

# 5. Poll backend health ------------------------------------------------
Write-Step "Waiting for backend /api/health (up to 90s)..."
$healthOk = $false
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $healthOk = $true; break }
    } catch { }
}
if (-not $healthOk) {
    Write-Bad "Backend never became healthy on :$BackendPort"
    Write-Host "  Look at the backend window for errors, or run: cd helix-backend; .\run.ps1"
    exit 4
}
Write-Ok "Backend healthy on http://127.0.0.1:$BackendPort"

# 6. Verify seeded project is queryable --------------------------------
Write-Step "Verifying seeded project proj_demo_seed01 ..."
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 3
    Write-Ok "Seed step ran (see backend window for 'Seeding showcase project')"
} catch {
    Write-Bad "Could not reach API to verify seed."
    exit 5
}

# 7. Poll frontend ------------------------------------------------------
Write-Step "Waiting for frontend on :$FrontendPort (up to 90s)..."
$uiOk = $false
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $uiOk = $true; break }
    } catch { }
}
if (-not $uiOk) {
    Write-Bad "Frontend never responded on :$FrontendPort"
    Write-Host "  Look at the frontend window for errors, or run: cd helix-frontend; npm run dev"
    exit 6
}
Write-Ok "Frontend responding on http://localhost:$FrontendPort"

# 8. Open browser to the seeded Delivery Package -----------------------
$demoUrl = "http://localhost:$FrontendPort/project/proj_demo_seed01/ai-workspace"
if (-not $NoBrowser) {
    Write-Step "Opening $demoUrl ..."
    Start-Process $demoUrl
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host " HELIX JUDGE MODE READY" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host " API:        http://127.0.0.1:$BackendPort" -ForegroundColor Green
Write-Host " UI:         http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host " Pre-baked:  $demoUrl" -ForegroundColor Green
Write-Host " Login:      demo@demo.com / demo123  (or 'Try as Guest')" -ForegroundColor Green
Write-Host " Mode:       HELIX_DEMO_FAST=true, HELIX_USE_AI=false (offline)" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers (closes the spawned windows)."

try {
    while ($true) {
        Start-Sleep -Seconds 5
        if ($backendProc.HasExited)  { Write-Bad "Backend process exited unexpectedly.";  exit 7 }
        if ($frontendProc.HasExited) { Write-Bad "Frontend process exited unexpectedly."; exit 8 }
    }
} finally {
    if (-not $backendProc.HasExited)  { Stop-Process -Id $backendProc.Id  -Force -ErrorAction SilentlyContinue }
    if (-not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Step "Stopped backend + frontend."
}
