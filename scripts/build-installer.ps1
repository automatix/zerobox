<#
.SYNOPSIS
    Build the Zerobox Windows installer (MSI + NSIS).
.DESCRIPTION
    1. Packages the Python backend as a standalone executable via PyInstaller.
    2. Copies the executable to the Tauri sidecar binaries directory.
    3. Runs `npm run tauri build` to produce the installer.
.NOTES
    Prerequisites: Python 3.13+, Node.js 20+, Rust toolchain.
    Runs under both Windows PowerShell 5.1 and PowerShell 7+.
    Uses backend/.venv if present (recommended — ensures PyInstaller can trace
    the backend's dependencies during analysis); otherwise falls back to the
    `python` on PATH. See docs/dev-testing.md.
#>

# Do NOT set `$ErrorActionPreference = "Stop"` here: under Windows PowerShell
# 5.1 any native tool that writes to stderr (pip, pyinstaller, npm, cargo) is
# promoted to a terminating NativeCommandError even when it exits 0, which
# aborts the build (#120). Instead keep going and check $LASTEXITCODE after
# every native command via Invoke-Native.
$ErrorActionPreference = "Continue"

# Silence pip's "A new release of pip is available" notice (stderr noise).
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Command,
        [Parameter(Mandatory = $true)][string]$What
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$What failed (exit code $LASTEXITCODE)."
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$tauriDir = Join-Path $frontendDir "src-tauri"
$binDir = Join-Path $tauriDir "binaries"

# Resolve the Python interpreter. Prefer the backend venv so PyInstaller can
# import the backend's dependencies (fastapi, uvicorn, …) while tracing imports.
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
    Write-Host "Using backend venv: $python" -ForegroundColor DarkGray
} else {
    $python = "python"
    Write-Host "backend/.venv not found - using 'python' on PATH. If the build cannot import backend modules, create the venv first (see docs/dev-testing.md)." -ForegroundColor Yellow
}

Write-Host "=== Step 1: Build Python backend sidecar ===" -ForegroundColor Cyan

Push-Location $backendDir
try {
    # Install PyInstaller into the chosen interpreter if needed.
    Invoke-Native { & $python -m pip install pyinstaller --quiet } "pip install pyinstaller"

    # Build the backend as a single executable. The zerobox package and its full
    # dependency tree are traced statically from __main__.py's `from zerobox.app
    # import create_app` (#146) — do NOT reintroduce the old
    # `--add-data "src/zerobox;zerobox"` + factory-string approach: it shipped the
    # backend without fastapi & friends. The uvicorn hidden imports stay because
    # uvicorn resolves its loops/protocols implementations dynamically.
    Invoke-Native {
        & $python -m PyInstaller `
            --name "zerobox-backend-x86_64-pc-windows-msvc" `
            --onefile `
            --noconsole `
            --hidden-import "uvicorn.logging" `
            --hidden-import "uvicorn.loops" `
            --hidden-import "uvicorn.loops.auto" `
            --hidden-import "uvicorn.protocols" `
            --hidden-import "uvicorn.protocols.http" `
            --hidden-import "uvicorn.protocols.http.auto" `
            --hidden-import "uvicorn.protocols.websockets" `
            --hidden-import "uvicorn.protocols.websockets.auto" `
            --hidden-import "uvicorn.lifespan" `
            --hidden-import "uvicorn.lifespan.on" `
            src/zerobox/__main__.py
    } "PyInstaller"

    # Smoke test: the frozen sidecar must actually boot and serve /health (#146).
    # A missing bundled dependency crashes the exe on launch — catch that here
    # instead of after shipping an installer.
    Write-Host "=== Step 1.5: Smoke-test the sidecar exe ===" -ForegroundColor Cyan
    $healthUrl = "http://127.0.0.1:8000/health"
    $portBusy = $false
    try {
        Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
        $portBusy = $true
    } catch {}
    if ($portBusy) {
        Write-Host "Port 8000 is already serving /health (dev backend running?) - skipping the smoke test. Stop the dev backend for a fully verified build." -ForegroundColor Yellow
    } else {
        $sidecar = Start-Process -FilePath (Resolve-Path "dist\zerobox-backend-x86_64-pc-windows-msvc.exe") -PassThru
        try {
            $healthy = $false
            foreach ($attempt in 1..30) {
                if ($sidecar.HasExited) { break }
                Start-Sleep -Milliseconds 500
                try {
                    $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
                    if ($resp.StatusCode -eq 200) { $healthy = $true; break }
                } catch {}
            }
            if (-not $healthy) {
                throw "Sidecar smoke test failed: the frozen backend did not serve $healthUrl (exited: $($sidecar.HasExited))."
            }
            Write-Host "Sidecar smoke test passed: /health is up." -ForegroundColor Green
        }
        finally {
            if (-not $sidecar.HasExited) { Stop-Process -Id $sidecar.Id -Force }
        }
    }

    # Copy to Tauri binaries.
    if (!(Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir | Out-Null }
    Copy-Item "dist\zerobox-backend-x86_64-pc-windows-msvc.exe" $binDir -Force
}
finally {
    Pop-Location
}

Write-Host "=== Step 2: Build Tauri installer ===" -ForegroundColor Cyan

Push-Location $frontendDir
try {
    Invoke-Native { npm run tauri build } "npm run tauri build"
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Installer output: $tauriDir\target\release\bundle\"
