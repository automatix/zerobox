# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Zerobox** — AI-powered scan processing app for Windows `11`. Automates the workflow: scan intake → OCR → AI classification (naming + filing) → user review → file operations. Rule-based learning through user-defined JSON profiles.

## Architecture

Modular service architecture with independent modules communicating through well-defined interfaces:

- **Intake** — file discovery from a configurable input folder
- **OCR Engine** — text extraction via `ocrmypdf` (Tesseract wrapper)
- **Classifier** — AI-based naming/filing via swappable LLM provider (Claude, OpenAI, Ollama)
- **Rule Engine** — JSON profile management, pattern matching
- **File Manager** — rename/move operations
- **Audit Logger** — SQLite-based action log
- **UI** — Tauri `2` + Svelte `5` desktop frontend

Backend (Python `3.13` + FastAPI) runs as a Tauri sidecar process, communicating via local HTTP.

## Key Documentation

- `MEMORY.md` — project journal: requirements (`FR-*`), non-functional requirements (`NFR-*`), design decisions (`DD-*`), ideas (`IDEA-*`)
- `docs/architecture.md` — living architecture document (directory structure, modules, interfaces, data flow, config model). **Update this file with every architectural change.**
- `docs/roadmap.md` — phased roadmap (`7` phases) with `29` tickets

## Tickets

Tickets are tracked as GitHub Issues on `automatix/zerobox` with phase labels (`phase:1-foundation` through `phase:7-packaging`). Reference format: `#{number}` (GitHub issue number). All changes must go through tickets — create a ticket before implementing.

All changes are developed in branches. Choose the prefix that matches *why* the change is happening, not *what* files it touches:

| Prefix | Use for |
|---|---|
| `feature/<description>` | New user-visible functionality or internal capability (something that previously wasn't possible). |
| `bugfix/<description>` | Repairing a defect — behaviour was wrong, errored, or regressed. |
| `hotfix/<description>` | Urgent defect repair on an already-released version, typically branching from the release tag rather than from `master`. |
| `release/<version>` | Release-branch for cutting a version: manifest bumps and release-notes prep, nothing else. |
| `chore/<description>` | Housekeeping — tooling, build config, CI, lockfile / dependency refreshes, internal docs, metadata. No behaviour change, no defect fixed, no feature added. |

Merge to `master` when done. Push at least on every ticket close.

Maintain ticket status via labels: `status:ready` (new/backlog), `status:in-progress` (being worked on), `status:done` (complete). Update on every transition.

## Interaction

When the user gives a directive that references multiple items and mentions parallelism (e.g. `"Mach beides. Gerne parallel."`, `"Löse beides"`, `"X, gerne parallel"`), the default is to **implement** them, not just to create tickets. Only file a ticket without implementing when the user explicitly says `"nur anlegen"` / `"nur ticketen"` / similar, or when an architectural decision requires user input — in which case ask before silently deferring.

Whenever the assistant decides to deviate from any instruction (`CLAUDE.md`, user message, documented process, e.g. the release procedure in `Versioning`), the deviation must be **explicit and visible** in the user-facing response: name what is being skipped or changed and why. The default is to **ask before deviating** — explain the proposed exception and let the user decide. Silent omissions, shortcuts, or "I'll skip this since it seems fine" are not acceptable.

After every change, update the **tests** and the **documentation** to match. Keep them continuously current — no PR leaves a behaviour or user-surface change without matching test updates *and* matching doc updates (`README.md`, `docs/user-guide.md`, `docs/architecture.md`, `docs/dev-testing.md`, `docs/roadmap.md`, `MEMORY.md`, Postman collection, Gherkin features — whichever the change actually touches). Pure internal refactors with no behaviour change must still keep tests green; doc updates only become necessary when something a reader of the docs would notice has changed.

## Versioning

This project uses Semantic Versioning (`semver.org`). After each commit, evaluate whether a new version release is warranted. Announce version bumps with a brief rationale (patch / minor / major).

When releasing a new version:
`1.` Update version in all manifests (`backend/pyproject.toml`, `frontend/package.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/tauri.conf.json`)
`2.` Create an annotated Git tag (`git tag -a vX.Y.Z`)
`3.` Build installers via `scripts/build-installer.ps1`
`4.` Create a GitHub Release with the installer artifacts (MSI + NSIS) attached. Release notes include a **Documentation** section with tag-pinned links to the relevant `.md` files: `https://github.com/automatix/zerobox/blob/vX.Y.Z/docs/user-guide.md`, `…/docs/architecture.md`, `…/docs/dev-testing.md`, `…/docs/roadmap.md`, `…/README.md`. Tag-pinned so the URL snapshots the doc at that version.
