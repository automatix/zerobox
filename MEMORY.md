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
- **Intake** (file discovery)
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
**Decision:** `7`-phase roadmap with `29` tickets (`#1` through `#29`), tracked as GitHub Issues with phase labels.
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
- `IDEA-07` — **Test coverage tooling** — add `pytest-cov` to dev dependencies and configure coverage reporting.
- `IDEA-08` — **User-defined LLM providers** — allow users to register a custom provider entry in the First-Run-Wizard / Settings (name, base URL, model, auth scheme) instead of picking from the fixed list (`anthropic`, `openai`, `ollama`). Useful for OpenAI-compatible gateways (Azure OpenAI, LiteLLM, LocalAI, Groq, self-hosted vLLM, etc.).
- `IDEA-09` — **Model picker assistance** — replace the free-text model field in the First-Run-Wizard / Settings with guided input: live-fetch available models from the selected provider (Anthropic `/v1/models`, OpenAI `/v1/models`, Ollama `/api/tags`) as a dropdown/autocomplete, fall back to a curated list of known models per provider if the API is unreachable, and surface metadata (context window, approximate cost, capability tags). Also warn when the stored default has been deprecated/retired.

---

## Work Log

### `2026-04-18` — `#48`: Update default Claude model to `claude-sonnet-4-6`
**Request:** Replace the stale hardcoded default Claude model (`claude-sonnet-4-20250514`) with the current Sonnet identifier.
**Done:** Updated defaults to `claude-sonnet-4-6` in `SetupWizard.svelte` (initial state + `providerModels.anthropic.defaultModel`), `backend/src/zerobox/config.py`, `backend/src/zerobox/api/routes/setup.py`, `backend/config.example.json`, `backend/tests/unit/test_anthropic_provider.py` (default fixture only), and `docs/architecture.md`. OpenAI (`gpt-4o`) and Ollama (`llama3`) defaults unchanged.
**Result:** `#48` closed via PR `#50`. `178` unit tests green.

### `2026-04-18` — `#47`: Document how to discover valid LLM model names
**Request:** Add examples to the docs explaining how to find valid model identifiers per LLM provider.
**Done:** New "Finding valid model names" subsection in `README.md` under Configuration with doc URLs and concrete curl/CLI examples for Anthropic, OpenAI, and Ollama.
**Result:** `#47` closed via PR `#49`.

### `2026-04-18` — `#45`: Sync frontend package-lock.json to `0.1.1`
**Request:** Resolve the remaining stash or discard it — ensure the stash list is empty.
**Done:** Stash contained a legitimate version drift fix (`package-lock.json` at `0.0.1` while `package.json` at `0.1.1`). Opened `#45`, branch `chore/sync-package-lock-version`, applied the two-line sync, merged via PR `#46`.
**Result:** `#45` closed. Stash list empty.

### `2026-04-18` — `#43`: Backend CORS + frontend error surfacing
**Request:** Fix First-Run-Wizard not appearing despite missing `config.json`.
**Done:** Root cause was missing CORS middleware — `http://localhost:5173` → `http://localhost:8000` is cross-origin, so the browser blocked `/setup/status` and the frontend's silent catch in `App.svelte` hid the failure behind the main UI. Added `CORSMiddleware` in `app.py` with allow-list for Vite dev (`localhost:5173`, `127.0.0.1:5173`) and Tauri WebView (`tauri://localhost`, `http://tauri.localhost`). Removed the silent fallback in `App.svelte`; unreachable backend now renders an explicit error state with a Retry button. `9` new CORS unit tests, `178` unit tests green total.
**Result:** `#43` closed via PR `#44`. Wizard appears again on fresh installs; backend outages are now visible.

### `2026-04-18` — `#41`: Unify client URLs to `localhost`
**Request:** Harmonize mixed usage of `127.0.0.1` and `localhost` in client-facing URLs.
**Done:** Replaced `127.0.0.1` → `localhost` in `README.md`, `docs/dev-testing.md`, `docs/postman/local.postman_environment.json`, `frontend/src/lib/api.ts`. Server bind host in `backend/src/zerobox/__main__.py` intentionally kept as `127.0.0.1` (IPv4 loopback bind address, semantically distinct from a client URL).
**Result:** `#41` closed via PR `#42`.

