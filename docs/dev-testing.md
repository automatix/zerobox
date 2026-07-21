# Dev Testing Notes

## Prerequisites

System-level tools that must be installed before running zerobox from source (none of these are bundled by `pip` / `npm`):

| Tool | Version | Purpose |
|---|---|---|
| Python | `3.13`+ | Backend runtime |
| Node.js | `20`+ (pinned via `frontend/.nvmrc`) | Frontend build + dev server |
| npm | `10.9.2` (pinned via `frontend/package.json` → `packageManager`) | Frontend package manager |
| Rust toolchain | stable | Building the Tauri shell (only needed for `cargo tauri dev` / installer builds) |
| Tesseract OCR | `5`+ | Text extraction (invoked by `ocrmypdf`) |
| Ghostscript | `10`+ | PDF processing (invoked by `ocrmypdf`) |

All Python packages — including `uvicorn`, `fastapi`, `ocrmypdf`, `anthropic`, `openai`, `pytest`, `ruff` — are installed automatically by `pip install -e ".[dev]"` and do **not** need to be installed separately. The same applies to the installed end-user build: the Windows installer (MSI/NSIS) bundles the backend (including `uvicorn`) as a standalone PyInstaller executable, so end users only need Tesseract and Ghostscript on their system.

### Node.js and npm version pinning

To prevent `frontend/package-lock.json` drift across dev machines, the Node.js + npm versions are pinned canonically:

- `frontend/.nvmrc` — Node major-version alias. Run `nvm use` inside `frontend/` to switch to a matching Node line (installs on demand with `nvm install`).
- `frontend/package.json` → `"packageManager": "npm@10.9.2"` — Corepack reads this and transparently downloads + invokes that exact npm version whenever you run `npm …` from the frontend directory.
- `frontend/package.json` → `"engines": { "node": ">=20.0.0", "npm": ">=10.0.0" }` — soft guard; npm emits a warning if your runtime is below the floor.

Enable Corepack once per machine (ships with most Node distributions, but you have to activate it):

```bash
corepack enable
```

If `corepack: command not found` (some newer Node builds omit it), install it standalone:

```bash
npm install -g corepack && corepack enable
```

From then on, `cd frontend && npm install` uses the pinned npm automatically — even if your system npm is a different version. Without Corepack active the pin is advisory only: `npm` / `engines` warnings will fire, but the installed npm on `PATH` is what actually runs, and it may re-write `frontend/package-lock.json` into whatever format *that* npm version prefers.

## Running Zerobox in Dev Mode (without installer)

Two terminals needed:

### Terminal 1 — Backend

**One-time setup** (per clone):

```bash
cd backend
python -m venv .venv                 # creates the venv directory
source .venv/Scripts/activate        # see the activation table below
pip install -e ".[dev]"              # installs uvicorn, fastapi, pytest, ruff, …
```

**Every session** (each time you start the backend):

```bash
cd backend
source .venv/Scripts/activate        # activate the existing venv
uvicorn zerobox.app:create_app --factory --reload
```

**Re-run `pip install -e ".[dev]"`** only when `backend/pyproject.toml` dependencies change (git pull brings new deps, you add a package, etc.). `python -m venv .venv` is never repeated unless you delete the `.venv` directory.

API available at `http://localhost:8000` (Swagger UI at `/docs`).

#### venv activation by shell

| Shell | Activate command |
|---|---|
| Git Bash (Windows) | `source .venv/Scripts/activate` |
| PowerShell (Windows) | `.venv\Scripts\Activate.ps1` |
| `cmd.exe` (Windows) | `.venv\Scripts\activate.bat` |
| bash / zsh (Linux/macOS) | `source .venv/bin/activate` |

Your prompt should change to show `(.venv)` once active. Run `deactivate` to leave the venv.

> **PATH-safe alternative.** If `uvicorn: command not found` appears despite a successful install (typical on Windows when no venv is used and the user-site `Scripts/` directory isn't on `PATH`), run the server via the Python module instead — this always works:
>
> ```bash
> python -m uvicorn zerobox.app:create_app --factory --reload
> ```

### Terminal 2 — Frontend

**One-time setup** (per clone, and whenever `frontend/package.json` dependencies change):

```bash
cd frontend
nvm use                # picks the Node line from frontend/.nvmrc (skip if you use another version manager)
npm install            # uses the npm version pinned via packageManager (requires corepack enable, see Prerequisites)
```

**Every session:**

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in the browser.

### What to expect

- On first launch (no `config.json` with `setup_complete: true`), the **First-Run-Wizard** appears.
- The wizard walks through: LLM Provider → Folders → OCR → Summary.
- After completing the wizard, `config.json` and `.env` are written to the per-user config directory (Windows: `%APPDATA%\zerobox\`, macOS: `~/Library/Application Support/zerobox/`, Linux: `$XDG_CONFIG_HOME/zerobox/` or `~/.config/zerobox/`). Override with `ZEROBOX_CONFIG_DIR`. See `DD-07`.
- Subsequent launches skip the wizard and show the main app (Review, Rule Profiles, Audit Log, Settings).
- OCR tools (Tesseract, Ghostscript) are user-installed prerequisites — **not bundled** (`#126`, `DD-10`; Ghostscript is AGPL-licensed). When they are missing, the wizard's OCR step shows an "OCR tools required" notice with install instructions and a docs link, and lets you continue (`Next` is never blocked there); `GET /setup/status` reports `tesseract_available` / `ghostscript_available` so the step can show a coloured dot per tool.

## Full desktop mode (Tauri shell)

```bash
cd frontend
npm run tauri -- dev
```

This uses the `@tauri-apps/cli` devDependency already installed by `npm install` — no extra global install required. `cargo tauri dev` works equivalently but only if you've run `cargo install tauri-cli` beforehand.

Either command starts both the backend sidecar and the Tauri WebView window. In dev mode (`debug_assertions`), the backend is **not** auto-started by Tauri — you must run it manually in Terminal 1.

## Building the installer (MSI + NSIS)

```powershell
scripts/build-installer.ps1
```

The script packages the backend with PyInstaller, **smoke-tests the frozen sidecar** (boots the exe and polls `GET /health`; the build fails if the sidecar cannot start — `#146`), copies it into the Tauri sidecar `binaries/` directory, and runs `npm run tauri build`. Output lands under `frontend/src-tauri/target/release/bundle/` (`msi/` and `nsis/`). The smoke test is skipped with a warning if port `8000` is already serving (e.g. a running dev backend) — stop it for a fully verified build.

Notes:
- Runs under both **Windows PowerShell 5.1** and **PowerShell 7+**. It checks each native tool's exit code explicitly rather than relying on `$ErrorActionPreference = "Stop"`, which under PS 5.1 would abort on harmless stderr output from `pip` / `pyinstaller` / `npm` / `cargo` (`#120`).
- It prefers `backend/.venv` (so PyInstaller can trace the backend's dependencies). Create it first via the Prerequisites steps; otherwise the script falls back to the `python` on `PATH` and warns.
- The OCR tools (Tesseract, Ghostscript) are **not** bundled — they are user prerequisites (`DD-10`).

For the full picture — how the installer/uninstaller work end to end, the user-facing flow, the decisions and problems behind them, and what is general vs Python- vs zerobox-specific — see [`windows-installer.md`](./windows-installer.md).

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
