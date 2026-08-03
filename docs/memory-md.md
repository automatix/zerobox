# MEMORY.md — Project Journal Pattern (Reusable Foundation)

A generic, project-independent description of the `MEMORY.md` pattern used in this repository (see `MEMORY.md` for the concrete instance). Written as the reusable by-product of explaining the pattern to a user who wanted to bootstrap it in a different project (`#154`); companion piece to `windows-installer.md` (`#134`) and `in-app-updater.md` (`#139`).

---

## Purpose

`MEMORY.md` is a project's **journal**. It records what neither the code nor `git log` can reconstruct: requirements, decisions made together with the alternatives that were rejected, open ideas, and the chronological history of individual pieces of work.

It complements — and does not replace — these other documents:

| Document | Purpose |
|---|---|
| `CLAUDE.md` | Stable rules of engagement: architecture overview, branching, ticket workflow, versioning |
| `MEMORY.md` | The evolving record: requirements, decisions, ideas, work log |
| `docs/architecture.md` (if present) | Current state (no history, no "why" — just "what is true now") |
| Git history | Authoritative for *what* changed and *when* — but does not encode *why* one of several options was chosen |

## Structure

```markdown
# MEMORY.md — {{Project Name}} Project Journal

This file documents the evolution of {{Project Name}}: requirements,
design decisions, problems, solutions, and ideas for future work.

---

## Functional Requirements
### `FR-01` — {{Title}}
{{What the software is meant to do, functionally.}}

## Non-Functional Requirements
### `NFR-01` — {{Title}}
{{Quality attribute: architecture, security, target platform, traceability, …}}

## Design Decisions
### `DD-01` — {{Title}} (`{{Date}}`)
**Decision:** {{What was decided.}}
**Rationale:** {{Why — including the alternatives considered and why they were rejected.}}

## Ideas / Future
- `IDEA-01` — **{{Short title}}** — {{Description; not yet a ticket.}}

---

## Work Log
### `{{Date}}` — `#{{Ticket}}`: {{Title}}
**Request:** {{What was asked for.}}
**Done:** {{What was done — brief.}}
**Result:** {{Outcome, ticket status, branch/PR reference.}}
```

## Core Rules

- **IDs are stable and are never reused or deleted.** A superseded decision is not removed — it is marked `**Superseded by `DD-0X`**` and stays in place. Traceability beats tidiness.
- **Every Design Decision names the rejected alternative and why it was rejected**, not just the chosen option. That is the actual value-add over a code comment.
- **Work Log entries are tied to a ticket** (Request/Done/Result) and correspond directly to the project's ticket system (GitHub Issues, Jira, Linear, …).
- **Relative dates are converted to absolute dates at write time** (`"last Thursday"` → `2026-07-30`), so an entry stays legible months later.
- **The file is updated after every unit of work and versioned in the same or a dedicated commit** — it is part of normal history, not a document written once and left to rot.
- **Reference it from the project's `CLAUDE.md`** under the core documents to read, so it gets picked up at the start of every session.

---

## Adaptation Checklist for a New Project

`1.` Create `MEMORY.md` at the project root with the five sections above (Functional Requirements, Non-Functional Requirements, Design Decisions, Ideas / Future, Work Log).
`2.` Seed it with whatever requirements/decisions can be reconstructed from the current state, if the project already has history.
`3.` Reference `MEMORY.md` from `CLAUDE.md` (or the project's equivalent instructions file) as a core document to read at session start.
`4.` Add a Work Log entry after every completed unit of work, in the same or a dedicated commit.
`5.` Never delete or reuse an `FR-*`/`NFR-*`/`DD-*`/`IDEA-*` ID — supersede in place instead.

---

## Copy-Paste Prompt for a New Claude Instance

The block below can be handed unmodified to a Claude instance in **another** project to introduce `MEMORY.md` there and lock in the maintenance rules going forward.

```text
Create a file `MEMORY.md` at the project root — the project journal.
Purpose: record what neither the code nor `git log` shows — requirements,
design decisions together with the alternatives that were rejected, open
ideas, and a chronological work log.

Structure (sections in this order, IDs per section incrementing and never
reused):

1. `## Functional Requirements` — `FR-01`, `FR-02`, … : what the software
   is meant to do, functionally.
2. `## Non-Functional Requirements` — `NFR-01`, … : quality attributes
   (architecture, security, target platform, traceability, …).
3. `## Design Decisions` — `DD-01` (date): **Decision** + **Rationale**.
   Rationale always names the alternatives that were considered and
   rejected, and why — not just the chosen option.
4. `## Ideas / Future` — `IDEA-01`, … : ideas that are not yet a ticket.
5. `## Work Log` — chronological entries, one per ticket/unit of work,
   format: `### {Date} — #{Ticket}: {Title}` with **Request** (what was
   asked for), **Done** (what was done, brief), **Result** (outcome,
   ticket status, branch/PR reference).

Maintenance rules, effective immediately and permanently for this project:

- Add a new Work Log entry after every completed unit of work
  (Request/Done/Result) and version the file in the same or a dedicated
  commit.
- Never delete or reuse an ID (`FR-*`, `NFR-*`, `DD-*`, `IDEA-*`). A
  superseded design decision is not removed — mark it
  `**Superseded by `DD-0X`**` and leave it in place.
- Convert relative dates ("last Thursday") to absolute dates
  (`2026-07-30`) at write time.
- If a `CLAUDE.md` (or equivalent project instructions file) exists,
  reference `MEMORY.md` there among the core documents to read, so it is
  picked up at the start of every session.
- `MEMORY.md` does not duplicate git history (no "what changed") or the
  architecture docs (no "what is the current state") — it adds the *why*
  and the running history on top of both.

Create the file now with the five sections (empty, or seeded with a first
sensible entry if the project already has requirements or decisions that
can be reconstructed) and briefly confirm that the maintenance rules apply
from now on.
```
