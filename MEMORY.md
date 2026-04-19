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

### `DD-07` — Config Storage Location (`2026-04-19`)
**Decision:** Hybrid layout. `config.json` and `.env` live in an OS-conventional per-user config directory: `%APPDATA%\zerobox\` on Windows, `~/Library/Application Support/zerobox/` on macOS, `$XDG_CONFIG_HOME/zerobox/` (fallback `~/.config/zerobox/`) on Linux. The env var `ZEROBOX_CONFIG_DIR` overrides for dev/tests. Final fallback: `~/.zerobox/`. Data folders (inbox, archive/output, profiles, audit DB) remain freely configurable via `config.json` — no change there.
**Rationale:** OS standard (Windows Roaming-`AppData`, XDG spec, macOS Application Support). Multi-user friendly. Survives re-installs and updates. No admin rights needed (unlike `Program Files\`). Installer builds never have to write next to the exe. Single source of truth via `zerobox.paths.config_dir` so every consumer — `load_config`, `AppConfig` `.env`-file resolution, the wizard's `/setup/save` + `/setup/status` — sees the same directory. Supersedes the previous `Path.cwd()` (dev) / `Path(sys.executable).parent` (frozen) behaviour, which was fragile and required admin rights in installer builds. Ticket `#80`.

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
- `IDEA-09` — **Model picker assistance** — keep the model field as free text (user remains in control) but enrich it with provider-aware assistance: live-fetch the list of available models from the selected provider (Anthropic `/v1/models`, OpenAI `/v1/models`, Ollama `/api/tags` — where the API key is already known, it scopes the list to what the user actually has access to) and show them as autocomplete suggestions. If the user commits a value that is **not** in the suggestion list, show a subtle inline warning that the model is likely unavailable (wrong name or not accessible with this key). Fall back to a curated static list per provider if the discovery call fails, and optionally surface metadata (context window, approximate cost, capability tags).
- `IDEA-10` — **OCR language chips with autocomplete** — in the OCR step of the First-Run-Wizard, replace the free-text `"deu+eng"` input with a tag/chip input: each selected language renders as a removable chip, and typing offers autocomplete against the list of installed Tesseract languages (discoverable via `tesseract --list-langs`). The final config value is still the `+`-joined Tesseract string. Makes the format self-documenting and avoids typos like `ger` (invalid) vs `deu` (correct).
- `IDEA-11` — **Folder picker in Wizard** — replace the free-text folder inputs (`input_folder`, `output_root`, `profiles_dir`) in the Folders step with a native folder-browse button (Tauri `dialog.open({ directory: true })`). Falls back to the current text input when running in a plain browser (Vite dev without Tauri shell). Reduces typos and makes path selection discoverable.
- `IDEA-12` — **Editable Settings tab** — `frontend/src/views/Settings.svelte` currently renders the live config read-only ("Edit the config file directly to make changes."). Make it editable: per-section forms backed by the same Pydantic schema as `config.json` / the wizard, validation client- and server-side, a `PATCH /config` (or `PUT /setup/save`-equivalent) endpoint to persist, and a clear "save" / "reset" workflow. Cover both `config.json` fields and the secrets in `.env` (with masked input).

---

## Work Log

### `2026-04-19` — `#78`: Release `v0.2.1` (patch — bundle `#68` + `#72` + `#74` + `#75`)
**Request:** Bundle the four post-`v0.2.0` fixes into a patch release following the full documented procedure.
**Done:** Bumped version `0.2.0` → `0.2.1` in all manifests (`backend/pyproject.toml`, `app.py` FastAPI title, frontend `package.json` + lockfile, `Cargo.toml` + `Cargo.lock`, `tauri.conf.json`, `App.svelte` header). Tag `v0.2.1` created and pushed. Installer build via `scripts/build-installer.ps1` produced MSI + NSIS; both attached to the GitHub Release. Release notes consolidated `#68`, `#72`, `#74`, `#75`.
**Result:** `#78` closed via PR `#79`. Release: https://github.com/automatix/zerobox/releases/tag/v0.2.1

### `2026-04-19` — `#75`: Expand `~` in all path fields
**Request:** Bug report — wizard creates a literal `~` directory in the project root because the `~` in user-entered paths is not expanded.
**Done:** Diagnosed: `setup.py:save_config` called `Path(folder).mkdir()` without `.expanduser()`, and `config.py` only expanded `profiles_dir` (not `intake.input_folder`, `filemanager.output_root`, `audit.db_path`, or the optional `OcrConfig.tesseract_path` / `ghostscript_path`). Added `field_validator(mode="before")` to every `Path` field via a shared `_expand` helper; `setup.save_config` now `.expanduser()`s before `mkdir`. Cleaned up the leftover `backend/~/` tree. `8` new unit tests, `194` total green. Live verified.
**Result:** `#75` closed via PR `#76`.

