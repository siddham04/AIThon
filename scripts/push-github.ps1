<#
.SYNOPSIS
  One-time HTTPS push to GitHub using a PAT (avoids broken GCM cache during hackathon setup).

.DESCRIPTION
  Prompts for a Personal Access Token securely, pushes main to siddham04/AIThon, then sets upstream to origin.
  Does not store the token in git remote. Clear shell history if you pasted the token in plain text elsewhere.

  Fine-grained token needs: Repository access to AIThon, Contents Read and write, Metadata Read.
#>
param(
  [string]$Owner = 'siddham04',
  [string]$Repo = 'AIThon',
  [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not (Test-Path '.git')) {
  Write-Error 'Run from repo root (this script lives in scripts/).'
  exit 1
}

Write-Host 'Paste your GitHub PAT (input is hidden). Fine-grained: AIThon + Contents Read/Write.' -ForegroundColor Cyan
$secure = Read-Host 'Token' -AsSecureString
if ($secure.Length -lt 1) {
  Write-Error 'No token entered.'
  exit 1
}

$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $token = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
} finally {
  [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}

$pushUrl = "https://${Owner}:${token}@github.com/${Owner}/${Repo}.git"
try {
  # Ephemeral URL push (token not written to .git/config)
  & git push "$pushUrl" "refs/heads/${Branch}:refs/heads/${Branch}"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & git branch --set-upstream-to="origin/${Branch}" $Branch 2>$null
  Write-Host 'Push OK. Next time use: git push' -ForegroundColor Green
} finally {
  $token = $null
  $pushUrl = $null
}