### `2026-04-17` — `#40`: Move dev-testing.md to docs/
**Request:** Move `dev-testing.md` to the `docs/` folder and commit & push.
**Done:** Relocated `dev-testing.md` from `.local/` (gitignored) to `docs/` on branch `feature/move-dev-testing-to-docs`, merged into `master` via `--no-ff`, pushed to `origin`.
**Result:** `#40` closed with `status:done`. File now tracked as project documentation.

### `2026-04-14` — `#21`, `#27`: Tauri Sidecar + Windows Installer
**Request:** Install Rust, close remaining tickets.
**Done:** Installed Rust `1.94.1` + MSVC Build Tools. `#21`: Tauri `2` Rust project with shell plugin for sidecar management, `cargo check` passes. `#27`: Build scripts (`scripts/build-installer.ps1` + `.sh`) — PyInstaller sidecar + Tauri MSI/NSIS bundler.
**Result:** `#21`, `#27` closed. **All `32` tickets closed.** Roadmap complete.

### `2026-04-14` — `#27`–`#29`: Packaging & Polish (Phase `7`)
**Request:** Close remaining tickets and wrap up.
**Done:** `#28`: Global exception handlers (404/400/500) + frontend toast notification system (`3` tests). `#29`: Comprehensive README with setup guide, architecture, testing, config reference.
**Result:** `#28`, `#29` closed. `175` total tests (`159` unit + `16` BDD).

### `2026-04-14` — `#20`–`#26`: Frontend + `#31` Postman + `#32` Gherkin (Phase `6`)
**Request:** Implement Phase `6` (Frontend), plus Postman collection and Gherkin BDD tests in parallel.
**Done:** `#20`–`#26`: Svelte `5` + Vite + Tailwind CSS `4` + Tauri `2` config (JS-only). `5` views: ReviewTable, CorrectionDialog, RuleProfiles, AuditLog, Settings. API client + TypeScript types. Build succeeds. `#21` (Tauri sidecar) deferred — Rust not installed. `#31`: Postman collection with `20` requests in `5` folders + local environment. `#32`: `16` BDD scenarios across `4` feature files with pytest-bdd.
**Result:** `#20`, `#22`–`#26`, `#31`, `#32` closed. `#21` open (needs Rust). `172` total tests (`156` unit + `16` BDD).

### `2026-04-14` — `#15`–`#19`: API Layer (Phase `5`)
**Request:** Implement Phase `5` — FastAPI routes exposing all backend functionality.
**Done:** `#15`: DI wiring in `dependencies.py` with `lru_cache` factories, app factory updated with router includes (`8` tests). `#16`–`#19` in parallel: Pipeline routes (`4` tests), Proposal routes with in-memory storage + status transitions (`13` tests), Rule profile CRUD routes (`11` tests), Audit log query route (`6` tests). All routes have Pydantic request/response models for OpenAPI docs.
**Result:** `#15`–`#19` closed. Phase `5` complete. `156` total tests green. Full API at `/docs`.

### `2026-04-14` — `#12`–`#14`: File Operations & Pipeline (Phase `4`)
**Request:** Implement Phase `4` — FileManager, Pipeline service, end-to-end audit trail.
**Done:** `#12`: `FileManagerService` with rename/move, `3` conflict strategies, batch processing (`17` tests). `#13` + `#14`: `PipelineService` orchestrating Intake → OCR → Classifier → FileManager with full audit trail at every step, auto-approve mode (`13` tests).
**Result:** `#12`–`#14` closed. Phase `4` complete. `114` total tests green.

### `2026-04-14` — `#7`–`#11`: AI Classification & Rules (Phase `3`)
**Request:** Implement Phase `3` — LLM provider abstraction, Anthropic provider, classifier service, rule engine, rule learning loop.
**Done:** `#7`: `LLMProvider` ABC, registry/factory, `ClassificationResult`/`Proposal`/`UserCorrection` models (`7` tests). `#8`: `AnthropicProvider` with Claude API, JSON prompt/response parsing (`12` tests). `#9`: `ClassifierService` orchestrating provider + rules → `Proposal` (`9` tests). `#10`: `RuleService` with CRUD, JSON profiles, pattern matching, validation (`19` tests). `#11`: `learn_from_correction()` method on `ClassifierService` — user correction → LLM extracts rule → persisted (`6` tests). Parallelized: `#7` + `#10` first, then `#8` + `#9`, then `#11`.
**Result:** `#7`–`#11` closed. Phase `3` complete. `84` total tests green.

