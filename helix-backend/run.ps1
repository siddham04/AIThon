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

Write-Host "Starting Helix API on http://127.0.0.1:8765 ..." -ForegroundColor Green
uvicorn app.main:app --reload --port 8765
