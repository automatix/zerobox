# Zerobox — Architecture

> Living document. Updated with every architectural change.
> Last updated: `2026-04-15`

---

## Overview

Zerobox is an AI-powered scan processing app for Windows `11`. It automates the workflow:

```
Scan intake → OCR → AI classification → User review → File operations
```

The system learns from user corrections through a rule engine backed by JSON profiles.

---

## Directory Structure

```
zerobox/
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   └── zerobox/
│   │       ├── __init__.py
│   │       ├── app.py                  # FastAPI app factory
│   │       ├── config.py               # Pydantic settings (all config + defaults)
│   │       ├── updates.py              # In-app update check (GitHub Releases)
│   │       │
│   │       ├── intake/                 # Module: file discovery
│   │       │   ├── __init__.py
│   │       │   ├── service.py
│   │       │   └── models.py           # IntakeFile
│   │       │
│   │       ├── ocr/                    # Module: OCR processing
│   │       │   ├── __init__.py
│   │       │   ├── service.py
│   │       │   └── models.py           # OcrResult
│   │       │
│   │       ├── classifier/             # Module: AI-based classification
│   │       │   ├── __init__.py
│   │       │   ├── service.py
│   │       │   ├── models.py           # ClassificationResult, Proposal
│   │       │   └── providers/          # LLM provider abstraction
│   │       │       ├── __init__.py     # Provider registry + factory
│   │       │       ├── base.py         # Abstract LLMProvider interface
│   │       │       ├── anthropic.py    # Claude implementation
│   │       │       ├── openai.py       # OpenAI implementation
│   │       │       └── ollama.py       # Ollama (local) implementation
│   │       │
│   │       ├── rules/                  # Module: rule engine
│   │       │   ├── __init__.py
│   │       │   ├── service.py
│   │       │   ├── models.py           # RuleProfile, Rule
│   │       │   └── schema.json         # JSON Schema for validation
│   │       │
│   │       ├── filemanager/            # Module: file operations
│   │       │   ├── __init__.py
│   │       │   └── service.py
│   │       │
│   │       ├── audit/                  # Module: audit logging
│   │       │   ├── __init__.py
│   │       │   ├── service.py
│   │       │   └── models.py           # AuditEntry
│   │       │
│   │       ├── pipeline/               # Module: orchestration
│   │       │   ├── __init__.py
│   │       │   └── service.py
│   │       │
│   │       └── api/                    # Module: HTTP interface
│   │           ├── __init__.py
│   │           ├── routes/
│   │           │   ├── pipeline.py     # POST /pipeline/run, GET /pipeline/status
│   │           │   ├── proposals.py    # GET/PATCH /proposals
│   │           │   ├── rules.py        # CRUD /rules/profiles
│   │           │   ├── audit.py        # GET /audit/log
│   │           │   └── update.py       # GET /update/check
│   │           └── dependencies.py     # FastAPI dependency injection
│   │
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   │
│   ├── .env.example
│   └── config.example.json
│
├── frontend/                       # Tauri 2 + Svelte 5 app
│   ├── src/                        # Svelte components
│   ├── src-tauri/                  # Tauri Rust shell + sidecar config
│   ├── package.json
│   └── tailwind.config.js
│
├── profiles/                       # User's rule profiles (JSON)
│   └── .gitkeep
│
├── docs/
│   └── architecture.md             # This file
│
├── CLAUDE.md
├── MEMORY.md
├── README.md
└── .gitignore
```

---

## Modules

| Module | Responsibility | Key Types |
|---|---|---|
| `intake` | Discover files from configurable input folder | `IntakeFile` |
| `ocr` | Extract text via `ocrmypdf` (Tesseract wrapper) | `OcrResult` |
| `classifier` | AI-based naming + filing proposals | `Proposal`, `ClassificationResult` |
| `classifier/providers` | Swappable LLM backends | `LLMProvider` (abstract) |
| `rules` | CRUD for JSON rule profiles | `Rule`, `RuleProfile` |
| `filemanager` | Rename + move with rollback support | — |
| `audit` | SQLite action log | `AuditEntry` |
| `pipeline` | Orchestrates the full workflow | — |
| `updates` | In-app update check against public GitHub Releases | `UpdateInfo` |
| `api` | FastAPI HTTP routes | — |

Each module exposes a `service.py` with its public interface. Modules do not import each other directly — dependencies are injected via constructors.

---

## Data Flow

