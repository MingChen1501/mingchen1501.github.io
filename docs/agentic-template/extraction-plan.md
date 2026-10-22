# Copy-out checklist: reuse the in-repo skeleton

Status: active. How to copy `docs/agentic-template/` into another
project. No standalone template repository is created by this or any
later change.

## Decision

**Option B** (issue #370): keep the template as a skeleton inside this
repo (`docs/agentic-template/` plus copyable files); no new repo. This
blog stays the worked example. The separate-template-repo option
(Option A in earlier revisions of this file) is rejected: a second
repository would need periodic sync decisions with no second adoption
in sight, so the copy-out checklist below is the whole extraction
story.

## What to copy

Copy these files into the new project's `docs/agentic-template/`
(or equivalent group) and link the group from its docs index:

- `README.md` — who the template is for, what it gives, adoption checklist
- `roles.md` — generalized role table + per-role file skeleton
- `gate.md` — the T0–T4 spec gate + a blank worked example
- `conventions.md` — artefact/commit/session naming, merge policy, verdict mechanics
- `bootstrap.md` — new repo to first guarded PR, step by step
- This file (`extraction-plan.md` is now this checklist; do not copy
  it unless the new project also wants to offer the skeleton onward)

Also copy `script/ao-role-footer.sh` and the role files
(`.opencode/agents/`) per `bootstrap.md` steps 2–3.

## Cleaning checklist

Before first use in the new project, replace or drop source-repo specifics:

1. Replace project nouns with placeholders per `bootstrap.md`
   (project name, repo path, agent-guide path, default branch).
2. Drop all blog-specific content: static-site-generator specifics,
   theme styling, bilingual content rules, comment-widget
   integrations, CDN configuration, article workflows, asset budgets,
   visual baselines/fixtures.
3. Drop all host-specific config: custom domains, analytics IDs,
   secrets, `giscus.repo_id` / `giscus.category_id` values.
4. Carry no git history: copy files with `cp -r` or `git archive`,
   never by forking or pushing this repo's history.

## Consumer start

```sh
cp -r docs/agentic-template [new-repo]/docs/agentic-template
```

Then follow `bootstrap.md` from step 1 (docs tree) onward in the new
repo. Note: there is no update path — consumers freeze at copy time
and pick up later improvements manually.
