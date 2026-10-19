# Site conventions (#173)

Follow-up of the #168 clean-code audit: load-bearing conventions that live
in code comments, collected in one short page. Each section names its single
source of truth — change the source, not the copies. Full workflow details
live in `AGENTS.md` and the `jekyll-*` skills; this page only records
*what* the conventions are and *where* they are enforced.

## Asset cache versioning (#61)

GitHub Pages (through Cloudflare) serves `assets/**` with
`cache-control: max-age=14400` (four hours) from a fixed URL, while HTML is
`max-age=600`. Every fixed-URL asset therefore carries the build token
`site.time` (epoch seconds): the stylesheet and favicon in
`_includes/head.html`, the deferred scripts in `_includes/sub-footer.html`.
Images are NOT versioned — their URLs are content-addressed by convention, so
a changed image ships under a NEW filename, never rewritten in place.
Single source: the `asset_version` assignment in `_includes/head.html`
(mirrored in `_includes/sub-footer.html`). Guard:
`tests/e2e/test_stylesheet_cache_version.py`. Rationale: see the README
"Asset cache versioning (#61)" section.

## List sidebar height budget (#63)

The shared `_includes/site-sidebar.html` must fit beside the post list with
no scrollbar of its own: capped thumbnails, two-line titles, collapsed tag
rows; pinned (`position: sticky`) only where it fits (desktop width AND at
least 720px viewport height). Styles: `_sass/minima/custom-styles.scss`.
Guard: `tests/e2e/test_sidebar_layout.py`. Never add `thumb-*` files or crop
thumbnails — `assets/img/` runs close to its budget (below).

## Image budget (#33, consolidated in #171)

Each file <= 500KB, `assets/img/` total <= 6MB, long edge <= 1600px.
Single source of truth: `script/image-budget.sh` (sourced by
`script/check-images`, parsed by `tests/e2e/test_check_images.py`). Do NOT
redeclare the numbers anywhere else. Per-post guidance: aim for <= 500KB per
post; raising the cap needs a decision recorded in the tracking issue.
Rules and the Pillow compress snippet: see the README "Image conventions"
section and the `jekyll-assets` skill.

## Pagination sources (#155, #176)

`paginate:` in `_config.yml` is the only per-page value. `jekyll-paginate`
reads it for the English home (`/`, `/page2/…` over `site.posts`); the
Vietnamese home (explicit `vi/pageN/index.html` files with `vi_page_num`
front matter — v1 supports one stream only) slices `site.vi_posts` in
`_layouts/home.html` and emits `prev`/`next` in `_includes/head.html` from
the same `site.paginate` (`default: 5` covers only configs without it, e.g.
upstream theme-dev).

## Theme-dev leftovers (not the real workflow)

`script/bootstrap`, `script/server`, `script/build`, `script/cibuild`, and
`_config_theme-dev.yml` target the upstream minima sample site, not the
personal posts. Preview with `bundle exec jekyll serve`, build with
`bundle exec jekyll build --trace`. The `gem build minima.gemspec` step in
`script/cibuild` is kept deliberately (see its inline note); removing the
theme-dev path is the #169 divergence decision, out of scope here.