```
┌──────────┐    ┌──────┐    ┌────────────┐    ┌─────────┐    ┌─────────────┐
│ Intake   │───>│ OCR  │───>│ Classifier │───>│ Review  │───>│ FileManager │
│          │    │      │    │            │    │ (UI)    │    │             │
│ discovers│    │ adds │    │ proposes   │    │ approve │    │ executes    │
│ files    │    │ text │    │ name+path  │    │ correct │    │ rename+move │
└──────────┘    └──────┘    └────────────┘    └─────────┘    └─────────────┘
                                                   │
                                            ┌──────┴──────┐
                                            │ Rule Engine │
                                            │ (learn from │
                                            │ corrections)│
                                            └─────────────┘

All steps ──────────────────────────────────> Audit Logger
```

`1.` **Intake** discovers all supported files from the input folder.
`2.` **OCR** processes each file → searchable PDF + extracted text.
`3.` **Classifier** sends the text + known rules to the configured LLM → receives a `Proposal` (name, folder, confidence).
`4.` **Review UI** shows proposals in a table. User approves or corrects.
`5.` Corrections are fed to the **Rule Engine**, which generates new rules (via the LLM's `extract_rule` method).
`6.` Approved proposals are executed by the **FileManager** (rename + move).
`7.` **Audit Logger** records every action across all steps.

---

## LLM Provider Abstraction

The LLM is swappable via a provider interface (`FR-08`).

### Interface

```python
class LLMProvider(ABC):
    @abstractmethod
    async def classify(
        self,
        text: str,
        rules: list[Rule],
        context: ClassificationContext,
    ) -> ClassificationResult: ...

    @abstractmethod
    async def extract_rule(
        self,
        text: str,
        correction: UserCorrection,
    ) -> Rule: ...
```

### Registry + Factory

```python
_PROVIDERS: dict[str, type[LLMProvider]] = {}

def register(name: str):
    def decorator(cls):
        _PROVIDERS[name] = cls
        return cls
    return decorator

def create_provider(config: LLMConfig) -> LLMProvider:
    return _PROVIDERS[config.provider](config)
```

### Implementations

| Provider | Config key | SDK |
|---|---|---|
| Claude | `"anthropic"` | `anthropic` |
| OpenAI / GPT | `"openai"` | `openai` |
| Ollama (local) | `"ollama"` | HTTP (`httpx`) |

Provider is selected via `config.llm.provider`. Each has its own credentials in `.env`.

---

## Core Data Models

```python
@dataclass
class Proposal:
    id: str
    original_path: Path
    original_name: str
    proposed_name: str
    proposed_folder: Path
    confidence: float              # 0.0–1.0
    matched_rule: str | None       # Rule ID if matched
    status: Literal["pending", "approved", "rejected", "corrected"]

@dataclass
class Rule:
    id: str
    profile_id: str
    patterns: list[str]            # Text patterns to match
    target_name_template: str      # e.g., "{date}_{type}_{sender}"
    target_folder_template: str
    priority: int
    examples: list[str]            # Example texts for LLM context

@dataclass
class AuditEntry:
    timestamp: datetime
    action: str                    # "classified", "approved", "moved", "rule_created", ...
    source: str
    target: str | None
    rule_id: str | None
    details: dict
```

---

## Configuration

### Storage location (`DD-07`)

`config.json` and `.env` live in an OS-conventional per-user directory:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\zerobox\` |
| macOS | `~/Library/Application Support/zerobox/` |
| Linux | `$XDG_CONFIG_HOME/zerobox/` (fallback: `~/.config/zerobox/`) |
| All | `$ZEROBOX_CONFIG_DIR` wins if set (dev / test override) |
| Fallback | `~/.zerobox/` |

Data folders (inbox, archive/output, profiles, audit DB) remain freely configurable via `config.json`'s respective keys.

Implemented in `backend/src/zerobox/paths.py` (`config_dir`, `config_file`, `env_file`). Used by `config.load_config` and `api.routes.setup._config_dir`.

### `config.json` — settings with defaults

```jsonc
{
  "intake": {
    "input_folder": "~/zerobox/inbox",
    "file_types": [".pdf", ".tiff", ".tif", ".png", ".jpg", ".jpeg"]
  },
  "ocr": {
    "language": "deu+eng",
    "deskew": true,
    "optimize": 1
  },
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "temperature": 0.0
  },
  "filemanager": {
    "output_root": "~/zerobox/archive",
    "conflict_strategy": "rename"
  },
  "audit": {
    "db_path": "~/zerobox/audit.db"
  },
  "profiles_dir": "~/zerobox/profiles"
}
```

### `.env` — secrets only

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
```

Templates (`.env.example`, `config.example.json`) are committed; actual files are gitignored.

---

## Dependency Injection

No globals, no singletons. All modules receive dependencies via constructor injection, wired through FastAPI's `Depends()` in `api/dependencies.py`:

