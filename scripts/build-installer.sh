#!/usr/bin/env bash
# Build the Zerobox Windows installer (MSI + NSIS).
#
# 1. Packages the Python backend as a standalone executable via PyInstaller.
# 2. Copies the executable to the Tauri sidecar binaries directory.
# 3. Runs `npm run tauri build` to produce the installer.
#
# Prerequisites: Python 3.13+, Node.js 20+, Rust toolchain, PyInstaller.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
TAURI_DIR="$FRONTEND_DIR/src-tauri"
BIN_DIR="$TAURI_DIR/binaries"

echo "=== Step 1: Build Python backend sidecar ==="
cd "$BACKEND_DIR"

pip install pyinstaller --quiet

pyinstaller \
    --name "zerobox-backend-x86_64-pc-windows-msvc" \
    --onefile \
    --noconsole \
    --add-data "zerobox;zerobox" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols" \
    --hidden-import "uvicorn.protocols.http" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan" \
    --hidden-import "uvicorn.lifespan.on" \
    zerobox/__main__.py

mkdir -p "$BIN_DIR"
cp "dist/zerobox-backend-x86_64-pc-windows-msvc.exe" "$BIN_DIR/"

echo "=== Step 2: Build Tauri installer ==="
cd "$FRONTEND_DIR"
npm run tauri build

echo ""
echo "=== Build complete ==="
echo "Installer output: $FRONTEND_DIR/src-tauri/target/release/bundle/"
