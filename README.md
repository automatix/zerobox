# Zerobox

AI-powered scan processing app for Windows `11`. Automates the workflow: scan intake, OCR, AI classification (naming + filing), user review, and file operations. Rule-based learning through user-defined JSON profiles.

## Features

- **Automated document processing** — drop files in an inbox folder, get them classified and filed
- **AI-powered classification** — uses Claude API (swappable: OpenAI, Ollama) to propose names and target folders
- **Learnable rule engine** — user corrections create new rules, improving future classifications
- **Review workflow** — approve, reject, or correct proposals before execution
- **Full audit trail** — every action logged to SQLite with timestamps and rule references
- **Desktop app** — Tauri `2` + Svelte `5` frontend with a lightweight, native feel

## Architecture

```
Intake ──> OCR ──> Classifier ──> Review (UI) ──> FileManager
                                     │
                                Rule Engine
                              (learn from corrections)

All steps ──────────────────────────> Audit Logger
```

Modular backend (Python `3.13` + FastAPI) with `9` independent services. The Tauri frontend communicates with the backend via local HTTP (`localhost:8000`).

See [`docs/architecture.md`](docs/architecture.md) for the full architecture document including module interfaces, data models, and dependency injection setup.

---

## User Guide

> For a full walkthrough of the app — First-Run-Wizard, the Review / Rule Profiles / Audit Log / Settings tabs, what to enter in the Rule form, typical workflows, and troubleshooting — see [`docs/user-guide.md`](docs/user-guide.md).

### Installation

Download the latest installer from the [Releases](https://github.com/automatix/zerobox/releases) page. Available formats:

- **NSIS** (`…_x64-setup.exe`) — **recommended.** During setup it detects the OCR tools and, if **Tesseract** or **Ghostscript** are missing, offers to download and install them for you (system-wide or as a portable copy next to zerobox). They are fetched from their upstream projects on your machine — they are not redistributed inside the installer.
- **MSI** (`…_x64_en-US.msi`) — plain Windows Installer package, intended for managed / enterprise deployment (e.g. Group Policy). It does **not** offer to install the OCR tools; install Tesseract and Ghostscript yourself (see [Prerequisites](#prerequisites)).

Either installer bundles the backend and frontend. The OCR tools are never bundled into the artifact (Ghostscript is AGPL-licensed); the First-Run-Wizard verifies both are present and points you to the install steps if not.

### Configuration

#### `config.json` — application settings

Copy `config.example.json` to `config.json` and adjust as needed:

| Section | Key settings |
|---|---|
| `intake` | `input_folder` — path to the inbox; `file_types` — accepted extensions |
| `ocr` | `language` — Tesseract languages (e.g. `"deu+eng"`); `deskew`, `optimize` |
| `llm` | `provider` — `"anthropic"`, `"openai"`, or `"ollama"`; `model`; `temperature` |
| `filemanager` | `output_root` — archive base path; `conflict_strategy` |
| `audit` | `db_path` — SQLite database path |
| `profiles_dir` | Path to rule profile directory |

#### `.env` — secrets

Copy `.env.example` to `.env` and fill in the required keys for your chosen LLM provider:

```bash
ANTHROPIC_API_KEY=sk-ant-...   # if provider = "anthropic"
OPENAI_API_KEY=sk-...          # if provider = "openai"
OLLAMA_BASE_URL=http://localhost:11434  # if provider = "ollama"
```

#### Finding valid model names

The First-Run-Wizard and the `llm.model` setting in `config.json` expect an exact model identifier. Each provider publishes its own catalog:

**Anthropic (Claude)**
- Docs: `https://docs.claude.com/en/docs/about-claude/models`
- API:
  ```bash
  curl https://api.anthropic.com/v1/models \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01"
  ```

**OpenAI (GPT)**
- Docs: `https://platform.openai.com/docs/models`
- API:
  ```bash
  curl https://api.openai.com/v1/models \
    -H "Authorization: Bearer $OPENAI_API_KEY"
  ```

**Ollama (local)**
- CLI: `ollama list` (shows pulled models), `ollama pull <name>` to fetch a new one.
- API:
  ```bash
  curl http://localhost:11434/api/tags
  ```

---

## Developer Guide

### Prerequisites

- **Python** `3.13`+
- **Tesseract OCR** — required by `ocrmypdf` for text extraction
- **Ghostscript** — required by `ocrmypdf` for PDF processing
- **Node.js** `20`+ — for the frontend (pinned via `frontend/.nvmrc`; npm pinned via `packageManager` → enable with `corepack enable`, see `docs/dev-testing.md`)
- **Rust toolchain** — for building the Tauri shell
- **API key** — Anthropic or OpenAI, unless using a local Ollama instance

### Quick Start

#### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Install in editable mode (src layout requires installation)
pip install -e ".[dev]"

# Set up configuration
cp .env.example .env         # then fill in your API key(s)
cp config.example.json config.json  # adjust paths if needed

# Start the backend
uvicorn zerobox.app:create_app --factory --reload
```

The API server starts at `http://localhost:8000`.

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server (Svelte only, without Tauri shell)
npm run dev
```

To run the full desktop app with the Tauri shell:

```bash
# From the frontend/ directory (requires Rust toolchain)
cargo tauri dev
```

#### API Documentation

With the backend running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

### Testing

All test commands run from the `backend/` directory.

#### Unit Tests

```bash
pytest tests/unit/
```

#### BDD Tests

```bash
pytest tests/bdd/
```

#### Postman Collection

An importable Postman collection is available at [`docs/postman/zerobox.postman_collection.json`](docs/postman/zerobox.postman_collection.json). Import it into Postman to test all API endpoints interactively.

### Project Structure

```
zerobox/
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   └── zerobox/          # Python package (src layout)
│   │       ├── app.py        # FastAPI app factory
│   │       ├── config.py     # Pydantic settings
│   │       ├── intake/       # File discovery
│   │       ├── ocr/          # Text extraction (ocrmypdf)
│   │       ├── classifier/   # AI classification + LLM providers
│   │       ├── rules/        # JSON rule profiles
│   │       ├── filemanager/  # Rename + move operations
│   │       ├── audit/        # SQLite action log
│   │       ├── pipeline/     # Orchestration
│   │       └── api/          # FastAPI routes
│   └── tests/                # Unit + BDD tests
├── frontend/
│   ├── src/                  # Svelte 5 components
│   ├── src-tauri/            # Tauri Rust shell + sidecar config
│   └── package.json
├── profiles/                 # User rule profiles (JSON)
├── scripts/                  # Build and installer scripts
├── docs/
│   ├── architecture.md       # Living architecture document
│   ├── in-app-updater.md     # Generic in-app updater foundation (reusable)
│   ├── memory-md.md          # Generic MEMORY.md project-journal pattern (reusable)
│   └── postman/              # Postman collection
├── CLAUDE.md
└── README.md
```