```python
def get_config() -> AppConfig: ...
def get_audit(config) -> AuditService: ...
def get_intake(config) -> IntakeService: ...
def get_ocr(config) -> OcrService: ...
def get_provider(config) -> LLMProvider: ...       # factory-based
def get_rules(config) -> RuleService: ...
def get_classifier(provider, rules) -> ClassifierService: ...
def get_pipeline(intake, ocr, classifier, ...) -> PipelineService: ...
```

---

## Frontend ↔ Backend

```
┌────────────────────┐       HTTP (localhost:8000)      ┌──────────────────┐
│   Tauri + Svelte   │ <──────────────────────────────> │  FastAPI Backend │
│   (WebView2)       │                                  │  (Sidecar)       │
└────────────────────┘                                  └──────────────────┘
```

Tauri launches the Python backend as a **sidecar process**. All communication goes through local HTTP.

### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/setup/status` | Check setup completion and dependency status |
| `POST` | `/setup/validate` | Test LLM provider connection |
| `POST` | `/setup/save` | Write config.json and .env from wizard |
| `POST` | `/pipeline/run` | Trigger batch processing |
| `GET` | `/proposals` | List current proposals |
| `PATCH` | `/proposals/{id}` | Approve / correct a proposal |
| `POST` | `/proposals/execute` | Execute approved proposals |
| `GET` | `/rules/profiles` | List rule profiles |
| `POST` | `/rules/profiles/{id}/rules` | Add a rule to a profile |
| `GET` | `/audit/log` | Query audit log |
| `GET` | `/update/check` | Compare running version against the latest GitHub Release |

---

## Tech Stack Summary

| Layer | Technology | Version |
|---|---|---|
| Backend runtime | Python | `3.13` |
| API framework | FastAPI | latest |
| Configuration | pydantic-settings | latest |
| OCR | ocrmypdf (Tesseract) | latest |
| AI (default) | anthropic SDK | latest |
| Audit storage | SQLite (`sqlite3` stdlib) | — |
| Rule storage | JSON + JSON Schema | — |
| Desktop shell | Tauri | `2` |
| UI framework | Svelte | `5` |
| CSS | Tailwind CSS | `4` |

---

## Resolved Architecture Decisions

### OCR tools are user prerequisites, not bundled (`#126`, `DD-10`)

`DD-06` originally called for the installer to bundle all runtime dependencies (Python, Tesseract, Ghostscript) for a zero-setup experience. **`DD-10` revises this:** Tesseract and Ghostscript are **not** bundled — they are documented user-installed prerequisites. The decisive reason is licensing: **Ghostscript is AGPL-3.0**, and redistributing it inside the installer would impose AGPL obligations on the distributed product. (Tesseract is Apache-2.0 and would be safe, but is left as a prerequisite too for a consistent, honest story.) The PyInstaller-packaged backend and the Tauri shell are still bundled.

**Consequence — supersedes `DD-09` / `#52`.** The dev-vs-installer `run_mode` distinction introduced by `#52` assumed bundling (installer → tools always present → a miss means a damaged install). With nothing bundled, the OCR tools can be missing in *any* distribution, so that distinction is meaningless. The `run_mode` field and `_run_mode()` were removed from `/setup/status`. The First-Run-Wizard's OCR step now behaves uniformly:

- **OCR deps missing** → amber "OCR tools required" notice explaining the tools are not bundled, with a link to the Prerequisites docs (README / in-app Help). `Next` is **allowed** — the user may continue and install them later.
- **OCR deps present** → green dots, `Next` enabled.

The backend still locates the tools via `setup.py:_find_executable` (`PATH` → well-known install globs; a portable `resources/` path is still checked first, harmlessly, should anyone choose to drop binaries there).

**Installer assistance (NSIS only).** "Not bundled" does not mean "no help installing." The **NSIS `.exe`** installer's pre-install hook (`frontend/src-tauri/nsis/hooks.nsh`, `NSIS_HOOK_PREINSTALL`) detects missing Tesseract / Ghostscript and offers to download + install them — system-wide, or as a portable copy under `resources/` — from their upstream projects, **on the user's machine**. Nothing is redistributed inside the artifact, so `DD-10` (no AGPL redistribution) still holds. The **`.msi`** (WiX) has no equivalent hook: replicating it is not advisable (Windows Installer disallows interactive UI / nested installs from deferred custom actions; the correct MSI pattern would be a WiX Burn bootstrapper, which Tauri does not generate). The NSIS `.exe` is therefore the **recommended** installer; the `.msi` targets managed / enterprise deployment where the OCR tools are provisioned separately.
