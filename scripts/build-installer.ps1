<#
.SYNOPSIS
    Build the Zerobox Windows installer (MSI + NSIS).
.DESCRIPTION
    1. Packages the Python backend as a standalone executable via PyInstaller.
    2. Copies the executable to the Tauri sidecar binaries directory.
    3. Runs `npm run tauri build` to produce the installer.
.NOTES
    Prerequisites: Python 3.13+, Node.js 20+, Rust toolchain, PyInstaller.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$tauriDir = Join-Path $frontendDir "src-tauri"
$binDir = Join-Path $tauriDir "binaries"

Write-Host "=== Step 1: Build Python backend sidecar ===" -ForegroundColor Cyan

Push-Location $backendDir

# Install PyInstaller if needed
pip install pyinstaller --quiet

# Build the backend as a single executable
pyinstaller `
    --name "zerobox-backend-x86_64-pc-windows-msvc" `
    --onefile `
    --noconsole `
    --add-data "zerobox;zerobox" `
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
    zerobox/__main__.py

# Copy to Tauri binaries
if (!(Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir | Out-Null }
Copy-Item "dist\zerobox-backend-x86_64-pc-windows-msvc.exe" $binDir -Force

Pop-Location

Write-Host "=== Step 2: Build Tauri installer ===" -ForegroundColor Cyan

Push-Location $frontendDir
npm run tauri build
Pop-Location

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Installer output: $frontendDir\src-tauri\target\release\bundle\"
