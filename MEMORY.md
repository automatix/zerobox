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

### `DD-06` — Installer Bundling Strategy (`2026-04-13`) — **partially superseded by `DD-10`**
**Decision:** The Windows installer bundles all runtime dependencies (Python, Tesseract, Ghostscript) so the end user has zero prerequisites to install manually.
**Rationale:** Minimum effort for the end user. Trade-off: larger installer (~`200`–`300` MB), but zero-setup experience. Python backend will be packaged as standalone executable (via PyInstaller or cx_Freeze). Tesseract and Ghostscript are bundled alongside. Only user-provided requirement: an API key (Claude/OpenAI) unless using a local LLM.
**Update (`2026-06-25`):** The Tesseract/Ghostscript bundling part was **never implemented** (`resources/` shipped empty) and is now **dropped** — see `DD-10`. The PyInstaller backend + Tauri shell remain bundled; the OCR tools become documented prerequisites.

### `DD-07` — Config Storage Location (`2026-04-19`)
**Decision:** Hybrid layout. `config.json` and `.env` live in an OS-conventional per-user config directory: `%APPDATA%\zerobox\` on Windows, `~/Library/Application Support/zerobox/` on macOS, `$XDG_CONFIG_HOME/zerobox/` (fallback `~/.config/zerobox/`) on Linux. The env var `ZEROBOX_CONFIG_DIR` overrides for dev/tests. Final fallback: `~/.zerobox/`. Data folders (inbox, archive/output, profiles, audit DB) remain freely configurable via `config.json` — no change there.
**Rationale:** OS standard (Windows Roaming-`AppData`, XDG spec, macOS Application Support). Multi-user friendly. Survives re-installs and updates. No admin rights needed (unlike `Program Files\`). Installer builds never have to write next to the exe. Single source of truth via `zerobox.paths.config_dir` so every consumer — `load_config`, `AppConfig` `.env`-file resolution, the wizard's `/setup/save` + `/setup/status` — sees the same directory. Supersedes the previous `Path.cwd()` (dev) / `Path(sys.executable).parent` (frozen) behaviour, which was fragile and required admin rights in installer builds. Ticket `#80`.

### `DD-08` — Resource ID Handling on Create (`2026-04-19`)
**Decision:** `POST /rules/profiles` and `POST /rules/profiles/{id}/rules` accept `id` **optionally** in the request body. When omitted, the server generates one (slugified `name` for profiles, short `uuid4` for rules). Explicit ids in the body are honoured. We do **not** introduce a separate `PUT /rules/profiles/{id}` upsert endpoint at this time.
**Pros:**
- One endpoint covers both the common "let the server name it" case and the rarer "I have my own id" case (imports, backups, scripted profile management, idempotency on retry).
- Minimal surface area: one route per resource collection instead of two (`POST` + `PUT`).
- Backwards-compatible — existing callers that send an `id` keep working unchanged.
- Matches current frontend usage with no client changes required.
**Cons:**
- Not strict REST. By convention `POST /collection` lets the server assign the id; client-supplied ids belong on `PUT /collection/{id}` (idempotent upsert with id in URL path). Mixing both shapes on `POST` blurs the contract.
- Schema is more permissive: clients have to know "id is optional but accepted", which is harder to discover than two endpoints with separate purposes.
- Conflict semantics are split: explicit-id path returns `409 Conflict`, slug-generated path silently dedupes with `-2` suffix. A single endpoint with two behaviours.
- Postpones the cleaner design instead of making it; technical debt.
**When to revisit:** When we add bulk import / backup-restore, when client-side offline mode (`IDEA-01` / `IDEA-04`) actually lands, or when we externalise the API beyond the in-app frontend. Tracked in `IDEA-14`.
**Tickets:** `#86` (the original 422 fix that produced this state), `IDEA-14` (proposal to revisit).

