# Zerobox — Roadmap

> Last updated: `2026-04-14`

---

## Phases

### Phase `1` — Foundation

> Project scaffolding, configuration, and cross-cutting concerns.

| Ticket | Requirement | Description |
|---|---|---|
| `#1` | — | Backend project scaffolding (Python `3.13`, `pyproject.toml`, package structure) |
| `#2` | `FR-07` | Configuration module (`config.py`, `pydantic-settings`, `.env`, defaults) |
| `#3` | `NFR-02` | Credential templates (`.env.example`, `config.example.json`) |
| `#4` | `FR-06` | Audit logging module (SQLite, `AuditEntry` model, query interface) |

**Exit criteria:** `python -m zerobox` starts, loads config from `config.json` / `.env`, and audit logger writes + queries entries.

---

### Phase `2` — File Ingestion & OCR

> The first two pipeline stages: reading files and extracting text.

| Ticket | Requirement | Description |
|---|---|---|
| `#5` | `FR-01` | Intake module (read input folder, filter by file type, yield `IntakeFile`) |
| `#6` | `FR-02` | OCR module (`ocrmypdf` integration, text extraction, `OcrResult` model) |

**Exit criteria:** Place test files in inbox → Intake picks them up → OCR produces searchable PDFs with extracted text. All actions audit-logged.

---

### Phase `3` — AI Classification & Rules

> The intelligence layer: LLM-based classification and the learning loop.

| Ticket | Requirement | Description |
|---|---|---|
| `#7` | `FR-08` | LLM provider abstraction (`LLMProvider` interface, registry, factory) |
| `#8` | `FR-08` | Anthropic provider implementation (Claude API) |
| `#9` | `FR-03` | Classifier service (orchestrates provider + rules → `Proposal`) |
| `#10` | `FR-05` | Rule engine (JSON profiles, CRUD, JSON Schema validation) |
| `#11` | `FR-05` | Rule learning loop (user correction → `extract_rule` → save to profile) |

**Exit criteria:** OCR text → Classifier → correct `Proposal` with name + folder. User corrections generate new rules. Rules improve subsequent classifications. Provider is swappable via config.

---

### Phase `4` — File Operations & Pipeline

> Connecting all backend modules into the end-to-end pipeline.

| Ticket | Requirement | Description |
|---|---|---|
| `#12` | `FR-01` | FileManager module (rename, move, conflict handling, rollback support) |
| `#13` | `FR-01` | Pipeline service (orchestrates Intake → OCR → Classifier → FileManager) |
| `#14` | `NFR-04` | End-to-end audit trail (every pipeline step logged with rule references) |

**Exit criteria:** `POST /pipeline/run` processes all inbox files through the full pipeline. `POST /proposals/execute` moves approved files. Complete audit trail queryable.

---

### Phase `5` — API Layer

> FastAPI routes exposing all backend functionality.

| Ticket | Requirement | Description |
|---|---|---|
| `#15` | — | FastAPI app factory + dependency injection wiring (`dependencies.py`) |
| `#16` | — | Pipeline routes (`/pipeline/run`, `/pipeline/status`) |
| `#17` | `FR-04` | Proposal routes (`/proposals`, `/proposals/{id}`, `/proposals/execute`) |
| `#18` | `FR-05` | Rule routes (`/rules/profiles` CRUD) |
| `#19` | `FR-06` | Audit routes (`/audit/log` with filtering) |

**Exit criteria:** Full API functional and documented via auto-generated OpenAPI spec at `/docs`.

---

### Phase `6` — Frontend

> Tauri desktop shell with Svelte UI.

| Ticket | Requirement | Description |
|---|---|---|
| `#20` | — | Frontend project scaffolding (Tauri `2` + Svelte `5` + Tailwind CSS `4`) |
| `#21` | — | Tauri sidecar setup (launch + manage Python backend process) |
| `#22` | `FR-04` | Review table view (proposals list, approve/reject/correct actions) |
| `#23` | `FR-04` | Correction dialog (edit proposed name/folder, feeds into rule learning) |
| `#24` | `FR-05` | Rule profile management view (list, edit, import/export profiles) |
| `#25` | `FR-06` | Audit log view (filterable table of all actions) |
| `#26` | `FR-07` | Settings view (configure paths, LLM provider, OCR language) |

**Exit criteria:** Desktop app launches, triggers pipeline, shows review table, user can approve/correct, files are moved. Full UI workflow.

---

### Phase `7` — Packaging & Polish

> Distribution-ready desktop app.

| Ticket | Requirement | Description |
|---|---|---|
| `#27` | `NFR-03` | Windows installer (Tauri bundler, `.msi` / `.exe`) |
| `#28` | — | Error handling & user feedback (toast notifications, progress indicators) |
| `#29` | — | README with setup instructions, screenshots, getting started guide |

**Exit criteria:** User downloads installer, runs setup, configures API key, processes first batch of scans.

---

## Dependency Graph

```
Phase 1 (Foundation)
  │
  ├──> Phase 2 (Intake + OCR)
  │       │
  │       └──> Phase 3 (Classifier + Rules)
  │               │
  │               └──> Phase 4 (FileManager + Pipeline)
  │                       │
  │                       └──> Phase 5 (API)
  │                               │
  │                               └──> Phase 6 (Frontend)
  │                                       │
  │                                       └──> Phase 7 (Packaging)
  │
  └──> Phase 5 can start partially in parallel with Phase 3/4
       (API scaffolding + DI wiring doesn't depend on module internals)
```
