# zerobox User Guide

> Audience: end users running an installed zerobox build.
> Looking for setup-from-source instructions? See `dev-testing.md`.
> Looking for architecture or internals? See `architecture.md`.

## What zerobox does

zerobox turns a folder of scanned documents into a sorted, named archive:

`1.` **Scan intake** — zerobox watches an "inbox" folder for new PDF/image files you've dropped in from your scanner.
`2.` **OCR** — each file is run through Tesseract so the document's text is searchable (and readable by the classifier).
`3.` **AI classification** — a language model (Claude, GPT, or a local Ollama model) reads the text and proposes a filename and target folder based on the rules you've defined.
`4.` **Review** — you see every proposal in a table before anything is moved. Approve the ones that look right; correct the ones that don't.
`5.` **Filing** — approved proposals are renamed and moved into your archive.
`6.` **Learning** — corrections feed back into the rule engine, so the system gets smarter about your document types over time.

Nothing leaves your machine except the OCR text sent to your chosen LLM provider (or, with Ollama, nothing leaves at all).

---

## First-Run Wizard

The wizard appears the first time you open zerobox.

### Step `1` — LLM Provider

Pick which language model classifies your documents:

| Provider | Notes |
|---|---|
| **Anthropic (Claude)** | Requires an API key (`sk-ant-…`). Default `claude-sonnet-4-6`. |
| **OpenAI (GPT)** | Requires an API key (`sk-…`). Default `gpt-4o`. |
| **Ollama (local)** | Runs a model locally; needs `ollama serve` reachable at `http://localhost:11434`. No key. Slower but private. |

**Model name** — the wizard pre-fills a sensible default per provider. Any model id the provider exposes is allowed. To list what's available to your account, see the `Finding valid model names` section of the project `README.md` for the exact API calls.

**Test connection** — pings the provider so you know the key/URL work before continuing.

### Step `2` — Folders

Three paths. `~` expands to your home directory automatically.

| Field | Purpose | Default |
|---|---|---|
| **Input Folder (Inbox)** | Drop your scanned files here. | `~/zerobox/inbox` |
| **Output Folder (Archive)** | Classified files end up here, organised by your rules' folder templates. | `~/zerobox/archive` |
| **Profiles Folder** | Where rule profiles (`.json` files) live. | `~/zerobox/profiles` |

### Step `3` — OCR

- **OCR Language(s)** — Tesseract language codes joined by `+`. Examples: `deu+eng` (German + English), `deu+eng+rus` (also Russian). The languages must be installed in Tesseract.
- **OCR Requirements** — Tesseract and Ghostscript must be installed on your system. The wizard checks both and shows a coloured dot per dependency. If a dot is red, install the missing tool and click **Check requirements** to re-verify. **Next** stays disabled until both are green.

### Step `4` — Summary

