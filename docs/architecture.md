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
│   │           │   └── audit.py        # GET /audit/log
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
    "model": "claude-sonnet-4-20250514",
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
| `POST` | `/pipeline/run` | Trigger batch processing |
| `GET` | `/proposals` | List current proposals |
| `PATCH` | `/proposals/{id}` | Approve / correct a proposal |
| `POST` | `/proposals/execute` | Execute approved proposals |
| `GET` | `/rules/profiles` | List rule profiles |
| `POST` | `/rules/profiles/{id}/rules` | Add a rule to a profile |
| `GET` | `/audit/log` | Query audit log |

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
