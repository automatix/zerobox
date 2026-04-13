# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Zerobox** — AI-powered scan processing app for Windows `11`. Automates the workflow: scan intake → OCR → AI classification (naming + filing) → user review → file operations. Rule-based learning through user-defined JSON profiles.

## Architecture

Modular service architecture with independent modules communicating through well-defined interfaces:

- **Scanner** — file ingestion from a configurable input folder
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
