# BACKLOG.md — Idea Backlog Pattern (Reusable Foundation)

A generic, project-independent description of the `BACKLOG.md` pattern used in this repository (see `BACKLOG.md` for the concrete instance). Split out of the project journal once its idea list grew (`#156`); companion piece to `MEMORY.md-pattern.md` (`#154`), `windows-installer.md` (`#134`), and `in-app-updater.md` (`#139`).

---

## Purpose

`BACKLOG.md` is a project's **idea backlog** — unprioritized ideas for future work that are not yet tickets. It gives ideas a durable home between "someone thought of this" and "someone picked it up," without cluttering the requirements/decisions journal and without forcing every half-formed idea into the ticket system prematurely.

It complements — and does not replace — these other documents:

| Document | Purpose |
|---|---|
| A project journal (e.g. `MEMORY.md`) | Requirements, design decisions, and the chronological work log — what *was* decided and done |
| The ticket system (GitHub Issues, Jira, Linear, …) | Planned, actionable work — what *will* be done, with an owner and a status |
| Git history | Authoritative for *what* changed and *when* — irrelevant to ideas that haven't been acted on yet |

## Structure

```markdown
# BACKLOG.md — Idea Backlog

Unprioritized ideas for future work — not yet tickets. When an idea is
picked up, open a ticket for it (referencing the `IDEA-*` id) and leave
the entry here for traceability; don't delete it.

---

- `IDEA-01` — **{{Short title}}** — {{Description of the idea, why it
  might be worth doing, and any open questions.}}
- `IDEA-02` — **{{Short title}}** — {{...}}
```

A single flat list is enough for most projects. If the backlog grows large, group entries under `##` headings (by area, by theme) while keeping the `IDEA-*` numbering flat and sequential across the whole file — grouping is presentation, not a second ID namespace.

## Core Rules

- **IDs are stable and are never reused or deleted**, exactly like a journal's `FR-*`/`DD-*` ids. An idea that turns out to be a bad one is still not removed — leave it as-is; the list is a record of what was considered, not just what's still live.
- **Picking up an idea does not delete its entry.** Once a ticket is opened for it, the ticket references the `IDEA-*` id (and, symmetrically, the ticket number can be added to the entry) — the backlog stays the traceable origin of the work.
- **Entries are short.** A title and a few sentences of rationale — enough to act on later without re-deriving the idea from scratch, not a full spec.
- **The file is updated whenever a new idea comes up or an existing one is picked up**, and versioned in the same or a dedicated commit — like any other project doc, not a document written once and left to rot.

## When to Split It Out of a Journal

Projects that already keep a requirements/decisions journal often start with ideas as a section inside that same file (e.g. `## Ideas / Future` inside `MEMORY.md`). That's a reasonable starting point. Split it into a dedicated `BACKLOG.md` once the idea list grows past a handful of entries and starts crowding out the requirements/decisions content — same `IDEA-*` ids, no renumbering, just a new home. See `MEMORY.md-pattern.md` for the single-file starting point this pattern splits out of.

---

## Adaptation Checklist for a New Project

`1.` Create `BACKLOG.md` at the project root with a short header (purpose, relation to the journal and the ticket system) followed by the `IDEA-*` list.
`2.` Seed it with whatever open ideas already exist — in people's heads, in old chat threads, in a journal's `Ideas / Future` section if one exists — assigning each a stable id.
`3.` Reference `BACKLOG.md` from the project's instructions file (e.g. `CLAUDE.md`) as a core document to read at session start, alongside the journal.
`4.` When an idea is picked up, open a ticket referencing its `IDEA-*` id; leave the backlog entry in place.
`5.` Never delete or reuse an `IDEA-*` id.

---

## Copy-Paste Prompt for a New Claude Instance

The block below can be handed unmodified to a Claude instance in **another** project to introduce `BACKLOG.md` there and lock in the maintenance rules going forward.

```text
Create a file `BACKLOG.md` at the project root — the idea backlog.
Purpose: give unprioritized ideas for future work a durable home before
they become tickets, without cluttering the project's requirements/
decisions journal (if one exists) or forcing half-formed ideas into the
ticket system prematurely.

If this project already keeps ideas inline in a journal file (e.g. a
`## Ideas / Future` section inside a `MEMORY.md`-style document), move
that section's content into the new `BACKLOG.md` verbatim, keeping the
existing ids unchanged, and remove the section from the journal. If no
such ideas exist yet, start `BACKLOG.md` empty except for its header.

Structure:

```markdown
# BACKLOG.md — Idea Backlog

Unprioritized ideas for future work — not yet tickets. When an idea is
picked up, open a ticket for it (referencing the `IDEA-*` id) and leave
the entry here for traceability; don't delete it.

---

- `IDEA-01` — **{{Short title}}** — {{Description.}}
```

Maintenance rules, effective immediately and permanently for this project:

- Never delete or reuse an `IDEA-*` id. An idea that turns out to be bad
  stays in the list as a record of what was considered.
- When an idea is picked up, open a ticket referencing its `IDEA-*` id;
  do not delete the backlog entry.
- Keep entries short: a title and a few sentences of rationale, not a
  full spec.
- Update the file whenever a new idea comes up or an existing one is
  picked up, and version it in the same or a dedicated commit.
- If a project instructions file (e.g. `CLAUDE.md`) exists, reference
  `BACKLOG.md` there among the core documents to read at session start.

Create the file now (moving over any existing inline ideas, or empty if
none exist) and briefly confirm that the maintenance rules apply from now
on.
```