### `DD-09` — Dev vs Installer Runtime Context (`2026-06-25`) — **SUPERSEDED by `DD-10`**
**Decision:** `GET /setup/status` returns `run_mode: "dev" | "installer"`, derived by `setup.py:_run_mode()`: `ZEROBOX_RUN_MODE` env override first, otherwise `sys.frozen` (`installer` when frozen by PyInstaller, else `dev`). The First-Run-Wizard's OCR step branches on it — `installer` + missing OCR deps → red "Damaged installation" / repair-installer error with `Next` blocked; `dev` + missing → amber install instructions with `Next` allowed (continue, verify later).
**Rationale:** Resolves the open question from `#52`. Chose Option `1` (backend signal) over the Tauri compile-time flag (only works inside the shell, conflates debug-build with dev-mode) and the bundled-binary heuristic (fragile). Sourcing from `sys.frozen` rather than a launcher-set env var avoids coupling the backend to the Tauri launcher and reuses the same signal `_resources_dir()` already trusts. Aligns the wizard with `DD-06` (installer bundles Tesseract + Ghostscript, so a miss on an installed build is a damaged install, not a user task).
**Superseded (`2026-06-25`, `#126`):** Its premise (bundling, per `DD-06`) was dropped by `DD-10`. With nothing bundled the dev/installer distinction is meaningless; `run_mode`/`_run_mode()` were removed and the wizard now behaves uniformly. Shipped only in `v0.6.0`.
**Tickets:** `#52`, superseded by `#126`.

### `DD-10` — OCR Tools Are Prerequisites, Not Bundled (`2026-06-25`)
**Decision:** zerobox does **not** bundle Tesseract or Ghostscript. They are documented user-installed prerequisites (checked by the wizard via `/setup/status`). The PyInstaller backend + Tauri shell remain bundled.
**Rationale:** **Ghostscript is AGPL-3.0** — redistributing it in the installer would impose AGPL obligations on the distributed product (project owner's decision to avoid). Tesseract (Apache-2.0) is left as a prerequisite too for a consistent, honest story. Revises `DD-06` (bundling, whose OCR-tool part was never implemented — `resources/` was empty) and supersedes `DD-09`/`#52` (the dev-vs-installer split assumed bundling). The wizard's OCR step now shows honest install instructions + a docs link when tools are missing, in all distributions, and never blocks `Next`.
**Installer assistance (`#132`):** "Not bundled" ≠ "no install help." The **NSIS `.exe`** installer (`nsis/hooks.nsh`) detects missing Tesseract/Ghostscript and offers to download + install them (system-wide or portable) from upstream **on the user's machine** — no redistribution, so `DD-10` holds. The **`.msi`** has no such hook (replicating it in MSI is not advisable — needs a WiX Burn bootstrapper Tauri doesn't produce). The `.exe` is the **recommended** installer; the `.msi` targets managed/enterprise deployment.
**Tickets:** `#126`, `#132` (installer recommendation docs).

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
- `IDEA-13` — **Ship documentation with the release** — bundle both end-user docs (`README.md`) and technical/dev docs (`docs/architecture.md`, `docs/dev-testing.md`, `docs/roadmap.md`, Postman collection) with the installer/release artifacts. Options to explore: (a) static HTML rendered from the Markdown at build time and bundled as Tauri resources, surfaced via an in-app "Help" tab; (b) a `docs.zip` attached alongside the MSI/NSIS on the GitHub Release; (c) both. Keep the single source of truth in the repo's `.md` files; rendering happens at build time.
- `IDEA-14` — **Revisit REST shape of resource creation** — current state (per `DD-08`) is pragmatic: `POST /rules/profiles` accepts an optional `id` in the body and generates one when absent. The strict-REST alternative would be `POST /rules/profiles {name, description}` (server always assigns the id, returned in the response and `Location` header) plus `PUT /rules/profiles/{id} {...}` as an idempotent upsert for the rarer "I want this exact id" case (imports, backups, sync). Decide in the context of: (a) whether bulk import / restore lands (`IDEA-04` rule sharing), (b) whether the API is consumed by anything beyond the in-app frontend, (c) whether client-side offline mode (`IDEA-01`) needs client-generated UUIDs. Apply the same shape to `/rules/profiles/{id}/rules` for consistency. Touches: backend route schemas + handlers, Postman collection, BDD scenarios, frontend API client.

---

## Work Log

