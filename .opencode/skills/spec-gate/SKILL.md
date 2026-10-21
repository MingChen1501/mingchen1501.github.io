---
name: Spec gate
description: Spec-managed workflow for the site — change tiers T0-T4, minimum spec set per tier, spec-role ownership, and the spec-reviewer gate before implementation. Use when scoping any change, writing specs before code, or gating an implementation worker.
trigger: "Scoping a site change, writing specs before implementation, or checking the spec gate: read this skill for tiers, minimum spec sets, role ownership, and the reviewer verdict."
---

# Spec gate (spec-managed workflow, #348)

No behavioural, architectural, or release-affecting change jumps straight
from idea to code. Specs are written first, marked `active` in
`docs/README.md`, and checked by the `spec-reviewer` before any
implementation worker starts. One rule lives here only; `AGENTS.md`, the
`orchestrator` skill, and role files link here instead of restating it.

## Role ownership (role -> doc groups)

| Role | Owns | May decide |
|---|---|---|
| `product-owner` | `docs/product/*`, `docs/business/*` | scope in/out, acceptance criteria, priority order, when a stub may stay stubbed |
| `business-analyst` | `docs/requirements/*` | FR/NFR wording, data dictionary, business rules, traceability inputs |
| `architect` (as solution architect) | `docs/architecture/*`, `docs/technical/*` | HLD/LLD, schemas, integration contracts, ADR authorship |
| `qa-lead` | `docs/testing/*` | strategy, plan, cases, data, traceability completeness (every FR/NFR has at least one guard) |
| `release-manager` | `docs/release/*`, `docs/devops/*`, `docs/operations/*` | release notes, rollback, deployment/env, runbook freshness at merge time |
| `spec-reviewer` | none (read-only gate) | PASS/FAIL verdict only — never edits specs, never implements |

Role files (`.opencode/agents/*.md`) state per role what it reads, writes,
must not do, and which artefacts it leaves behind (file path + status
change in `docs/README.md`).

## Change tiers and minimum spec sets

| Tier | Shape | Minimum spec set (before the implementation PR opens) |
|---|---|---|
| **T0 docs-only** | prose/docs/process only, no site behaviour change | no gate; `docs/README.md` statuses updated in the same PR when a doc flips stub <-> active |
| **T1 low risk, no behaviour change** | typo, test-only, dependency bump | no new spec; `docs/README.md` unaffected |
| **T2 behaviour change** | reader-visible UI/content feature | acceptance criteria + FR/NFR delta + test traceability, written before the implementation PR opens |
| **T3 architectural** | new subsystem, data-model change (e.g. series/tags), workflow change, subsystem removal | T2 set + ADR + HLD update before implementation; ADR status must move `proposed -> accepted` (owner) before code merges |
| **T4 release-affecting** | workflow/permissions/deployment change | applicable T0-T3 set + deployment/env/runbook deltas + rollback note in the same PR |

Tier is chosen by the owning spec role (`product-owner` for scope,
`architect` for T3) and recorded in the issue; `spec-reviewer`
re-checks the tier as part of its verdict.

## Gate procedure

1. The orchestrator spawns the owning spec role(s) for the tier; they
   write/update the required specs and flip the matching `docs/README.md`
   rows to `active`.
2. The orchestrator spawns `spec-reviewer`, which checks that the
   required specs exist, are `active`, and match the change, then posts
   one COMMENT verdict (`SPEC-GATE PASS` or `SPEC-GATE FAIL` with
   `file:line` gaps) on the issue/PR — same mechanics as the
   `dev-peer-review`/`content-review` verdicts (no native AO reviewer,
   never `ao review trigger` on this project).
3. Implementation starts only on PASS. On FAIL the orchestrator routes
   the gaps back to the owning spec role, not to the implementer.
4. T3 additionally requires the owner to accept the ADR
   (`proposed -> accepted`) before the implementation PR merges.

## How the tiers interact with existing rules

- **Risk labels.** Tier sets the spec floor; risk sets the merge bar
  (canonical: `jekyll-review` skill). Rough mapping: T0/T1 land on
  `risk-low`; T2 on `risk-medium`; T3/T4 often `risk-medium` or higher.
  Either axis can escalate independently — a T2 with SEO/URL blast
  radius is still `risk-high` and still needs owner approval to merge.
- **1-worker pool.** Spec sessions count as the single task worker
  (canonical pool rule: `orchestrator` skill). Spec work and
  implementation run sequentially, never in parallel: specs first,
  gate verdict next, implementation last.
- **Article workflow.** Articles keep their owner-read gate
  (`article-writer` skill, entry #190/#192): the owner's confirmation
  of title/slug/tags/outline is the article spec, and no separate
  `spec-reviewer` pass applies. If an article needs site behaviour
  (new layout, new tag pillar), that part is tiered separately.

## Worked example

PR #349 (removing the static client-side search, Closes #342,
`risk-medium`): deleting `search.json`, `assets/js/search.js`, the
search include/SCSS/nav entries, and the search guards is a subsystem
removal, so tier **T3 architectural**. Under this gate it would have
required, before the implementation PR: an ADR (remove vs keep search,
owner-accepted), an HLD/LLD update (component removal), the FR/NFR
delta (drop the search FRs, lower the JS budget), updated test
traceability (search guards removed), and acceptance criteria — the
same artefacts the PR in fact carried as diff hunks, but written as
specs first with `docs/README.md` rows flipped to `active`.
