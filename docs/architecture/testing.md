# Testing

Purpose: what guards what — E2E suite, shell guards, and CI — and where
coverage overlaps.

## Current structure

- `tests/e2e/`: 59 `test_*.py` files plus `conftest.py`, fixtures, and an
  `axe-core` vendored helper — 108 files, ~19,100 LOC total. The largest
  area of the repo (layouts + includes + SCSS + JS ≈ 5,800 LOC combined).
  Largest files: `test_sidebar_layout.py` (1,158), `test_giscus_comments.py`
  (949), `test_i18n.py` (842), `test_search.py` (743).
- `script/` (14 files): `check-images` + `image-budget.sh` (500KB/file,
  6MB-total image budgets), `check-external-images` (allowlisted
  attachment hosts, #195), `classify-content-only` (#229),
  `asset-budget.sh` (JS/CSS byte ceilings), `generate-thumbnails` (#226),
  `article-intake`, `cibuild`, `update-visual-baselines`, plus thin
  `bootstrap`/`build`/`server` wrappers.
- `.github/workflows/` (5 files, 597 LOC): `ci.yaml` (Jekyll matrix +
  image guards + `cibuild`), `e2e.yml` (content-only classifier → static
  guards → one shared build → browser matrix), `lighthouse.yml`,
  `visual-baselines.yml`, `demo_site.yml` (legacy upstream-minima demo
  deploy, unrelated to the personal site).

Two layers by design: static guards (no browser: markup, budgets, image
rules) run always; browser tests (Playwright, visual compares opt-in
locally via `E2E_VISUAL=1`, always in CI) run on full-suite PRs. `tests/e2e/README.md`
documents per-feature coverage; the scope matrix in the `jekyll-verify`
skill maps each touch area to its guard test.

## Boundaries

- Content-only PRs (`_posts/`, `_vi_posts/`, `assets/img/`,
  `_data/highlights.yml`) skip the browser matrix and baselines (#229,
  `script/classify-content-only`); anything else runs the full suite.
- Content-only PRs never regenerate visual baselines
  (`script/update-visual-baselines` is for intentional visual changes,
  diff reviewed before commit).
- Static guards must stay runnable without Ruby/bundler or a browser;
  browser tests reuse the one shared build (`E2E_PREBUILT_SITE`).

## Coupling notes

- Budgets are declared once and parsed in two places: `image-budget.sh`
  → `check-images` + `test_check_images.py`; `asset-budget.sh` →
  `test_asset_budget.py` + `test_syntax_highlight_css.py`. Never redeclare
  the literals.
- `test_css_parity.py` pins the #174 SCSS split (byte-identical CSS);
  any cascade reorder fails it on purpose.
- `e2e.yml` depends on the classifier contract in `tests/e2e/README.md`
  ("CI") — changing either side means changing both.

## Known findings

- #297 — overlap clusters with no documented owner: comments
  (`test_comments.py` + `test_comments_markup.py` + `test_giscus_comments.py`),
  footer (`test_footer_email_a11y.py` + `test_footer_i18n.py` +
  `test_footer_social_a11y.py`), i18n (`test_i18n.py` +
  `test_seo_bilingual.py` + `test_post_chrome_i18n.py` +
  `test_footer_i18n.py`), images (`test_check_images.py` +
  `test_content_images.py` + `test_external_images.py` +
  `test_vi_alt_text.py` + `test_asset_budget.py`). Some layering is
  intentional (static vs browser); record it, then merge strict dupes.
- `demo_site.yml` (Ruby 2.7, upstream demo deploy) looks stale next to the
  Ruby 3.3 `ci.yaml`/`e2e.yml` — confirm and remove or pin (noted, no
  issue filed; one-line follow-up for the next audit).

## Open questions

- Is 19,100 LOC of guard for ~5,800 LOC of site past the point of
  diminishing returns, or proportional to the bilingual × theme × page-kind
  matrix? The overlap map (#297) is the evidence base for that call.
- Should `tests/e2e/README.md` gain a per-file one-line index so the next
  audit does not re-derive ownership by reading 59 files?
