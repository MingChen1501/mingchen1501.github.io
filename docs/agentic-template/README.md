# Agentic-coding base template

Status: active (template starter). A reusable starter for applying
agentic coding to other projects: the role set, the spec gate, the AO
wiring, the CI/test conventions, and the artefact conventions — without
this repo's blog-specific parts.

Start here. The other four files in this directory are the template
body; `extraction-plan.md` covers turning this into a real standalone
template repository (decision still open).

## Who it is for

- A solo owner (or small team) running one AI orchestrator plus short-lived
  worker sessions against a GitHub repository.
- Projects where every change flows through issues and pull requests, CI
  is the source of truth for "done", and merges are squash-only.
- Teams willing to trade a little ceremony (specs before code on
  behaviour changes, a manual review verdict per PR) for fewer
  half-understood merges.

## What the template gives you

| File | Content |
|---|---|
| `roles.md` | generalized role table + the file skeleton each role needs |
| `gate.md` | the T0–T4 change-tier spec gate + a blank worked example |
| `conventions.md` | artefact/commit/session naming, language policy, merge policy, verdict-as-comment mechanics |
| `bootstrap.md` | step-by-step: new repo to first guarded PR, with commands |
| `extraction-plan.md` | how to turn this into a real template repo, with the open decision |

## What is deliberately not in the template

Blog-specific material stays out and survives only as explicitly marked
"worked example" side notes:

- Static-site/Jekyll specifics, bilingual content rules, comment-system
  integrations, CDN configuration, article workflows with owner-read
  gates, per-page asset budgets, and any actual visual baselines.

Worked example (this repo): a personal blog deployed from `master` via a
static-site host, where "reader-visible" means rendered HTML and "guard
tests" include build plus end-to-end checks. Replace those nouns with
your own stack when adopting.

## Adoption checklist

- [ ] Register the AO project for the new repo (`ao project add`,
  set `--agent-rules-file` to the agent guide so every session loads
  the same rules).
- [ ] Copy the `docs/` classification tree and index table
  (`bootstrap.md` step 1); mark every row `active`, `stub (not needed
  yet)`, or `n/a (technical)` — no orphans, no dead links.
- [ ] Install the role files (`roles.md` skeletons) and the spec-gate
  reference (`gate.md`).
- [ ] Turn on branch protection on the default branch (require green CI;
  no direct pushes).
- [ ] Create the risk labels (`risk-low`, `risk-medium`, `risk-high`,
  `risk-very-high`) and require exactly one per issue and PR.
- [ ] Set up the reviewer flow: one dedicated reviewer session per PR,
  reviewer role differs from implementer, verdict posted as a COMMENT
  (`conventions.md`).
- [ ] Run the first guarded PR end to end (`bootstrap.md` step 5) before
  declaring adoption done.
