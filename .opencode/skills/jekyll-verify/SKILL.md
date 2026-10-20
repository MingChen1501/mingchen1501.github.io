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
    The suite builds the site once per session; to reuse an existing build instead, set `E2E_PREBUILT_SITE=<dir>` (see `tests/e2e/README.md` "Shared fixtures").
   Visual pixel compares skip locally by default and always run in CI —
   opt in locally with `E2E_VISUAL=1` (#265).
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
    - Theme toggle (`_includes/header.html` `.theme-toggle`,
      `_includes/head.html` bootstrap, `assets/js/theme-toggle.js`,
      `_sass/minima/custom/_theme-toggle.scss`, `minima.skin`) →
      `tests/e2e/test_theme_toggle.py` (OS default, persistence, localized
      names, keyboard, 44px target, axe contrast in both modes) plus the
      dark blockquote pin in `tests/e2e/test_axe_a11y.py`.
   - Search (`search.json` template, `_includes/search.html`,
     `assets/js/search.js`, `search.md`, `vi/search.md`, nav links) →
     `tests/e2e/test_search.py` (index fields, both language pages,
     diacritics-free VI queries, keyboard, no 375px overflow).
   - Share buttons (`_includes/share.html`, `assets/js/share.js`) →
     `tests/e2e/test_share_buttons.py` (post-only row, localized labels,
     copy-link + fallback, share intents, `noscript` link, no tracker).
   - Image lightbox (`assets/js/lightbox.js`, post content images, its
     SCSS partial) → `tests/e2e/test_lightbox.py` (triggers, dialog
     semantics, keyboard/arrows/Esc, focus trap + restore; baselined pages
     stay pixel-identical, so no baseline regeneration).
   - Reading progress + back-to-top (`_layouts/post.html` bar/button
     markup, `assets/js/reading-progress.js`) →
     `tests/e2e/test_reading_progress.py` (post-only, `hidden` up front,
     0-100% tracking, ~600px button reveal, reduced motion, no-JS).
   - Print stylesheet (`_sass/minima/custom/_print.scss`) →
     `tests/e2e/test_print_styles.py` (article-only output, last import,
     single `@media print` block, dark-mode print pinned to light).
   - List thumbnails (`_includes/post-thumbnail.html`,
     `script/generate-thumbnails`, `assets/img/thumbs/**`, the list-thumb
     SCSS partial) → `tests/e2e/test_list_thumbnails.py` (source chain,
     fixed 120x90 box, no CLS; rerun `script/generate-thumbnails` after
     adding or changing a post image and commit the variants).
   - Post-only JS gating + shared helper (`_includes/sub-footer.html`
     script tags, `assets/js/site-utils.js`, any `assets/js/` caller) →
     `tests/e2e/test_post_only_js.py` (share/reading-progress scripts on
     post pages only) plus `tests/e2e/test_site_utils.py` (the three
     shared primitives live only in the helper; total-bytes ceiling in
     `script/asset-budget.sh` with `tests/e2e/test_asset_budget.py`).
   - Giscus theme sync (`_includes/comments.html` mapping attributes,
     `assets/js/giscus-theme.js`) →
     `tests/e2e/test_giscus_comments.py` (embed attempt with zero real
     network, initial paint + toggle flip in every OS x site combo;
     needs `JEKYLL_ENV=production` — dev builds gate comments off).
   - Post social image + JSON-LD `image:` (post front matter only, no
     layout/SEO-template change) → `tests/e2e/test_post_social_image.py`
     (every local-image post declares root-relative `image:`, file exists
     and stays within budget; never hand-write a second `BlogPosting`
     block — `jekyll-seo-tag` owns the graph).
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
8. Confirm the issue and PR carry a risk label (`risk-low`/`risk-medium`/`risk-high`/`risk-very-high`).
9. Merge/CI: merge only when CI is green; squash merge only
   (`gh pr merge <n> --squash --delete-branch`); stacked PRs keep their base branch
   alive until the child merges. See `references/checklist.md` "Merge and
   orchestration".
10. Concurrency: a verify session is part of task-worker work — do not run it
    alongside another task worker; queue it. Pool (canonical:
    `orchestrator` skill): one task worker at a time plus one buffer
    worker (see `references/checklist.md` "Concurrency").
11. On a failure at any step → fix it, then rerun from that step. Do not open a PR while red.
