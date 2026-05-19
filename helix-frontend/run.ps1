# Helix frontend launcher (PowerShell)
$ErrorActionPreference = "Stop"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    npm install
}

Write-Host "Starting Helix UI on http://localhost:5173 ..." -ForegroundColor Green
npm run dev