### `2026-04-19` — `#74`: Mask API keys in `/config` via `SecretStr`
**Request:** Security finding from `#72` — `/config` exposes raw API keys after the cache invalidation made the in-memory `.env` values visible.
**Done:** Switched `AppConfig.{anthropic_api_key, openai_api_key}` from `str` to `SecretStr`. `model_dump()` now serializes them as `'**********'`; `repr()` and `str()` are masked too. No consumer updates needed — the fields were never read by any code; the Anthropic provider reads `ANTHROPIC_API_KEY` directly from `os.environ`. `4` new unit tests, `198` total green. Live verified — `/config` returns `**********` (was a real `sk-ant-…`).
**Result:** `#74` closed via PR `#77`. Recommendation chosen: `SecretStr` over `model_dump(exclude=…)` because it is default-safe at the type level (every future endpoint inherits the masking), protects against repr/log/stack-trace leaks, and the consumer-update cost was zero.

### `2026-04-19` — `#72`: Wizard-saved settings invisible in Settings tab (stale config cache)
**Request:** Bug report — values entered in the First-Run-Wizard didn't show up under Settings, only defaults were displayed.
**Done:** Diagnosed: `/config` returned the closure-captured `AppConfig` from `create_app()`, and `dependencies.get_config()` plus all downstream service getters were `@lru_cache`'d — so the wizard's `config.json` write was on disk but the running backend kept serving startup defaults (uvicorn `--reload` only watches `.py`). Added `reload_config()` helper in `dependencies.py` that clears every cached getter; `setup.save_config` calls it after writing `config.json` + `.env`; `/config` delegates to the (now invalidatable) cached getter. `3` new unit tests, `186` total green. Live-verified against the running dev backend.
**Result:** `#72` closed via PR `#73`. Settings now reflects wizard input; pipeline services pick up new config without process restart. Side-finding: `/config` exposes API keys in cleartext — tracked separately in `#74`.

### `2026-04-19` — `#70`: Untrack `.claude/settings.local.json`
**Request:** Stop the recurring auto-appends to `settings.local.json` from blocking `gh pr merge`'s post-merge auto-pull.
**Done:** `git rm --cached .claude/settings.local.json` (file stays on disk) and added the path to `.gitignore`. Project-level shared permissions remain in `.claude/settings.json`; the `.local` variant is by convention machine-specific.
**Result:** `#70` closed via PR `#71`. Auto-pull on the merge worked cleanly for the first time in this batch.

### `2026-04-19` — `#68`: Detect Tesseract/Ghostscript at well-known Windows paths
**Request:** OCR Requirements check kept reporting `Not found` even after the user installed Tesseract (UB-Mannheim) and Ghostscript (GPL) — both installers leave the binaries under `C:\Program Files\…` without updating `PATH`.
**Done:** Added a third fallback step to `_find_executable` in `backend/src/zerobox/api/routes/setup.py`: scan a list of well-known install-path globs after `shutil.which()` misses. Globs cover `C:\Program Files\Tesseract-OCR\tesseract.exe` (+ `(x86)`) and `C:\Program Files\gs\gs*\bin\gswin64c.exe` (+ `(x86)`/`gswin32c`). `5` new unit tests; `183` total green. Verified live against the running dev backend — `/setup/status` now reports both as available with correct paths without `PATH` changes.
**Result:** `#68` closed via PR `#69`. Fix matches `DD-06`'s zero-setup goal.

### `2026-04-19` — `#65` + `#66`: Catch up `v0.2.0` release artifacts and codify deviation-transparency rule
**Request:** (a) Run the missed steps `3`–`4` of the documented release process for `v0.2.0` (build installers + attach to release). (b) Codify a new rule: any deviation from a documented instruction must be explicit and visible, ideally asked about first.
**Done:** `#65` — Ran `scripts/build-installer.ps1` (after correcting `pwsh` → `powershell` since PowerShell Core is not installed). PyInstaller built `zerobox-backend-x86_64-pc-windows-msvc.exe`, then `npm run tauri build` produced `Zerobox_0.2.0_x64_en-US.msi` (MSI) and `Zerobox_0.2.0_x64-setup.exe` (NSIS). Both uploaded to the existing `v0.2.0` GitHub Release; release notes updated. `#66` — Added a deviation-transparency paragraph to the `Interaction` section of project `CLAUDE.md`, mirrored in the user's global `CLAUDE.md` and in `feedback_make_deviations_explicit.md` in the session auto-memory.
**Result:** `#65` and `#66` closed via PRs `#67` (`#66`) and direct release work (`#65`). Release `v0.2.0` is now complete with installer artifacts.

