<#
.SYNOPSIS
    Wipe zerobox state selectively for dev-testing.
.DESCRIPTION
    Thin wrapper around `python -m zerobox.dev_uninstall`. Forwards every
    argument to the Python module. See `docs/dev-testing.md` for flags and
    full usage.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$backendDir = Join-Path $repoRoot "backend"

Push-Location $backendDir
try {
    python -m zerobox.dev_uninstall @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
