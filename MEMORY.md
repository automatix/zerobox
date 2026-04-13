# MEMORY.md — Zerobox Project Journal

This file documents the evolution of the Zerobox project: requirements, design decisions, problems, solutions, and ideas for future work.

---

## Functional Requirements

### `FR-01` — Batch Scan Processing
The app picks up all files from a configurable input folder and processes them through the full pipeline (OCR → classify → rename → move) in one batch run ("auf Knopfdruck").

### `FR-02` — OCR
Each scanned file is run through OCR to produce a searchable PDF. Input may be image-based PDFs or image files (TIFF, PNG, JPEG).

### `FR-03` — AI-Based Classification
Based on the OCR-extracted text, the app determines:
- the **target filename** (following naming rules),
- the **target folder** (following filing rules).

Classification is powered by a swappable LLM provider (see `FR-08`) guided by user-defined rule sets.

### `FR-04` — Review & Approval UI
Before any file operation is executed, the user sees a summary table:

| Original filename | Target filename | Target folder | Status |
|---|---|---|---|
| `scan_001.pdf` | `2026-04-13_Rechnung_Stadtwerke.pdf` | `Finanzen/Rechnungen/` | pending |

The user can:
- **approve** individual or all entries,
- **reject and correct** entries — corrections feed back into the rule engine.

### `FR-05` — Learnable Rule Sets (Profiles)
Rules are stored in structured files (JSON) and organized as profiles. A profile defines patterns like:
- "If the document contains `Rechnung` and `Stadtwerke`, name it `{date}_Rechnung_Stadtwerke.pdf` and file under `Finanzen/Rechnungen/`."
- Profiles can be created, edited, imported, and exported.
- The system ships with no built-in rules — the user builds them iteratively through the correction loop (`FR-04`).

### `FR-06` — Audit Logging
Every file action (rename, move, delete, rule creation/modification) is logged with timestamp, source, target, and the rule that triggered it. Logs are queryable and stored locally.

### `FR-07` — Configurable with Sensible Defaults
All paths, API endpoints, OCR settings, etc. are configurable. Defaults are provided so the app works out of the box with minimal setup (e.g., input folder = `~/zerobox/inbox`, output root = `~/zerobox/archive`).

---

## Non-Functional Requirements

### `NFR-01` — Modular Architecture
The system is composed of independent, atomic services/modules:
- **Scanner** (file ingestion)
- **OCR Engine** (text extraction)
- **Classifier** (AI-based naming/filing)
- **Rule Engine** (profile management)
- **File Manager** (rename/move operations)
- **Audit Logger**
- **UI**

Each module communicates through well-defined interfaces. Modules can be developed, tested, and replaced independently.

### `NFR-02` — Local-Only Credentials
API keys and secrets are stored exclusively in local files (e.g., `.env`), never committed. Template files (`.env.example`, `config.example.json`) are provided.

### `NFR-03` — Target OS
Windows `11` (primary). Cross-platform support is a future goal, not a current constraint.

### `NFR-04` — Transparency & Traceability
All automated decisions (why a file was named X, why it was filed under Y) must be traceable via audit logs and rule references.

---

## Design Decisions

