# Dev Testing Notes

## Running Zerobox in Dev Mode (without installer)

Two terminals needed:

### Terminal 1 — Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn zerobox.app:create_app --factory --reload
```

API available at `http://localhost:8000` (Swagger UI at `/docs`).

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
- After completing the wizard, `config.json` and `.env` are written to the backend working directory.
- Subsequent launches skip the wizard and show the main app (Review, Rule Profiles, Audit Log, Settings).

## Full desktop mode (Tauri shell)

```bash
cd frontend
cargo tauri dev
```

This starts both the backend sidecar and the Tauri WebView window. In dev mode (`debug_assertions`), the backend is **not** auto-started by Tauri — you must run it manually in Terminal 1.

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

Delete `config.json` in the backend directory to trigger the wizard again on next page load.
