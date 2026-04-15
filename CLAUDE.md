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

## Versioning

This project uses Semantic Versioning (`semver.org`). After each commit, evaluate whether a new version release is warranted. Announce version bumps with a brief rationale (patch / minor / major).

When releasing a new version:
`1.` Update version in all manifests (`backend/pyproject.toml`, `frontend/package.json`, `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/tauri.conf.json`)
`2.` Create an annotated Git tag (`git tag -a vX.Y.Z`)
`3.` Build installers via `scripts/build-installer.ps1`
`4.` Create a GitHub Release with the installer artifacts (MSI + NSIS) attached
