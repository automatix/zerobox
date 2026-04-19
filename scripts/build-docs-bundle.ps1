<#
.SYNOPSIS
    Bundle the repo documentation into docs.zip for release attachment.
.DESCRIPTION
    Collects README.md and the user-facing files under docs/ into docs.zip
    in the repo root, ready to be uploaded to a GitHub Release alongside
    the installer MSI/NSIS. See docs/dev-testing.md for usage in the
    release flow. Implements IDEA-13 phase 1.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$staging = Join-Path $repoRoot ".docs-bundle-staging"
$output = Join-Path $repoRoot "docs.zip"

if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
if (Test-Path $output) { Remove-Item -Force $output }
New-Item -ItemType Directory -Path $staging | Out-Null
$stagingDocs = Join-Path $staging "docs"
New-Item -ItemType Directory -Path $stagingDocs | Out-Null

# Files included in the bundle
Copy-Item (Join-Path $repoRoot "README.md") $staging
Copy-Item (Join-Path $repoRoot "docs/user-guide.md") $stagingDocs
Copy-Item (Join-Path $repoRoot "docs/architecture.md") $stagingDocs
Copy-Item (Join-Path $repoRoot "docs/dev-testing.md") $stagingDocs
Copy-Item (Join-Path $repoRoot "docs/roadmap.md") $stagingDocs
Copy-Item (Join-Path $repoRoot "docs/postman") $stagingDocs -Recurse

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $output -Force
Remove-Item -Recurse -Force $staging

Write-Host "Created: $output" -ForegroundColor Green