### `2026-06-26` — `#134`: Document the Windows installer/uninstaller as a reusable foundation (docs)
**Request:** The user is building a Windows installer for a *separate* Python app (`Receipt Board` — FastAPI BE + HTML/CSS/JS FE, pywebview, PyInstaller `onedir`) and wants a docs deep-dive on zerobox's installer/uninstaller to serve as the product + technical foundation. Confirm whether zerobox has an uninstaller (it does). User decisions: doc lives in `zerobox/docs/`; **document zerobox only** — present Receipt Board options neutrally, no pre-decided installer tech.
**Done:** Added `docs/windows-installer.md` covering process, end-user view (NSIS `.exe` vs MSI), technique (PyInstaller `--onefile --noconsole` + uvicorn hidden imports + target-triple sidecar naming → Tauri bundler → NSIS hooks), problems & fixes (`#120` PS 5.1 stderr, `#68` PATH detection, `#126`/`DD-10` AGPL non-bundling, `#132`/`#133` MSI-vs-NSIS, venv freeze, `DD-07` per-user state), decisions table, uninstaller section (Tauri-generated + `NSIS_HOOK_POSTUNINSTALL` data-wipe; `dev_uninstall.py` disambiguated as dev-only), and a generality matrix (🟦 general / 🟨 Python / 🟥 zerobox). Closing `§9` bridges to Receipt Board: stack comparison, what transfers/adapts/doesn't, neutral options table (standalone NSIS / Inno Setup / WiX-MSI / adopt Tauri), pre-flight checklist. Cross-linked from `docs/dev-testing.md`.
**Result:** Branch `chore/134-windows-installer-doc`.

### `2026-06-25` — `#132`: Recommend NSIS `.exe` installer; clarify `.msi` (docs)
**Request:** Post-release Q&A surfaced that the NSIS `.exe` installer already offers to download+install Tesseract/Ghostscript (`nsis/hooks.nsh`), while the `.msi` does not — and the `DD-10` docs read as purely manual. User chose to recommend the `.exe` rather than retrofit the MSI (MSI can't do interactive download/nested installs cleanly; would need a WiX Burn bootstrapper Tauri doesn't generate).
**Done:** Docs-only. `README.md` install section now recommends the `.exe` (offers OCR-tool install) and frames the `.msi` as a plain managed-deployment installer. `docs/user-guide.md` OCR step notes the `.exe` may have already installed the tools. `docs/architecture.md` + `MEMORY.md` `DD-10` extended with the NSIS install-time download option and the MSI rationale. No code change, no version bump.
**Result:** Branch `docs/installer-recommendation`.

### `2026-06-25` — `#129`: Release `v0.7.0` (minor — honest OCR prerequisites + build-script fix)
**Request:** Finish everything open, then release.
**Done:** Bumped all manifests + lockfiles to `0.7.0` via `release/0.7.0` → merged (PR `#130`). Annotated tag `v0.7.0`. Built MSI + NSIS using the **fixed** `scripts/build-installer.ps1` (end-to-end success under PS 5.1 — verifies `#120`). Published GitHub Release `v0.7.0` (bundles `#126`/`DD-10` + `#120`) with both installers + tag-pinned doc links. Smoke test: backend `/setup/status` honestly reports tool availability and no longer returns `run_mode`; both OCR tools detected via well-known paths; `/health` ok; `241` tests green.
**Result:** `#129` closed. https://github.com/automatix/zerobox/releases/tag/v0.7.0. **All issues closed; no open tickets.**

### `2026-06-25` — `#120`: Make `build-installer.ps1` robust under PowerShell 5.1
**Request:** Finish all open work.
**Done:** Replaced `$ErrorActionPreference="Stop"` (which under PS 5.1 turned harmless native-tool stderr into terminating errors and aborted the build) with `Continue` + explicit `$LASTEXITCODE` checks (`Invoke-Native`); silenced the pip version notice; made the script prefer `backend/.venv` for PyInstaller. Documented the build in `docs/dev-testing.md`. Verified by building `v0.7.0` end-to-end with the script.
**Result:** `#120` closed via PR `#128`.

### `2026-06-25` — `#126`: Abandon OCR bundling — honest prerequisites + wizard (`DD-10`)
**Request:** Finish all open work. Decision on the OCR-bundling rollout blocker: **do not bundle** (Ghostscript is AGPL-3.0).
**Done:** New `DD-10` revises `DD-06` (bundling, never implemented — `resources/` was empty) and supersedes `DD-09`/`#52`: Tesseract + Ghostscript are documented prerequisites. Reverted the `run_mode` mechanism — removed `_run_mode()` + `run_mode` from `SetupStatus`/`/setup/status` (backend), the `TestRunMode` suite, `api.ts`, and the dev/installer branch in `SetupWizard.svelte`. Wizard now shows one honest "OCR tools required (not bundled)" notice with a docs link when tools are missing, and never blocks `Next`. Docs updated: `architecture.md` (`DD-10` section), `README.md` (install + bundling note), `docs/user-guide.md` (OCR step), `docs/dev-testing.md`. Tests green, `svelte-check` clean.
**Result:** Branch `feature/126-honest-ocr-prerequisites`. Net effect of `#52` + `#126`: OCR tools are explicit prerequisites with an honest wizard.

