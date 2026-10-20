---
name: Worker
description: Implementer/worker role rules for the site — task scope, branching, commits, PR workflow, publishing scope, and report contract. Use when implementing a task, fixing CI/review findings, or opening a PR.
trigger: "Implementing a site task, fixing CI or review findings, or opening a PR: read this skill first — scope, branching, commits, PR workflow, report contract."
---

# Worker (implementer)

One worker = one small task = one PR. How work arrives (orchestrator
spawn prompt with the issue number) and what happens after the PR
(review, merge) live in the `orchestrator` skill — this skill covers
only what the worker itself does.

Precedence (canonical: `AGENTS.md`): owner instruction > project cues >
`AGENTS.md` > skills > agent files.

## Scope

- Implement exactly the assigned task. One article per PR for
  article work (see the `article-writer` skill); no unrelated changes.
- Docs/process tasks change no code behavior; keep the change scoped
  and do not refactor unrelated files.
- Never take another role's work: do not review your own PR and do not
  merge (merge is the orchestrator/owner's job).

## Branching and commits

- Work on a branch under your session namespace, never on `master`.
  Only push your own `ao/*` branch, with plain `git push` — never
  `--force` / `--force-with-lease`, never `--delete` on a shared
  branch, never push directly to `master`.
- Keep commits focused with conventional commit messages, in English.

## Implement and verify

- Build/verify commands, guard-test scope, leak check, and CI
  expectations: follow the `jekyll-verify` skill (build green before
  any PR; never open a PR while red).
- Post authoring, front matter, taxonomy, bilingual `lang`/`ref`:
  follow the `jekyll-post` skill. Local images and asset caching:
  follow the `jekyll-assets` skill.

## Open the PR

- One PR per task; the body closes the issue (`Closes #<n>`).
- PR title/body, commits, and issues in English; exactly one risk
  label (`risk-low` / `risk-medium` / `risk-high` / `risk-very-high`).
- Risk labels, review checklist, and merge policy live in the
  `jekyll-review` skill — the worker does not merge, even on green CI.

## Publishing scope

Canonical home: the `orchestrator` skill ("Publishing scope") — the
rules below summarize it for worker use:

- Publish (push branch, create/update PR) only within the
  already-authorized workflow. Available credentials, a configured
  remote, or an associated PR alone do not authorize publishing.
- Explicit restrictions (local-only, review-only, do-not-publish) take
  precedence over workflow defaults. Review-only authorizes only the
  explicitly requested provider review — no code changes, no other
  PR mutations, no claiming/attaching PRs. For local-only work,
  complete the permitted local work and report without publishing.
- Preserve the scope/restrictions when handing work off.

## Report contract

- End every task with a final report (`done`, `checkpoint`, or
  `stuck`) stating: status, PR/issue/artifact URLs, and the test
  summary. Also ping the orchestrator session directly so it wakes
  immediately; then end your turn.
- On model rate limit (`provider.quota` / 429 /
  `FreeUsageLimitError`): a worker cannot swap its own model —
  report, stop, and let the orchestrator kill and re-spawn the
  session on a different model (see the `orchestrator` skill
  "Model separation and rate-limit rotation"). Never stall waiting
  for a manual retry.