Review your settings and click **Finish Setup**. zerobox writes `config.json` and `.env` to the per-user config directory:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\zerobox\` |
| macOS | `~/Library/Application Support/zerobox/` |
| Linux | `$XDG_CONFIG_HOME/zerobox/` (fallback `~/.config/zerobox/`) |

You can override this with the `ZEROBOX_CONFIG_DIR` environment variable before starting zerobox (see `DD-07` in `MEMORY.md`).

---

## Main App

After the wizard, zerobox shows four tabs.

### Review

The central workspace. Each scan in your inbox becomes a row.

| Column | Meaning |
|---|---|
| Original filename | What came out of your scanner |
| Target filename | Proposed name based on rules + LLM classification |
| Target folder | Proposed destination, relative to the archive root |
| Confidence | `0.0`–`1.0`, how sure the classifier is |
| Status | `pending`, `approved`, `rejected`, or `corrected` |

Per-row actions:

- **Approve** — accept the proposal as-is.
- **Reject** — skip this file (it stays in the inbox).
- **Correct** — open a dialog to edit the proposed name and folder. Your correction is fed to the rule engine to improve future classifications.

Toolbar:

- **Run Pipeline** — re-scan the inbox and classify any new files.
- **Execute Approved** — actually perform the rename + move for every approved proposal. Until you click this, nothing has been renamed or moved.

### Rule Profiles

Your classification rules live here. Rules are grouped into **profiles** (e.g. `Personal`, `Work`), each stored as one `.json` file in your Profiles folder.

#### Creating a profile

Click **New Profile**, enter a name (e.g. `Personal`) and an optional description, then **Create**. zerobox derives a machine-readable id from the name (`Personal` → `personal`).

#### Creating a rule

Open a profile and click **+ Add Rule**. Four fields:

| Field | Meaning | Example |
|---|---|---|
| **Patterns** (comma-separated) | Text substrings that must **all** appear in the OCR'd document (case-insensitive) for the rule to match. | `Rechnung, Stadtwerke` |
| **Name template** | Guideline the LLM uses to name the file. Placeholders like `{date}`, `{sender}`, `{type}`, `{invoice_number}` are free-form hints — the LLM fills them based on the document's content. | `{date}_Rechnung_Stadtwerke` |
| **Folder template** | Target folder relative to the archive root. Also a guideline the LLM may refine. | `Finanzen/Rechnungen/Stadtwerke` |
| **Priority** | Integer; when multiple rules match the same document, the higher-priority rule wins. Default `0`. | `10` |

> **Important — templates are LLM hints, not Python format strings.**
> The placeholders inside `{...}` are not a fixed set the system substitutes mechanically. They are guidelines passed to the language model, which fills them by reading the document. You can use any placeholder name that makes sense for your document type — `{date}`, `{customer_number}`, `{quarter}`, `{invoice_number}` — and the LLM decides what to put there.

A complete example for an electricity-bill rule:

| Field | Value |
|---|---|
| Patterns | `Rechnung, Stadtwerke` |
| Name template | `{date}_Rechnung_Stadtwerke` |
| Folder template | `Finanzen/Rechnungen/Stadtwerke` |
| Priority | `10` |

### Audit Log

Every action — file classified, rule matched, file renamed, profile edited, rule learned — is written to a local SQLite database and surfaced here. Filter by action type, rule id, or time range. Use this when a file ended up somewhere unexpected and you want to know *why*.

The database itself defaults to `~/zerobox/audit.db` and can be relocated via `config.json` (`audit.db_path`).

### Settings

Read-only view of the merged configuration (`config.json` + `.env`). API keys are masked (`**********`) for safety. To change a setting, edit the config file directly in your per-user config directory (see Step `4` above) and restart zerobox.

(An in-app editor is tracked in `IDEA-12`.)

---

## Typical Workflow

### First time

`1.` Walk through the Wizard. Point the Inbox at the folder your scanner drops files into.
`2.` Open **Rule Profiles** and create a profile (e.g. `Personal`). Add a few starter rules for your most common document types.
`3.` Drop a handful of scans into the Inbox.
`4.` Open **Review** and click **Run Pipeline**.
`5.` Approve good proposals; correct the off-target ones. Each correction teaches the rule engine.
`6.` Click **Execute Approved** to actually file the approved scans.

### Ongoing

`1.` Scan documents into the Inbox as they arrive.
`2.` Periodically open zerobox, **Run Pipeline**, review, approve, **Execute Approved**.
`3.` Whenever you correct a classification, the system learns. Next time a similar document arrives it should classify itself correctly.

---

## Troubleshooting

**The Wizard reappears every time / settings aren't being saved.**
Check that `config.json` exists in your per-user config dir (`%APPDATA%\zerobox\` on Windows). If not, the wizard's save call failed — check the backend logs.

**OCR Requirements show "Not found" although I installed Tesseract / Ghostscript.**
zerobox checks `PATH` first, then well-known install locations (`C:\Program Files\Tesseract-OCR\tesseract.exe`, `C:\Program Files\gs\gs*\bin\gswin64c.exe`, plus `(x86)` variants). If your install is elsewhere, either move it to a standard location or add its bin directory to `PATH`.

**Classification looks wrong / the LLM ignores my templates.**
Templates are LLM guidelines, not strict formats. Two checks:
- Are your **Patterns** specific enough? Patterns that match too many document types confuse the classifier.
- Is the **Priority** of the rule you wanted high enough relative to competing rules?

**`API error: …` toast in the UI.**
The backend is unreachable or returned an error. Make sure the backend process (Tauri sidecar in installed builds, manual `uvicorn` when running from source) is up and listening on `localhost:8000`. The browser shows a clear "Backend unreachable" screen with a Retry button when `/setup/status` itself can't be reached.

**Reset everything and start over.**
The dev-uninstall CLI lets you wipe state selectively or completely. From the source repo:

```bash
scripts/dev-uninstall.sh --all --yes        # Linux/macOS
scripts/dev-uninstall.ps1 --all --yes       # Windows
```

Or call it interactively without flags to pick targets one by one. See `dev-testing.md` for details.

---

## Where things live on disk

| Item | Default (Windows) |
|---|---|
| `config.json` | `%APPDATA%\zerobox\config.json` |
| `.env` (API keys) | `%APPDATA%\zerobox\.env` |
| Inbox | `%USERPROFILE%\zerobox\inbox` (configurable in wizard) |
| Archive | `%USERPROFILE%\zerobox\archive` (configurable in wizard) |
| Profiles | `%USERPROFILE%\zerobox\profiles` (configurable in wizard) |
| Audit database | `%USERPROFILE%\zerobox\audit.db` (configurable via `config.json`) |

On macOS and Linux, the per-user config dir becomes `~/Library/Application Support/zerobox/` or `~/.config/zerobox/`. Data folders are wherever the wizard placed them (defaults to `~/zerobox/...`).

---

## Further reading

- `README.md` — installation and configuration reference, prerequisites, model-name lookup commands.
- `architecture.md` — internal architecture and module layout (developer-oriented).
- `dev-testing.md` — running zerobox from source, dev-uninstall CLI, manual API testing.
- `MEMORY.md` — project journal: requirements (`FR-*`), design decisions (`DD-*`), ideas (`IDEA-*`).
