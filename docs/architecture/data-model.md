# Data model

Purpose: the three `_data/` files — what each owns and who reads it.

## Current structure

`_data/` holds 3 files, 80 LOC total.

- `highlights.yml` — per-language sidebar highlight slugs (`en:` / `vi:`,
  ≤5, ordered). Unknown/unpublished slugs are skipped silently; an
  empty/missing list falls back to the 5 newest posts of that language.
  Sole reader: `_includes/site-sidebar.html:100`. Content-only path
  (#229): editing it skips the browser matrix.
- `tag_labels.yml` — taxonomy source of truth: canonical key → `en`/`vi`
  labels, `slug_en`/`slug_vi`, one-line `description_en`/`description_vi`.
  Readers: `tag-label.html`, `tags.md`, `vi/tags.md`, tag pages. Bodies of
  `tags/*.md` + descriptions here must be kept in sync by hand (header
  comment in the file).
- `image_hosts.yml` — temporary (#195) allowlist for external article
  images (GitHub issue attachments until dedicated storage exists):
  `scheme: https`, `allowed_hosts`, `attachment_path_prefixes`. Readers:
  `script/check-external-images`, `test_external_images.py`, plus the
  README image-conventions section and `docs/conventions-173.md`. The file
  header records the full migration checklist (repoint, rewrite URLs,
  drop the Lighthouse exemption, update docs).

## Boundaries

- Labels, slugs, and descriptions belong in `tag_labels.yml` — never
  hardcoded in layouts (the `doi-song` key vs `life` EN slug split is
  resolved there, not in `tag.html`).
- `highlights.yml` is the only `_data/` file on the content-only path;
  `tag_labels.yml` and `image_hosts.yml` changes run the full CI suite.
- `image_hosts.yml` is temporary by design; every consumer added for #195
  must be easy to remove (see ADR-002).

## Coupling notes

- Sidebar chain: `highlights.yml` → `site-sidebar.html:100-105` →
  `home.html` / `tag.html` layouts. Slug typos fail silently (skip +
  fallback), so the highlights guard (`test_sidebar_layout.py`) is the
  only tripwire.
- Tag chain: `tag_labels.yml` ↔ `tags/*.md` / `vi/tags/*.md` bodies
  (manual sync) → `tags.md` / `vi/tags.md` indexes → `tag.html` pages.
  Guarded by `test_tag_localization.py` (453 lines) and
  `test_tag_index_descriptions.py`.
- Image-host chain: `image_hosts.yml` → guard script + E2E test + README
  + `docs/conventions-173.md`. Four consumers of one 20-line file; the
  migration must touch all four.

## Known findings

- Silent-skip semantics in `highlights.yml` (typo → fallback, no error)
  have caused no incident but are a known footgun; a warning-level lint
  would be a valid micro-issue (noted, no issue filed).
- Tag descriptions live in two places (per-tag page bodies +
  `tag_labels.yml`) with manual sync; drift is guarded only by
  `test_tag_index_descriptions.py`.

## Open questions

- Should `highlights.yml` gain a CI warning on unresolvable slugs?
- When dedicated image storage lands, who runs the #195 migration
  checklist in `image_hosts.yml`?

## Series (proposed, ADR-004)

Series support is decided but not yet implemented: no `_data/` file, no
template, and no series post exist — this section records the contract so
Phase 2 only adds front matter, not template rewrites.

- Planned `_data/series_labels.yml` — series source of truth, mirroring
  `tag_labels.yml`: canonical language-neutral key → `en`/`vi` titles,
  `slug_en`/`slug_vi`, `description_en`/`description_vi`, plus
  `coming_soon_en`/`coming_soon_vi` labels for unlinked gap positions
  (concrete keys Phase 2 templates read). Templates never
  hold series copy. Full CI suite on change (like `tag_labels.yml`); series
  front matter on posts stays on the content-only path (#229).
- Front matter: `series: <key>` + `series_order: <int>` (1-based, no
  per-post `series_title`). A post belongs to at most one series: `series`
  is a scalar key; the array form is out of scope and Phase 2 validators
  must reject a sequence value. Strict validation — `series` without
  `series_order` (or the reverse, non-integer/non-positive order, duplicate
  order within one series + language) fails the guard; order is never
  derived from the date.
- i18n: EN/VI twins share the key via the `lang`/`ref` pipeline (ADR-003)
  and must share `series_order` (parity guard). VI may lag behind EN:
  nav/index render within the reader's language, missing twins are skipped
  by prev/next and unlinked on the index — never cross-linked, never 404
  (same rule class as #93/#172).
- Rendering (Phase 2): `<nav class="series-nav">` (part N of M, prev/next
  with titles, index link) inside `.post-main` after `share.html`, sidebar
  untouched; index pages at `/series/<slug>/` + `/vi/series/<slug>/` on a
  `tag.html`-mirroring layout; installments stay normal posts in all lists.
  "Part N of M" numbering is global, not per-language (M is the highest
  published order in the reader's language, never a count), so gaps render
  as unlinked coming-soon labels and a "Part 5 of 3" can never occur.
  JSON-LD gains `isPartOf` + `position`.
- Full contract, feature interactions (#343/#344/#345, RSS/sitemap/JSON-LD,
  CI classification), guard plan, and open questions: see
  [`adr-004-series-posts.md`](decisions/adr-004-series-posts.md).
