# ADR-001: In-repo architecture specs under docs/architecture/

- Status: accepted
- Date: 2026-10-20
- Context: #290 — the codebase was perceived as bloated with no accurate
  in-repo picture; follow-up refactors needed an evidence base.
- Decision: one short spec per area (`overview.md`, `content-pipeline.md`,
  `styling.md`, `javascript.md`, `testing.md`, `data-model.md`) plus this
  `decisions/` log. Each spec carries purpose, structure, boundaries,
  coupling notes, findings with `file:line` evidence, and open questions;
  specs link out instead of restating (`AGENTS.md`, skills, per-feature
  READMEs stay canonical).
- Consequences: refactors cite specs + issues (#293-#297); specs must be
  updated by any PR that changes the structures they describe, or they rot.
