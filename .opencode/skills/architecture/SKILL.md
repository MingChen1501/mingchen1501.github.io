---
name: Architecture
description: Audit site architecture and maintain specs. Use when evaluating boundaries, coupling, duplication, dead code, or bloat, or when writing specs under docs/architecture.
trigger: "Auditing site architecture (boundaries, coupling, duplication, dead code, bloat) or maintaining docs/architecture specs: read this skill, quantify every finding, spec first, file small issues."
---

# Architecture working method

Definition only; audit execution and spec content are separate
issues. No code, layout, style, JS, CI, or config behavior change.

## What to read

In order: site structure (`_layouts/`, `_includes/`, `_sass/`,
`assets/js/`), data files (`_data/`), tests/scripts (`tests/`,
`script/`), CI workflows (`.github/workflows/`), then `_config.yml`
and `docs/` for existing specs and conventions. Use `glob`, `grep`,
`git log` for history; `git diff` for PR scope in review-lens mode.

## How to quantify

Every finding needs `file:line` plus at least one measurement:
include counts (include/include chains, call sites), sizes
(file/asset KB against the 500KB-per-file and 6MB-total budgets),
duplication instances (repeated Liquid/SCSS/JS blocks with
locations), dead-code evidence (zero references via `grep`), or
bloat deltas. No finding without evidence; no speculative rewrites.

## Spec layout (`docs/architecture/`)

One spec per area (e.g. `layouts.md`, `styles.md`, `scripts.md`):
purpose, current structure (tree + file roles), boundaries (what
belongs where), coupling notes (who includes/imports whom),
known findings (linked issues), and open questions. Keep specs
short; link out instead of restating.

## Issue-filing format

One small issue per refactor (one worker = one PR downstream),
each with: context (evidence-backed findings), clear scope,
acceptance criteria, exactly one risk label (`risk-low` /
`risk-medium` / `risk-high` / `risk-very-high`), and an English
title/body.

## Review-lens mode

For architecture-affecting PRs, post an advisory checklist only:
boundaries, coupling, duplication, dead code, bloat, spec drift —
each item with `file:line` evidence. No merge authority and no
APPROVE/CHANGES_REQUESTED verdict; the verdict stays with the
reviewer role (`jekyll-review` skill).
