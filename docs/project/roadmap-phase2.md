# Phase 2 roadmap: milestones with measurable exit

Status: active. Phase 2 is planned as milestones, not a flat issue list:
each milestone below states why it matters, what is in and out, exit
criteria a human can check without asking an agent, dependencies, and a
single owning role. Default order is M1 → M2 → M3 → M4; the owner may
reorder streams. Each milestone is 1–2 weeks of agent time.

## M1 — Reader-visible quality (owner: `dev`)

Why: small UX defects compound into a neglected feel; clearing the
known backlog first keeps later work on a clean baseline.

- In: button shape audit (#389), mobile nav flash (#384), sidebar
  sections (#386), Resume/CV (#387), About (#388).
- Out: new reader-facing features; redesigns beyond the listed fixes.
- Exit: the five listed issues are closed; every reader-visible change
  in the milestone has a guard test or updated visual baseline
  (checkable in the merged diffs); Lighthouse CI is green on the
  milestone's PRs.
- Dependencies: none.

## M2 — Discovery closure (owner: `qa-lead`)

Why: deferred discovery round 12 is still unrun; unknown findings are
unbounded risk, and fix throughput is the health signal for the phase.

- In: run discovery round 12; triage and fix its findings.
- Out: new audits beyond round 12; refactors spun out as separate issues.
- Exit: the round-12 report is posted; every high finding is closed or
  converted into a tracked issue; fix throughput (findings closed per
  week) is reported in the milestone-closing comment.
- Dependencies: none; may run in parallel with M1.

## M3 — Content depth (owner: `product-owner`)

Why: series support turns one-off posts into a return path; cadence
plus evergreen refreshes keep the archive accurate.

- In: ADR-004 acceptance, then series nav block, series index pages,
  and guards per ADR-004; article cadence; evergreen refreshes.
- Out: retro-fitting old posts into series (excluded by ADR-004);
  new post types beyond series.
- Exit: ADR-004 is accepted; series nav and index pages are live with
  their guards green; the cadence target recorded in the milestone
  kickoff comment is met; every refreshed post keeps its EN/VI parity.
- Dependencies: blocked on the ADR-004 owner answers (see below).

## M4 — Ops and measurement (owner: `release-manager`)

Why: DORA plus agent metrics make throughput reportable instead of
inferred; the phase audit (#390) closes the loop before Phase 3.

- In: DORA + agent metrics (companion issue), phase audit (#390),
  stack hygiene, owner decision #154 (geo-redirect).
- Out: new metrics tooling beyond what the companion issue scopes;
  platform migrations.
- Exit: the metrics report is posted with median PR lead time under
  1 day over the milestone window (measured from merge timestamps);
  the phase audit is filed; CI is green on `master` at milestone end.
- Dependencies: metric definitions come from the companion issue;
  geo-redirect work is blocked on the #154 owner decision (see below).

## Non-goals for the phase

No search reintroduction (#342/#349 stays removed); no CSP change
(#329 stands); no CMS, database, or comment-platform migration; no
site-wide redesign; no new reader-facing feature beyond the series
nav/index scoped in M3.

## Phase risk register

| Risk | Mitigation |
|---|---|
| Agent throughput limits stall milestones | 1–2-week milestones with a closing comment each; spillover becomes a tracked issue, not silent slip |
| Content accuracy (stale or mistranslated copy) | EN/VI parity guards stay green; evergreen refreshes reviewed as content PRs |
| CI flakiness masks real regressions | flaky runs are quarantined and retried per the runbook; milestone exit requires green, not green-ish |
| Owner review bandwidth bottlenecks decisions | open decisions listed below with the milestone each blocks; nothing waits silently |

Live register: `project/risk-register.md`.

## Open owner decisions

| Decision | Blocks |
|---|---|
| #154 geo-redirect: build it or drop it | M4 platform work |
| ADR-004 Q1–Q5 (slugs, single-post launch, coming-soon shape, JSON-LD shape, index discoverability) | M3 series implementation |
| DORA + agent metric definitions and targets (companion issue) | M4 exit measurement |
