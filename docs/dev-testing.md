# Dev Testing Notes

## Prerequisites

System-level tools that must be installed before running zerobox from source (none of these are bundled by `pip` / `npm`):

| Tool | Version | Purpose |
|---|---|---|
| Python | `3.13`+ | Backend runtime |
| Node.js | `20`+ | Frontend build + dev server |
| Rust toolchain | stable | Building the Tauri shell (only needed for `cargo tauri dev` / installer builds) |
| Tesseract OCR | `5`+ | Text extraction (invoked by `ocrmypdf`) |
| Ghostscript | `10`+ | PDF processing (invoked by `ocrmypdf`) |

All Python packages — including `uvicorn`, `fastapi`, `ocrmypdf`, `anthropic`, `openai`, `pytest`, `ruff` — are installed automatically by `pip install -e ".[dev]"` and do **not** need to be installed separately. The same applies to the installed end-user build: the Windows installer (MSI/NSIS) bundles the backend (including `uvicorn`) as a standalone PyInstaller executable, so end users only need Tesseract and Ghostscript on their system.

## Running Zerobox in Dev Mode (without installer)

Two terminals needed:

### Terminal 1 — Backend

```bash
cd backend

# Create and activate a virtual environment (strongly recommended — avoids
# the uvicorn/pytest/ruff console scripts landing outside your PATH).
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash) / use .venv\Scripts\activate.bat in cmd, .venv\Scripts\Activate.ps1 in PowerShell
# source .venv/bin/activate      # Linux/macOS

pip install -e ".[dev]"
uvicorn zerobox.app:create_app --factory --reload
```

API available at `http://localhost:8000` (Swagger UI at `/docs`).

> **PATH-safe alternative.** If `uvicorn: command not found` appears despite a successful install (typical on Windows when no venv is used and the user-site `Scripts/` directory isn't on `PATH`), run the server via the Python module instead — this always works:
>
> ```bash
> python -m uvicorn zerobox.app:create_app --factory --reload
> ```

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in the browser.

### What to expect

- On first launch (no `config.json` with `setup_complete: true`), the **First-Run-Wizard** appears.
- The wizard walks through: LLM Provider → Folders → OCR → Summary.
- After completing the wizard, `config.json` and `.env` are written to the per-user config directory (Windows: `%APPDATA%\zerobox\`, macOS: `~/Library/Application Support/zerobox/`, Linux: `$XDG_CONFIG_HOME/zerobox/` or `~/.config/zerobox/`). Override with `ZEROBOX_CONFIG_DIR`. See `DD-07`.
- Subsequent launches skip the wizard and show the main app (Review, Rule Profiles, Audit Log, Settings).

## Full desktop mode (Tauri shell)

```bash
cd frontend
npm run tauri -- dev
```

This uses the `@tauri-apps/cli` devDependency already installed by `npm install` — no extra global install required. `cargo tauri dev` works equivalently but only if you've run `cargo install tauri-cli` beforehand.

Either command starts both the backend sidecar and the Tauri WebView window. In dev mode (`debug_assertions`), the backend is **not** auto-started by Tauri — you must run it manually in Terminal 1.

## Testing the setup endpoints directly

```bash
# Check setup status
curl http://localhost:8000/setup/status

# Validate a provider
curl -X POST http://localhost:8000/setup/validate \
  -H "Content-Type: application/json" \
  -d '{"provider": "anthropic", "api_key": "sk-ant-..."}'

# Save config via wizard
curl -X POST http://localhost:8000/setup/save \
  -H "Content-Type: application/json" \
  -d '{"input_folder": "~/zerobox/inbox", "output_root": "~/zerobox/archive", "profiles_dir": "~/zerobox/profiles", "provider": "anthropic", "api_key": "sk-ant-..."}'
```

## Resetting the wizard

Delete `config.json` from the per-user config directory (see above) to trigger the wizard again on next page load. For selective or scripted resets, prefer the dev-uninstall CLI below.

## In-App Docs Sync

The Help tab renders the repo's `.md` docs from inside the app. To make that work without runtime network access, `frontend/scripts/sync-docs.mjs` copies `README.md` and the user-facing/technical files under `docs/` into `frontend/public/docs/` so Vite bundles them into `dist/` and Tauri bundles `dist/` into the installer.

The script runs automatically before `npm run dev` and `npm run build` (via `predev` / `prebuild` hooks). To run it manually:

```bash
cd frontend
npm run sync-docs
```

Smoke test (asserts every expected file lands in `frontend/public/docs/`):

```bash
cd frontend
npm run test:sync-docs
```

`frontend/public/docs/` is git-ignored — the synced copies are derived artefacts, never committed. If you change the list of bundled docs, edit the `files` array in `frontend/scripts/sync-docs.mjs` and the `expected` array in `frontend/scripts/sync-docs.test.mjs`, and the `docs` array in `frontend/src/views/HelpTab.svelte`.

## Dev-Uninstall / Reset

Wipe zerobox state selectively to retest the First-Run-Wizard or pipeline from a clean slate. Reads the current `config.json` (if present) so user-configured paths are honoured.

### Usage

PowerShell wrapper:

```powershell
scripts/dev-uninstall.ps1 [flags]
```

Bash wrapper:

```bash
scripts/dev-uninstall.sh [flags]
```

Or directly as a Python module:

```bash
cd backend
python -m zerobox.dev_uninstall [flags]
```

### Flags

| Flag | Effect |
|---|---|
| `--all` | Wipe every target below. |
| `--config` | Delete `config.json` (wizard settings). |
| `--env` | Delete `.env` (API keys). |
| `--data-inbox` | Delete the intake input folder. |
| `--data-output` | Delete the archive/output folder. |
| `--profiles` | Delete the rule profiles directory. |
| `--audit` | Delete `audit.db`. |
| `--yes` / `-y` | Skip the final confirmation prompt. |

With no flags the script enters **interactive mode** and asks `y/N` for each target. The script always prints a plan of what will be deleted before proceeding, and exits non-zero if any deletion fails.

### Examples

```bash
# Nuke everything (with confirmation)
scripts/dev-uninstall.sh --all

# Just reset the wizard (keeps data)
scripts/dev-uninstall.ps1 --config --env --yes

# Interactive
scripts/dev-uninstall.sh
```