### `2026-06-25` — `#121`: Release `v0.6.0` (minor — dev-vs-installer wizard context)
**Request:** Cut `v0.6.0` bundling `#52` (second of the two agreed releases).
**Done:** Bumped all manifests + lockfiles (`pyproject.toml`, `package.json`, `package-lock.json`, `Cargo.toml`, `Cargo.lock`, `tauri.conf.json`) to `0.6.0` via `release/0.6.0` → merged to `master` (PR `#122`). Annotated tag `v0.6.0`. Built MSI + NSIS (manual build sequence — see `#120`), published GitHub Release `v0.6.0` with both installers + tag-pinned doc links.
**Result:** `#121` closed. https://github.com/automatix/zerobox/releases/tag/v0.6.0

### `2026-06-25` — `#118`: Publish the dangling `v0.5.1` GitHub release
**Request:** The `v0.5.1` tag existed but had no GitHub release / installers (incomplete per the release procedure). Publish it.
**Done:** Built MSI + NSIS from `master` (provenance noted: chore/docs commits ahead of the tag; Node `25`/npm `11`, no `npm install` so lockfile untouched). Created GitHub Release `v0.5.1` (ref = existing tag) with both installers + tag-pinned doc links.
**Result:** `#118` closed. https://github.com/automatix/zerobox/releases/tag/v0.5.1. Discovered the build script breaks under PowerShell 5.1 on native-tool stderr → filed `#120` (bugfix, not yet implemented).

### `2026-06-25` — `#52`: Distinguish dev vs installer context in wizard dependency checks
**Request:** Rollout-readiness review → implement `#52` (and publish the dangling `v0.5.1` release) in parallel.
**Done:** Resolved `#52` per `DD-09`. Backend: `setup.py:_run_mode()` returns `"dev"`/`"installer"` (env override `ZEROBOX_RUN_MODE`, else `sys.frozen`); added `run_mode` to the `SetupStatus` model + `/setup/status` response. Frontend (`SetupWizard.svelte`): OCR step now branches — `installer` + missing deps shows a red "Damaged installation" / repair-installer error with `Next` blocked; `dev` + missing shows amber install instructions with `Next` allowed (continue, verify later). `api.ts` type extended. Docs: `architecture.md` "Open Architecture Questions" → "Resolved Architecture Decisions"; `DD-09` added to `MEMORY.md`; `dev-testing.md` documents `run_mode` + the `ZEROBOX_RUN_MODE` override. Tests: `6` new backend tests (`TestRunMode`), full suite `247` green; frontend `svelte-check` clean. No Postman/Gherkin change (no `/setup/status` example in the collection).
**Result:** Branch `feature/52-dev-installer-wizard-context`. Feeds into the `v0.6.0` release.

### `2026-04-19` — `#116`: Document `chore/` branch prefix in `CLAUDE.md`
**Request:** The repo has been using `chore/` for infra / tooling / lockfile branches (`chore/100-…`, `chore/114-…`), but `CLAUDE.md`'s **Tickets** section only lists `feature/bugfix/hotfix/release`. Legitimise `chore/` and explain the semantics.
**Done:** Rewrote the branch-prefix paragraph in `CLAUDE.md` as a table with one row per prefix, each pointing at *why* a change happens rather than *what* files it touches. New row: **`chore/<description>`** — "Housekeeping — tooling, build config, CI, lockfile / dependency refreshes, internal docs, metadata. No behaviour change, no defect fixed, no feature added." Aligned with the Conventional Commits / Angular commit-type tradition.
**Result:** `#116` in progress via branch `chore/116-document-chore-branch-prefix` (dogfooding the new prefix — this commit itself is a chore: a meta-doc update with no code-behaviour impact).