### `2026-04-14` — Rename Scanner → Intake (`#30`)
**Request:** Rename "Scanner" module to "Intake" — the old name was misleading (suggested OCR).
**Done:** Renamed directory `scanner/` → `intake/`, `ScannedFile` → `IntakeFile`, `ScannerService` → `IntakeService`, `ScannerConfig` → `IntakeConfig`, audit action `"scanned"` → `"intake_discovered"`. Updated all imports, tests, config, docs (`architecture.md`, `roadmap.md`, `CLAUDE.md`, `MEMORY.md`). All `31` tests green.
**Result:** `#30` closed. Naming consistent across the entire project.

### `2026-04-14` — `#5` & `#6`: Intake + OCR Modules (Phase `2`)
**Request:** Implement Phase `2` (`#5` and `#6` in parallel).
**Done:** `#5`: `intake/models.py` with `IntakeFile` dataclass, `intake/service.py` with `IntakeService` (reads input folder, filters by extension, optional audit logging). `11` unit tests. `#6`: `ocr/models.py` with `OcrResult` dataclass, `ocr/service.py` with `OcrService` (async `ocrmypdf` integration via `to_thread`, sidecar text extraction, graceful failure handling). `10` unit tests. All `31` tests green.
**Result:** `#5` and `#6` closed. Phase `2` complete.

### `2026-04-13` — `#4`: Audit Logging Module
**Anfrage:** `#4` umsetzen.
**Durchgeführt:** `audit/models.py` mit `AuditEntry` Dataclass, `audit/service.py` mit `AuditService` (SQLite). `log()` zum Schreiben, `query()` mit Filtern (action, date range, rule_id, limit). Auto-Erstellung von DB und Verzeichnissen. `10` Unit-Tests, alle grün.
**Ergebnis:** `#4` abgeschlossen und als **Done** geschlossen. Phase `1` komplett.

### `2026-04-13` — `#3`: Credential and Config Templates
**Anfrage:** `#3` umsetzen.
**Durchgeführt:** `backend/.env.example` (Placeholder-Keys) und `backend/config.example.json` (alle Felder mit Defaults) erstellt. `.gitignore` angepasst: `config.json` hinzugefügt, `.env.example` per `!`-Ausnahme whitegelistet.
**Ergebnis:** `#3` abgeschlossen und als **Done** geschlossen.

### `2026-04-13` — `#2`: Configuration Module
**Anfrage:** `#2` umsetzen.
**Durchgeführt:** `backend/zerobox/config.py` erstellt mit `AppConfig` (pydantic-settings), Sektionen `IntakeConfig`, `OcrConfig`, `LLMConfig`, `FileManagerConfig`, `AuditConfig`. Laden aus `config.json` mit Fallback auf Defaults, Secrets aus `.env`. Validierung bei Startup (z.B. ungültiger Provider → `ValidationError`). In App Factory integriert, `/config`-Endpoint hinzugefügt.
**Ergebnis:** `#2` abgeschlossen und als **Done** geschlossen.

### `2026-04-13` — `#1`: Backend Project Scaffolding
**Anfrage:** Phase-`1`-Issues auf Ready setzen, `#1` umsetzen.
**Durchgeführt:** `#1` bis `#4` auf **Ready** gesetzt. `#1` implementiert: `backend/pyproject.toml`, Package-Struktur mit allen `9` Modulverzeichnissen, `app.py` (FastAPI Factory mit `/health`), `__main__.py` (Entry Point), venv eingerichtet, `python -m zerobox` verifiziert.
**Ergebnis:** `#1` abgeschlossen und als **Done** geschlossen. Python `3.14.2` ist auf dem System (statt `3.13` — kompatibel, da `requires-python = ">=3.13"`).

### `2026-04-13` — GitHub Project Sync Check
**Anfrage:** Prüfen, ob das GitHub Project (`https://github.com/users/automatix/projects/1`) mit dem Repo `automatix/zerobox` in Sync ist.
**Durchgeführt:** `gh` CLI lokalisiert (`C:\Program Files\GitHub CLI\gh.exe`), Token-Scopes um `read:project` und `project` erweitert, Project-Inhalt abgefragt.
**Ergebnis:** Repo und Project sind vollständig verknüpft. Alle `29` Issues (`#1` bis `#29`) sind im Project vorhanden.
