# Move unrouted React pages to pages/_archive (idempotent).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pages = Join-Path $root "helix-frontend\src\pages"
$archive = Join-Path $pages "_archive"
$keep = @(
  "Landing.jsx", "Login.jsx", "Register.jsx",
  "MissionControl.jsx", "AiWorkspace.jsx", "DeliveryCommandCenter.jsx",
  "CopilotChat.jsx", "Settings.jsx", "WinningDemoScreen.jsx"
)
New-Item -ItemType Directory -Force -Path $archive | Out-Null
$moved = 0
Get-ChildItem $pages -Filter "*.jsx" -File | ForEach-Object {
  if ($keep -notcontains $_.Name) {
    Move-Item -Force $_.FullName $archive
    $moved++
  }
}
Write-Host "Active pages: $((Get-ChildItem $pages -Filter '*.jsx').Count)"
Write-Host "Archived:   $moved -> $archive"
