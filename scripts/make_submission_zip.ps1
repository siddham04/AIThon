<#
.SYNOPSIS
  Create a hackathon submission ZIP (excludes heavy regeneratable paths).

.DESCRIPTION
  Run from repository root:
    powershell -ExecutionPolicy Bypass -File scripts\make_submission_zip.ps1

  Output: Helix-AI-Thon-submission.zip in the **parent directory** of the repo
  (so the archive is not inside the folder being compressed).

  Requires: tar.exe (Windows 10+ / Git for Windows).
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$parent = Split-Path -Parent $RepoRoot
$OutZip = Join-Path $parent "Helix-AI-Thon-submission.zip"
if (Test-Path $OutZip) { Remove-Item -LiteralPath $OutZip -Force }

if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
  Write-Error "tar.exe not found. Install Git for Windows or use Windows 10+ built-in tar."
}

$excludes = @(
  "node_modules",
  ".venv",
  ".venv2",
  "venv",
  "env",
  "dist",
  ".vite",
  "playwright-report",
  "test-results",
  "blob-report",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".git",
  ".DS_Store",
  "Thumbs.db"
)

$tarArgs = @("-a", "-c", "-f", $OutZip)
foreach ($e in $excludes) {
  $tarArgs += "--exclude=$e"
}
$tarArgs += "."

Write-Host "Repo:  $RepoRoot"
Write-Host "Out:   $OutZip"
Push-Location $RepoRoot
try {
  & tar @tarArgs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}

$mb = [math]::Round((Get-Item $OutZip).Length / 1MB, 2)
Write-Host "Done. Size: $mb MB"
if ($mb -gt 50) {
  Write-Warning "ZIP exceeds 50 MB. Remove large binaries/media from the repo or zip from a clean clone."
}