### `DD-01` — Tech Stack (`2026-04-13`)
**Status:** approved.
See section [Tech Stack Proposal](#tech-stack-proposal) below and `docs/architecture.md` for the full architecture.

### `DD-02` — Rule Storage Format (`2026-04-13`)
**Decision:** JSON files, one file per profile.
**Rationale:** Machine-readable, easily validated with JSON Schema, diff-friendly in Git, no extra dependencies (unlike YAML). Human-editable with any text editor.

### `DD-03` — Audit Log Storage (`2026-04-13`)
**Decision:** SQLite database.
**Rationale:** File-based (no server), queryable with SQL, supports structured data, built into Python's standard library. Lightweight enough for a single-user desktop app.

---

## Tech Stack Proposal

### Backend — Python `3.13`

| Concern | Library / Tool | Rationale |
|---|---|---|
| OCR | `ocrmypdf` (wraps Tesseract) | Produces searchable PDFs directly, handles rotation/deskew, mature, well-maintained |
| AI Classification | `anthropic` SDK (Claude API) | Best-in-class document understanding; structured output for reliable parsing |
| Rule Engine | Custom module + JSON Schema | Keeps it simple; no heavy framework needed for pattern matching on extracted text |
| Audit Log | `sqlite3` (stdlib) | Zero-dependency, local, queryable |
| Configuration | `pydantic-settings` | Type-safe config with `.env` support and sensible defaults |
| API layer | `FastAPI` | Lightweight, async, auto-generates OpenAPI docs; connects backend to frontend |
| Task orchestration | Custom pipeline module | Simple sequential pipeline; no need for Celery/task queues at this scale |

**Why Python?** The OCR and AI ecosystems are Python-first. `ocrmypdf`, `anthropic`, `pydantic` — all are Python-native. Trying to do this in Node.js or Rust would mean fighting the tooling instead of using it.

### Frontend — Tauri `2` + Svelte `5`

| Concern | Choice | Rationale |
|---|---|---|
| Desktop shell | Tauri `2` | ~`5` MB vs Electron's ~`150` MB. Uses the OS WebView (Edge/WebView2 on Windows `11`). Rust core is fast and memory-efficient |
| UI framework | Svelte `5` | Minimal boilerplate, reactive by default, small bundle size. Good fit for a focused app with a few views (not a sprawling SPA) |
| Styling | Tailwind CSS `4` | Utility-first, fast iteration, no custom CSS architecture needed |

**Why not Electron?** Overkill for this use case. Bundles an entire Chromium instance (~`150` MB). Tauri uses the system WebView already present on Windows `11`.

**Why not a Python-only UI (PyQt, Tkinter)?** These frameworks feel dated, have poor developer ergonomics, and make it harder to build a polished review table UI. A web-based frontend is more flexible and easier to iterate on.

### Communication: Backend ↔ Frontend

**Option A (recommended):** Tauri sidecar — Tauri launches the Python backend as a managed child process. Communication via local HTTP (`FastAPI` on `localhost`).

**Option B:** Tauri commands calling Python via CLI. Simpler but less flexible for streaming updates.

### Alternatives Considered

| Alternative | Why not (for now) |
|---|---|
| Electron + React | Heavy runtime, larger bundle, more RAM usage |
| Python + Streamlit | Fast to prototype but limited UI control; not a real desktop app |
| Python + `pywebview` | Lighter than Electron but less mature than Tauri; smaller ecosystem |
| .NET MAUI / WPF | Locks into Microsoft ecosystem; poor AI/OCR library support compared to Python |
| Local LLM (Ollama) | Interesting for offline use — noted as future idea. Claude API is stronger for document classification today |

### `DD-05` — Roadmap and Ticket Structure (`2026-04-13`)
**Decision:** `7`-phase roadmap with `29` tickets (`T-01` through `T-29`), tracked as GitHub Issues with phase labels.
**Rationale:** Phases follow the dependency graph (Foundation → Ingestion → Classification → Pipeline → API → Frontend → Packaging). See `docs/roadmap.md`.

### `DD-06` — Installer Bundling Strategy (`2026-04-13`)
**Decision:** The Windows installer bundles all runtime dependencies (Python, Tesseract, Ghostscript) so the end user has zero prerequisites to install manually.
**Rationale:** Minimum effort for the end user. Trade-off: larger installer (~`200`–`300` MB), but zero-setup experience. Python backend will be packaged as standalone executable (via PyInstaller or cx_Freeze). Tesseract and Ghostscript are bundled alongside. Only user-provided requirement: an API key (Claude/OpenAI) unless using a local LLM.

### `DD-04` — Architecture (`2026-04-13`)
**Decision:** Modular service architecture with `9` modules, LLM provider abstraction, dependency injection, FastAPI backend as Tauri sidecar.
**Rationale:** See `docs/architecture.md` for the full living document.

---

## Functional Requirements (continued)

### `FR-08` — Swappable LLM Provider
The AI classification module supports multiple LLM backends (Claude, OpenAI, local models via Ollama) through a provider abstraction. The active provider is selected via `config.llm.provider`. Each provider implements the `LLMProvider` interface (`classify` + `extract_rule`).

---

## Ideas / Future

- `IDEA-01` — **Offline mode with local LLM** (e.g., Ollama + Mistral/Llama) as fallback when no API key is configured or for privacy-sensitive documents.
- `IDEA-02` — **Watch mode** — monitor the input folder for new files and auto-trigger the pipeline (instead of manual "Knopfdruck").
- `IDEA-03` — **Cross-platform support** — Tauri already supports macOS/Linux; Python backend is OS-agnostic.
- `IDEA-04` — **Rule sharing** — export/import rule profiles for community sharing.
- `IDEA-05` — **Duplicate detection** — flag files that appear to be duplicates of already-filed documents.
- `IDEA-06` — **Preview pane** — show a thumbnail/preview of the scanned document alongside the classification result in the review table.

---

## Work Log

### `2026-04-13` — T-03: Credential and Config Templates
**Anfrage:** `T-03` umsetzen.
**Durchgeführt:** `backend/.env.example` (Placeholder-Keys) und `backend/config.example.json` (alle Felder mit Defaults) erstellt. `.gitignore` angepasst: `config.json` hinzugefügt, `.env.example` per `!`-Ausnahme whitegelistet.
**Ergebnis:** `T-03` abgeschlossen und als **Done** geschlossen.

### `2026-04-13` — T-02: Configuration Module
**Anfrage:** `T-02` umsetzen.
**Durchgeführt:** `backend/zerobox/config.py` erstellt mit `AppConfig` (pydantic-settings), Sektionen `ScannerConfig`, `OcrConfig`, `LLMConfig`, `FileManagerConfig`, `AuditConfig`. Laden aus `config.json` mit Fallback auf Defaults, Secrets aus `.env`. Validierung bei Startup (z.B. ungültiger Provider → `ValidationError`). In App Factory integriert, `/config`-Endpoint hinzugefügt.
**Ergebnis:** `T-02` abgeschlossen und als **Done** geschlossen.

### `2026-04-13` — T-01: Backend Project Scaffolding
**Anfrage:** Phase-`1`-Issues auf Ready setzen, `T-01` umsetzen.
**Durchgeführt:** `T-01` bis `T-04` auf **Ready** gesetzt. `T-01` implementiert: `backend/pyproject.toml`, Package-Struktur mit allen `9` Modulverzeichnissen, `app.py` (FastAPI Factory mit `/health`), `__main__.py` (Entry Point), venv eingerichtet, `python -m zerobox` verifiziert.
**Ergebnis:** `T-01` abgeschlossen und als **Done** geschlossen. Python `3.14.2` ist auf dem System (statt `3.13` — kompatibel, da `requires-python = ">=3.13"`).

### `2026-04-13` — GitHub Project Sync Check
**Anfrage:** Prüfen, ob das GitHub Project (`https://github.com/users/automatix/projects/1`) mit dem Repo `automatix/zerobox` in Sync ist.
**Durchgeführt:** `gh` CLI lokalisiert (`C:\Program Files\GitHub CLI\gh.exe`), Token-Scopes um `read:project` und `project` erweitert, Project-Inhalt abgefragt.
**Ergebnis:** Repo und Project sind vollständig verknüpft. Alle `29` Issues (`T-01` bis `T-29`) sind im Project vorhanden.