### `2026-04-19` — `#114`: Regenerate `frontend/package-lock.json` under pinned `npm@10.9.2` (follow-up to `#112`)
**Request:** After `#112` / PR `#113` pinned the tooling but deferred the lockfile regeneration, open a follow-up ticket and implement it in the same session.
**Done:** Installed Corepack globally (`npm install -g corepack` — Node `25.5.0` on this machine ships without it, as documented in `#112`'s `dev-testing.md` update). `corepack enable` silently no-op'd on Windows without admin shims, but `corepack install` + `corepack npm …` as a wrapper worked fine. Wiped `frontend/package-lock.json` + `frontend/node_modules/`, ran `corepack npm install` → the pinned `npm@10.9.2` fetched all deps and wrote the canonical lockfile. `corepack npm run check` → `0` errors / `0` warnings. `corepack npm run build` → success. Diff: `engines` section added, `libc` fields removed (confirming npm `10.x` doesn't write them — the drift direction is `11.x` writes / `10.x` strips), and one transitive bump `@napi-rs/wasm-runtime` `1.1.3` → `1.1.4` from a fresh resolution. From now on, Corepack-enabled dev machines will produce this exact lockfile, no churn.
**Result:** `#114` in progress via branch `chore/114-regenerate-lockfile-pinned-npm`.

### `2026-04-19` — `#112`: Pin Node.js and npm versions to prevent lockfile drift
**Request:** After the `v0.5.1` release, decide whether the lingering `frontend/package-lock.json` drift needed committing (verdict: discarded — `libc` fields are Linux-only noise that ping-pongs between npm versions). User then asked to file a backlog ticket and implement the canonical pin.
**Done:** Added `"packageManager": "npm@10.9.2"` and `"engines": { "node": ">=20.0.0", "npm": ">=10.0.0" }` to `frontend/package.json`, and created `frontend/.nvmrc` with `20` (major-version alias nvm honours). Extended `docs/dev-testing.md` Prerequisites with a dedicated **Node.js and npm version pinning** subsection explaining the three pins and how to activate Corepack (`corepack enable`, plus `npm install -g corepack && corepack enable` fallback for Node builds that omit Corepack — e.g. the current dev machine's Node `25.5.0`). Terminal `2` one-time setup now leads with `nvm use` + a note that `npm install` honours the pinned version once Corepack is active. `README.md` prereqs updated with a one-line pointer to the pin. `package-lock.json` intentionally *not* regenerated in this PR: this machine's npm (`11.8.0`) rewrites the file away from the pinned format; the canonical lockfile regeneration needs to happen on a machine running the pinned `npm@10.9.2` via Corepack, as a follow-up.
**Result:** `#112` in progress via branch `feature/112-pin-node-npm-versions`.

### `2026-04-19` — `#110`: Release `v0.5.1` (patch — wizard UX polish + `svelte-check` fix)
**Request:** Bundle `#106` + `#108` into a patch release. Tag only — no installer rebuild, no GitHub Release with executables.
**Done:** Manifests bumped `0.5.0` → `0.5.1` across `backend/pyproject.toml`, `backend/src/zerobox/app.py`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/Cargo.lock` (`zerobox` entry), `frontend/src-tauri/tauri.conf.json`, and the header badge in `frontend/src/App.svelte`. Annotated tag `v0.5.1` created on `master` after PR `#111` merged. Deviation from the standard release procedure in `CLAUDE.md`: steps `3` (installer build) and `4` (GitHub Release with installers) were skipped on explicit user direction — both shipped changes are contained to `SetupWizard.svelte` (UX polish + type-safety), no backend binary change.
**Result:** `#110` closed via PR `#111`. Tag: https://github.com/automatix/zerobox/releases/tag/v0.5.1 (tag page only; no Release attached).

### `2026-04-19` — `#108`: Fix pre-existing `svelte-check` type errors in `SetupWizard.svelte`
**Request:** Patch the three `svelte-check` errors that surfaced during `#106` (`depStatus` narrowing + `step === 'ocr'` literal-type comparison).
**Done:** Root cause: Svelte `5`'s `$state()` infers the literal type from its argument, so `let step: Step = $state('provider')` narrows `step` to `'provider'` (left-hand annotation doesn't widen it in `svelte-check`'s view). Switched both problem declarations to the explicit generic form: `let step = $state<Step>('provider')` and `let depStatus = $state<DepStatus | null>(null)`. `npm run check` now reports `0` errors / `0` warnings. No behavioural change.
**Result:** `#108` in progress via branch `bugfix/108-svelte-check-state-narrowing`.

### `2026-04-19` — `#106`: First-Run-Wizard — hide Back button on Step `1` (Provider)
**Request:** On Step `1` of the First-Run-Wizard the Back button in the lower-left footer is superfluous (there is no previous step). Remove it. Patch-level fix.
**Done:** In `frontend/src/views/SetupWizard.svelte`, gated the Back button behind `{#if step !== 'provider'}` with an empty `<div>` placeholder on the else branch so the footer's `justify-between` keeps Next right-aligned. Dropped the now-redundant `disabled={step === 'provider'}` attribute and the associated `disabled:` utility classes since Back only renders when it's actionable. No doc / test updates needed (no reference to the Back button in `docs/user-guide.md`, no frontend tests for the wizard). Noticed 3 pre-existing svelte-check type errors in `SetupWizard.svelte` (`depStatus` narrowing, `step === 'ocr'` comparison) — not introduced by this patch; flagged for a separate ticket.
**Result:** `#106` in progress via branch `bugfix/106-wizard-hide-back-on-step1`.

### `2026-04-19` — `#104`: Document system prerequisites and venv setup in `dev-testing.md`
**Request:** Dev install on a second machine failed with `bash: uvicorn: command not found` after `pip install -e ".[dev]"`. Check whether `uvicorn` is also a system requirement for the normal installation, find any other packages missing from the docs, and fix them. Follow-up: clarify which Terminal `1` steps are one-time vs. every-session.
**Done:** Root cause: `uvicorn` is already a regular dep in `backend/pyproject.toml` (installed by `pip install -e ".[dev]"`), but the `Scripts/` dir wasn't on `PATH` because `dev-testing.md` didn't tell users to create a venv. For normal (installer) installs, `uvicorn` is bundled into the PyInstaller sidecar exe — no system requirement. Added a **Prerequisites** section to `dev-testing.md` (Python `3.13`+, Node.js `20`+, Rust toolchain, Tesseract, Ghostscript) with a note that all Python packages install via `pip`. Split Terminal `1` + Terminal `2` into explicit **One-time setup** and **Every session** blocks (so `python -m venv .venv` / `pip install` / `npm install` aren't repeated every launch), with a shell-specific activation table (Git Bash, PowerShell, `cmd.exe`, bash/zsh). Documented `python -m uvicorn …` as a `PATH`-safe fallback. Switched **Full desktop mode** from `cargo tauri dev` to `npm run tauri -- dev` (uses the `@tauri-apps/cli` devDependency that's already installed by `npm install`), keeping `cargo tauri dev` as an aside for users who've run `cargo install tauri-cli`.
**Result:** `#104` closed via branch `bugfix/104-dev-testing-prerequisites` / PR `#105`.

### `2026-04-19` — `#102`: Release `v0.5.0` (minor — in-app Help tab + release-procedure cleanup)
**Request:** Bundle `#98` + `#100` into `v0.5.0` with installer rebuild.
**Done:** Manifests bumped `0.4.0` → `0.5.0`, `App.svelte` header updated, tag `v0.5.0` pushed. Installer build produced `zerobox_0.5.0_x64_en-US.msi` + `zerobox_0.5.0_x64-setup.exe`, both attached to the GitHub Release. Release notes follow the new template from `#100` — installer artifacts plus a **Documentation** section with tag-pinned `/docs/*.md` + `/README.md` links, no `docs.zip`.
**Result:** `#102` closed via PR `#103`. Release: https://github.com/automatix/zerobox/releases/tag/v0.5.0

### `2026-04-19` — `#100`: Drop `docs.zip` release artifact, link docs from release notes
**Request:** After `#98` made the docs available inside the app, the `docs.zip` artifact introduced by `#92` became redundant. Remove it; use tag-pinned doc links in the release notes where that's actually useful.
**Done:** Deleted `scripts/build-docs-bundle.(ps1|sh)`, cleaned the `docs.zip`/`.docs-bundle-staging/` entries from `.gitignore`, removed the "Docs Bundle (release artifact)" section from `docs/dev-testing.md`, and collapsed `CLAUDE.md`'s versioning steps `4`+`5` back to a single step `4` that uploads only the installer artifacts while embedding a **Documentation** section (tag-pinned `/docs/*.md` + `/README.md` links) in the release notes. `v0.4.0`'s `docs.zip` stays attached to that release as a historical artifact — no retroactive deletion.
**Result:** `#100` closed via PR `#101`.

### `2026-04-19` — `#98`: In-app Help tab with rendered, bundled docs (`IDEA-13` phase 2)
**Request:** "Bring the docs into the application — that was actually what I meant by 'ship with'." Implement formatted, in-app access to the docs.
**Done:** Added a fifth tab `Help` to the main app. Sidebar lists User Guide, README, Architecture, Dev Testing, Roadmap; right pane renders the selected `.md` with `marked` (parser) + `dompurify` (sanitiser). New `frontend/scripts/sync-docs.mjs` copies the repo's `.md` files into `frontend/public/docs/` so Vite bundles them into `dist/` and Tauri into the installer; hooked into `predev` / `prebuild`, plus standalone `npm run sync-docs` and a smoke test `npm run test:sync-docs`. `frontend/public/docs/` is git-ignored (derived artefact). `marked` + `dompurify` added as prod deps. Frontend bundle grew from `~78 KB` to `~143 KB` JS — acceptable for a desktop app. `docs/user-guide.md` ("five tabs", new Help section) and `docs/dev-testing.md` (new In-App Docs Sync section) updated per the keep-current rule. Deliberately did **not** add Vitest / svelte-testing-library — too much new test infra for one component; smoke test guards the build-time sync, which is the most fragile piece.
**Result:** `#98` closed via PR `#99`.

### `2026-04-19` — `#96`: Release `v0.4.0` (minor — docs + process, no installer rebuild)
**Request:** Bump to `0.4.0` for the post-`v0.3.1` docs + script changes (`#90`, `#91`, `#92`); no installer build because the app binary itself didn't change.
**Done:** Manifests bumped, `App.svelte` header updated, tag `v0.4.0` pushed. GitHub Release created with text-only release notes; only artifact attached is `docs.zip` (the new artifact type from `#92`). MSI/NSIS were intentionally omitted — `v0.3.1` installers are functionally equivalent.
**Result:** `#96` closed via PR `#97`. Release: https://github.com/automatix/zerobox/releases/tag/v0.4.0

### `2026-04-19` — `#92`: Ship documentation with the release — `IDEA-13` phase 1
**Request:** Implement `IDEA-13`; keep it scoped and honest about what's phase 1 vs. phase 2.
**Done:** Added `scripts/build-docs-bundle.(ps1|sh)` that zips `README.md` and the user-facing/technical docs under `docs/` (plus `docs/postman/`) into `docs.zip` at the repo root, mirroring the `build-installer` dual-script pattern. Release procedure in `CLAUDE.md` grew a step `4` (build docs bundle) and step `5` uploads `docs.zip` alongside MSI/NSIS. `dev-testing.md` documents the script. `.gitignore` ignores `docs.zip` and the staging dir. Phase `2` (HTML rendering, Tauri resource bundling, in-app Help tab) stays in `IDEA-13` for a future pass.
**Result:** `#92` closed via PR `#95`.

### `2026-04-19` — `#91`: Codify "keep tests and docs current after every change"
**Request:** Add a project- and global-wide rule that every change updates tests and docs in the same PR — no drift.
**Done:** Extended `CLAUDE.md` Interaction with a second paragraph requiring matching test + doc updates per change (listing the docs to consider: `README.md`, user-guide, architecture, dev-testing, roadmap, `MEMORY.md`, Postman, Gherkin). Pure internal refactors still keep tests green but only need doc updates when a reader of the docs would notice a difference. Mirrored in the user's global `CLAUDE.md` and `feedback_keep_tests_and_docs_current.md` in the session auto-memory.
**Result:** `#91` closed via PR `#94`.

### `2026-04-19` — `#90`: Write end-user guide (`docs/user-guide.md`)
**Request:** The repo had no user-facing usage documentation — user was stuck on what to enter in the Rule form. Write a full user manual under `docs/` and link from `README.md`.
**Done:** New `docs/user-guide.md` covering the mental model of the pipeline, the First-Run-Wizard step by step, the Review / Rule Profiles / Audit Log / Settings tabs, Rule field semantics with a concrete example (plus the important note that name/folder templates are LLM guidelines, not Python format strings), typical first-time and ongoing workflows, troubleshooting, and per-platform file locations. `README.md` User Guide section now opens with a link to it.
**Result:** `#90` closed via PR `#93`.

### `2026-04-19` — `#88`: Release `v0.3.1` (patch — bundle `#86`)
**Request:** Ship a patch release for the profile-creation fix.
**Done:** Bumped `0.3.0` → `0.3.1` in all manifests + `App.svelte` header. Tag `v0.3.1` pushed. Installer build produced MSI + NSIS; both attached to the GitHub Release.
**Result:** `#88` closed via PR `#89`. Release: https://github.com/automatix/zerobox/releases/tag/v0.3.1

### `2026-04-19` — `#86`: Rule-Profile creation returns `422`
**Request:** Bug report — creating a profile in the UI fails with `API error: 422` (screenshot showed `Dummy` / `Dummy profile` input).
**Done:** Root cause: `CreateProfileBody.id` (and `AddRuleBody.id`) were required, but the frontend forms only send `{name, description}` / `{patterns, ...}` — pydantic rejected at the schema boundary. Made both ids optional; backend now auto-generates. Profile id = slugified name (lowercase, non-alphanum → `-`, collapse, strip, `-2`/`-3`/… on collision, falls back to `uuid4().hex[:8]` when the slug would be empty). Rule id = `uuid4().hex[:8]` deduped against the profile. `add_rule` now `get_profile`s before generating an id so missing profiles surface as `404`. Explicit ids still honoured. `7` new unit tests; `225` total green. Live `curl` confirmed `201 {"id":"dummy",...}`.
**Result:** `#86` closed via PR `#87`.

### `2026-04-19` — `#84`: Release `v0.3.0` (minor — hybrid config layout + dev-uninstall CLI)
**Request:** Minor release bundling `#80` + `#81`, per full documented procedure, with lowercase `zerobox` brand in user-visible UI.
**Done:** Bumped version `0.2.1` → `0.3.0` in all manifests. Rebranded user-visible strings: FastAPI title, Tauri `productName` + window title, `App.svelte` header, `SetupWizard` header + OCR warning prose (docs/`MEMORY.md` prose intentionally untouched for now). Tag `v0.3.0` pushed. Installer build ran, MSI + NSIS attached to the GitHub Release, release notes consolidated `#80` (hybrid config) and `#81` (dev-uninstall CLI).
**Result:** `#84` closed via PR `#85`. Release: https://github.com/automatix/zerobox/releases/tag/v0.3.0

### `2026-04-19` — `#81`: Dev-uninstall CLI for selective state reset
**Request:** A CLI to wipe zerobox state (config, env, data, audit) selectively or entirely, so the First-Run-Wizard and pipeline can be tested from zero without hand-hunting files.
**Done:** Implementation as a Python module (`backend/src/zerobox/dev_uninstall.py`, runnable via `python -m zerobox.dev_uninstall`) so it reuses `zerobox.paths` and is cross-platform. Thin PowerShell and Bash wrappers in `scripts/` mirror the `build-installer` pattern. Six targets, each selectable individually plus `--all`; interactive mode when no flags; confirmation prompt skippable via `--yes`; honours the paths in `config.json` if present (else falls back to `~/zerobox/{inbox,archive,profiles,audit.db}`). `12` new unit tests cover target resolution, file/dir deletion, all CLI modes, and a description-completeness guard. `218` total tests green. `docs/dev-testing.md` gained a "Dev-Uninstall / Reset" section; "Resetting the wizard" now points at the new tool.
**Result:** `#81` closed via PR `#83`.

### `2026-04-19` — `#80`: Hybrid config layout — OS-conventional per-user dir (`DD-07`)
**Request:** Clean up the config location. Old behaviour (`Path.cwd()` in dev, `Path(sys.executable).parent` in frozen) is fragile and needs admin rights in `Program Files\` installer builds. Decide + implement.
**Done:** Added `DD-07` (hybrid layout): `config.json` + `.env` under `%APPDATA%\zerobox\` (Windows), `~/Library/Application Support/zerobox/` (macOS), `$XDG_CONFIG_HOME/zerobox/` fallback `~/.config/zerobox/` (Linux). `$ZEROBOX_CONFIG_DIR` overrides for dev/tests. Data folders (inbox, archive/output, profiles, audit DB) remain user-configurable. New `backend/src/zerobox/paths.py` centralizes resolution (`config_dir`, `config_file`, `env_file`). `load_config` now reads from `config_file()` and passes `_env_file` into `AppConfig`. `setup.py:_config_dir()` delegates; the `sys.frozen` special case is gone. `save_config` `mkdir(parents=True)`s the config dir before writing. `8` new tests per platform branch + env override; existing fixtures switched from `monkeypatch.chdir` to `ZEROBOX_CONFIG_DIR`. `206` total tests green. `docs/architecture.md` Configuration section documents the new layout.
**Result:** `#80` closed via PR `#82`.

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
