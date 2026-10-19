---
name: Jekyll Verify
description: Check changes before opening a PR (Jekyll build, comments E2E tests). Use after editing layout, include, sass, config, or before creating a PR.
trigger: "After editing layout, include, sass, config, or assets — or before opening a PR: build, tests, guards, leak check, CI expectations."
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
   Scope matrix — run the matching guard when you touch:
   - Image sizing, layout wrappers, `_sass/` → `tests/e2e/test_layout_overflow.py`
     (builds the site, asserts no horizontal scroll at 375px on a post page, the
     home list, and the tag pages; needs Ruby + `bundle install`, skips with an
     explicit reason without `bundle`).
   - `_includes/head.html` or any file under `assets/` → `jekyll-assets` cache
     rules plus `tests/e2e/test_stylesheet_cache_version.py`.
   - `_layouts/home.html`, `_layouts/tag.html`, `_includes/site-sidebar.html`,
     or the list grid in `_sass/` → `tests/e2e/test_sidebar_layout.py` (sidebar
     shell, highlights, collapsed tag block, no inner scrollbar, 375px
     overflow on `/` and a `/tags/<tag>/` page).
   - `_includes/header.html`, `_includes/nav-items.html`,
     `_includes/sub-footer.html`, `assets/js/`, or the nav rules in `_sass/` →
     `tests/e2e/test_nav_a11y.py` (button disclosure: accessible name,
     aria-expanded toggling, keyboard/Escape; link-free summaries).
   - New post only → a build smoke test is enough; verify front matter matches
     the 4-pillar taxonomy template (`tags`, `description`) — see the
     `jekyll-post` skill.
4. Review the common breakages in `references/checklist.md`.
5. Leak check: a build must leave neither `AGENTS.md` nor `.opencode/` in
   `_site/` (both are `exclude`d in `_config.yml`).
6. `robots.txt`, `sitemap.xml`, and `llms.txt` are generated at build time and
   must not be hand-edited.
7. CI: Lighthouse CI (`.github/workflows/lighthouse.yml`) runs on PRs to
   `master` and fails on Performance / Accessibility / Best Practices / SEO
   regressions; thresholds live in `lighthouserc.json` (Performance is `warn`,
   the rest `error`).
5. Confirm the issue and PR carry a risk label (`risk-low`/`risk-medium`/`risk-high`/`risk-very-high`).
6. Merge/CI: merge only when CI is green; squash merge only
   (`gh pr merge <n> --squash --delete-branch`); stacked PRs keep their base branch
   alive until the child merges. See `references/checklist.md` "Merge and
   orchestration".
7. Concurrency: a verify session is part of task-worker work — do not run it
   alongside another task worker; queue it (see `references/checklist.md`
   "Concurrency").
8. On a failure at any step → fix it, then rerun from that step. Do not open a PR while red.