### `2026-04-18` — `#62`: Bump version to `0.2.0` + GitHub Release
**Request:** Align/catch up versioning across all manifests after the session's accumulated work.
**Done:** Minor bump `0.1.1` → `0.2.0` in `backend/pyproject.toml`, `backend/src/zerobox/app.py` (FastAPI title), `frontend/package.json` + `package-lock.json`, `frontend/src-tauri/{Cargo.toml, Cargo.lock, tauri.conf.json}`, and the `App.svelte` header display. Annotated tag `v0.2.0` created and pushed. GitHub Release published with collated highlights. Installer artifacts not attached — can be built locally via `scripts/build-installer.ps1` and uploaded later.
**Result:** `#62` closed via PR `#64`. Release: https://github.com/automatix/zerobox/releases/tag/v0.2.0

### `2026-04-18` — `#61`: Gitignore `docs/keys.md` and `.claude/worktrees/*`
**Request:** Protect accidental commit of the real API key in `docs/keys.md` and stop tracking background-agent worktree contents.
**Done:** Added both patterns to `.gitignore`; verified via `git check-ignore -v`. Existing `.local/*` pattern served as the template.
**Result:** `#61` closed via PR `#63`.

### `2026-04-18` — `#59`: Gate Wizard OCR step on requirement status
**Request:** In the Wizard's OCR step, list all requirements with red/green dots, add a `Check requirements` button, and disable the `Next` button until all requirements are satisfied.
**Done:** `SetupWizard.svelte` — promoted OCR dependency status from a one-shot `{#await}` to reactive state (`depStatus`, `depLoading`, `depError`); added a `Check requirements` button that re-fetches `/setup/status`; added derived `ocrRequirementsMet` and `nextDisabled` flags that disable `Next` on the OCR step until Tesseract **and** Ghostscript are found, with amber helper text and tooltip explaining why. Auto-check on first entry to the OCR step. Frontend build green.
**Result:** `#59` closed via PR `#60`.

### `2026-04-18` — `#56`: Codify "implement, don't just file" interaction rule
**Request:** Remember the lesson that `"Mach beides. Gerne parallel."` defaults to implementation, both at project and global scope.
**Done:** Added an `Interaction` section to the project `CLAUDE.md`. Mirrored the rule in the user's global `CLAUDE.md` and added a `feedback_implement_when_parallel.md` entry to the session auto-memory (both outside this repo).
**Result:** `#56` closed via PR `#58`.

### `2026-04-18` — `#52`: Document dev-vs-installer context detection options (docs only)
**Request:** Capture the architectural considerations around detecting dev vs. installer runtime context in docs and in the ticket; implementation deferred.
**Done:** Extended the body of issue `#52` with three candidate approaches (backend signal via `/setup/status`, Tauri compile-time flag, bundled-binary heuristic) incl. trade-offs and current leaning (Option `1`). Added a new `Open Architecture Questions` section to `docs/architecture.md` mirroring the decision matrix. Ticket `#52` stays open (`status:ready`) pending the final decision after user-testing feedback on `#51`.
**Result:** Docs landed via PR `#57`. Implementation of `#52` deferred per user request.

### `2026-04-18` — `#53`: Restructure `dev-testing.md`
**Request:** The "Full desktop mode", "Testing endpoints", and "Resetting the wizard" subsections were nested under "Running Zerobox in Dev Mode" and read as continuation steps, not alternatives. Fix the structure.
**Done:** Promoted the three misplaced `###` subsections to top-level `##` sections in `docs/dev-testing.md`. Heading-level change only, content untouched. Implemented via background agent in an isolated worktree.
**Result:** `#53` closed via PR `#54`.

### `2026-04-18` — `#51`: Correct misleading OCR dependency message
**Request:** The wizard's OCR step showed "Missing dependencies can still be installed later. The app will work for non-OCR features." — factually wrong (OCR is `FR-02`, core) and contradicts `DD-06` (installer bundles deps). Short-term copy fix.
**Done:** Replaced the text in `SetupWizard.svelte:289-293` with a clear warning that OCR is required and pointing to the `Prerequisites` section in `README.md`. Amber styling preserved. Implemented via background agent in an isolated worktree; frontend build verified. Broader dev-vs-installer context handling tracked separately as `#52`.
**Result:** `#51` closed via PR `#55`.

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
