# Helix backend launcher (PowerShell)
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -q --upgrade pip
pip install -q -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env from template — add Azure OpenAI and/or Anthropic keys." -ForegroundColor Yellow
}

# Repo-root .env often sets POSTGRES_URL; fall back to SQLite when Postgres is not up.
if ($env:FORCE_POSTGRES -ne "1") {
    $pgUp = $false
    try {
        $pgUp = (Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -WarningAction SilentlyContinue).TcpTestSucceeded
    } catch { $pgUp = $false }
    if (-not $pgUp) {
        $env:DATABASE_URL = "sqlite:///./helix.db"
        Remove-Item Env:POSTGRES_URL -ErrorAction SilentlyContinue
        Write-Host "Postgres not reachable — using SQLite (helix.db). Set FORCE_POSTGRES=1 to require Postgres." -ForegroundColor Yellow
    }
}

Write-Host "Seeding showcase project (idempotent)..." -ForegroundColor Cyan
.\.venv\Scripts\python scripts\seed.py 2>$null

$env:HELIX_DEMO_FAST = "true"
$env:HELIX_ALLOW_INSECURE_JWT = "1"
$env:HELIX_DEBUG = "true"
# Production pilot: set JWT_SECRET in .env; set HELIX_PRODUCTION=1 (disables guest + OpenAPI)
Write-Host "Starting Helix API on http://127.0.0.1:8765 (REST only) ..." -ForegroundColor Green
Write-Host "Preflight health:  http://127.0.0.1:8765/api/health" -ForegroundColor Cyan
Write-Host "Backup package:     http://localhost:5173/project/proj_demo_seed01/ai-workspace" -ForegroundColor Cyan
Write-Host "Open the UI:        cd ..\helix-frontend; npm run dev  ->  http://localhost:5173" -ForegroundColor Cyan
uvicorn app.main:app --reload --port 8765
