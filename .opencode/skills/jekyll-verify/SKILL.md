---
name: Jekyll Verify
description: Check changes before opening a PR (Jekyll build, comments E2E tests). Use after editing layout, include, sass, config, or before creating a PR.
---

# Verify before a PR

## Workflow

1. Determine the scope from `git status --short`:
   - Only added/edited posts in `_posts/` → step 2 is enough.
   - Touched `_layouts/`, `_includes/`, `_sass/`, `_config.yml`, `assets/` → run both steps 2 + 3.
   - Touched `assets/` (images) → also run `script/check-images` (single file <= 500KB,
     `assets/img/` total <= 6MB).
2. Build: `bundle exec jekyll build --trace` (run `bundle install` first if gems are missing).
3. Test: `python -m pytest tests/e2e -v` (first time: `pip install -r tests/e2e/requirements.txt`).
4. Review the common breakages in `references/checklist.md`.
5. Confirm the issue and PR carry a risk label (`risk-low`/`risk-medium`/`risk-high`/`risk-very-high`).
6. Merge/CI: merge only when CI is green; merge commits only
   (`gh pr merge --merge --delete-branch`); stacked PRs keep their base branch
   alive until the child merges. See `references/checklist.md` "Merge and
   orchestration".
7. Concurrency: a verify session is part of task-worker work — do not run it
   alongside another task worker; queue it (see `references/checklist.md`
   "Concurrency").
8. On a failure at any step → fix it, then rerun from that step. Do not open a PR while red.
