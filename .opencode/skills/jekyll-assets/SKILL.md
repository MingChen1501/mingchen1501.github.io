---
name: Jekyll Assets
description: Image conventions, asset budgets, cache versioning, and lazy-load rules for the site. Use when adding images, touching assets/, or changing how fixed-URL assets are served or cached.
trigger: "Adding site images, touching assets/, or changing asset serving/caching: image conventions, budgets, check-images, cache-buster token, lazy-load."
---

# Site assets (images, cache versioning, lazy-load)

## Images

Site images live under `assets/img/<post-slug>/` (matching the post filename
slug) and are committed to git (compress-local by default; no CDN or Git LFS).
Scope split (canonical: `article-writer` skill): article issue attachment
images stay at direct attachment URLs and are never committed here —
this section covers committed local images only.

- Location: `assets/img/<post-slug>/`.
- Naming: lowercase, hyphen-separated, no spaces, quotes, diacritics, or
  special characters (e.g. `desktop-fedora.jpg`).
- Format: JPG (photos/screenshots) or WebP; PNG only for line-art needing
  lossless. Flatten alpha to white when converting to JPG.
- Size: long edge at most **1600px**, JPEG quality ~75 (progressive,
  optimized). Each file must be **<= 500KB** and the whole `assets/img/`
  folder must stay **<= 6MB**.
- Budget policy (#33): the 6MB total is a hard CI gate. Per-post guidance: aim
  for a post's images to total **<= 500KB** (no single post should add more
  than ~1MB without review). When the folder approaches 6MB, compress existing
  images harder or remove obsolete assets before raising the budget again;
  raising the cap requires a decision recorded in the tracking issue.
- Reference images with absolute site paths, e.g.
  `![Desktop](/assets/img/2026-01-01-Migrate-windows-11-to-fedora/desktop-fedora.jpg)`.
- Enforcement: `script/check-images` fails the build when any image exceeds
  500KB or `assets/img` exceeds 6MB. It runs in `script/cibuild` and as the
  "Check image sizes" step in `.github/workflows/ci.yaml`. See the README
  "Image conventions" section for the Pillow compress snippet (single source of
  truth — do not drift the numbers here).
- To change an image's content, publish it under a NEW filename — never
  rewrite it in place (image URLs are content-addressed, not versioned).
- Optimize with imagemin/squoosh before commit.

## List thumbnails (#226)

The home list and the tag pages (`_layouts/home.html`, `_layouts/tag.html`,
both languages) show post imagery again through one shared include,
`_includes/post-thumbnail.html`, with a fixed 120x90 (4:3) box for every
item (`_sass/minima/custom/_list-thumbs.scss`: `width`/`height` 120x90,
`object-fit: cover`, load-bearing `padding: 0` against the base `img` rule).

- Source chain per post: front matter `thumbnail`, else front matter `image`,
  else the first image of the post body, else the fixed built-in placeholder
  (`assets/img/placeholder.svg`). The include emits `width="120" height="90"`
  so the box is reserved before the first byte (no CLS).
- Local sources never load the original: `script/generate-thumbnails`
  pre-generates 240x180 cover-cropped WebP variants
  (`assets/img/thumbs/<slug>/<name>-240.webp`) committed inside the 6MB
  budget — rerun it after adding or changing a post image. The URL mapping
  lives in both the script and the include; keep them in sync.
- External attachment URLs cannot be resized: they keep the same fixed CSS
  box at full attachment bytes (documented bandwidth trade-off).
- Guards: `tests/e2e/test_list_thumbnails.py` (chain order, identical
  rendered box at 375/768/1280px, placeholder for imageless posts, box
  reserved with images blocked). Never touch `_layouts/post.html` for list
  thumbnails.

## Asset cache versioning (#61)

GitHub Pages serves `assets/**` (via Cloudflare) with `cache-control:
max-age=14400` from a FIXED URL, while the HTML is `max-age=600`. A warm
browser can thus pair NEW HTML with an OLD asset — that is how the #58 list
sidebar went missing on the live index page for up to four hours after the
deploy.

- Every fixed-URL asset linked from a template carries the build token assigned
  in `_includes/head.html`: `/assets/css/style.css?v={{ asset_version }}` and
  `/assets/img/favicon.ico?v={{ asset_version }}`, plus the deferred scripts
  in `_includes/sub-footer.html` (`lazy-load.js`, `nav-toggle.js`,
  `copy-code.js`, `lang-switch.js`, `theme-toggle.js`). A new fixed-URL asset needs
  the same `?v=` token.
- The token is `site.time` (epoch seconds). No plugin, works with GitHub Pages
  `--safe`, `bundle exec jekyll serve` and the E2E build; it changes on every
  build — a superset of "the asset changed", so cached assets can never pair
  with newer HTML. Cost: one re-fetch per deploy (~18KB stylesheet). A
  per-file content hash needs a Jekyll plugin, which GitHub Pages does not run.
- Guards: `tests/e2e/test_stylesheet_cache_version.py` (token present on every
  page, token changes with a new build and with a CSS change, a client holding
  the old stylesheet under the unversioned URL still gets the sidebar). See the
  README "Asset cache versioning (#61)" section for the full rationale.
- GitHub Pages serves `Cache-Control: max-age=600` for HTML, longer for
  assets; do not change caching without verifying Lighthouse.

## Lazy-load (#86)

Content images are lazy-loaded at runtime by `assets/js/lazy-load.js`: the
first image of a content block stays `loading="eager"` (it can be the LCP
element), the following ones become `loading="lazy"`. The script is a
fixed-URL asset, so it carries the same `?v=` build token as the stylesheet.
