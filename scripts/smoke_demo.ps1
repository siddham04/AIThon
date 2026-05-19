# Smoke demo — requires backend on http://127.0.0.1:8765
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/smoke_demo.py
exit $LASTEXITCODE
