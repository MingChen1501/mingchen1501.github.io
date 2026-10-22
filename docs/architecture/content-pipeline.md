# Content pipeline

Purpose: how raw posts become bilingual pages — layouts, includes,
collections, cross-language links, taxonomy, and comments.

## Current structure

Layouts (`_layouts/`, 5 files, 579 LOC):

- `base.html` (29 lines): shell. `head.html` → skip link → `header.html`
  → `{{ content }}` → `footer.html` → `sub-footer.html` (scripts).
- `home.html` (192 lines, `layout: base`): paginated EN/VI index.
  Post-card loop renders the shared `post-card.html` (~L90) +
  `site-sidebar.html` (~L189).
- `post.html` (260 lines, `layout: base`): article page. Reading-progress
  bar + back-to-top button (~L19-21), `reading-time.html` (~L66),
  `post-toc.html` (~L93), `share.html` (~L104), `post-tags.html` (~L145),
  `comments.html` (~L255).
- `tag.html` (81 lines, `layout: base`): per-tag listing. Post-card loop
  renders the shared `post-card.html` (~L67, `show_tags=false`) +
  `site-sidebar.html` (~L78).
- `page.html` (17 lines, `layout: base`): static pages + `vi-fallback-notice.html`.

Includes (`_includes/`, 23 files, 1,420 LOC). Largest: `site-sidebar.html`
(302 lines), `head.html` (121 lines). Every include has at least one caller
outside itself (no orphan includes, 2026-10-20). `post-card.html`
(38 lines, #293) is the single home/tag list-item markup
(`post-thumbnail.html` + `reading-time.html` + description-first excerpt +
home chips); both list layouts call it with `post` + `lang`.

## Bilingual `lang` / `ref` pipeline

- Collections: `site.posts` (`_posts/`, 7 files: 6 published EN posts plus
  the unpublished `codeblocks-ahoy` sample with no `lang`/`ref`) +
  `site.vi_posts`
  (`_vi_posts/`, 6 VI; `collections:` in `_config.yml:88-89`). Every post
  sets `lang` + a shared `ref` slug; EN and VI twins share the `ref`.
- `ref-urls.html` is the single resolver: given a `ref`, it exposes
  `ref_en` / `ref_vi` by scanning `site.posts`, `site.vi_posts`, and
  `site.pages` with plain `for` loops (filters would crash on nil
  `site.vi_posts` in the `_config_theme-dev.yml` CI build). First match
  wins (paginate page-2..N duplicates sort after). Callers (4):
  `lang-alternates.html`, `sitemap-alternates.html`, `lang-switcher.html`,
  `vi-fallback-notice.html`.
- Inline `{% if <x>_lang == 'vi' %}` string switches appear in 9+ files
  (`base.html:13,17`, `home.html:51,77,84,124,188`, `post.html:19,21,34,129,144,157,211,251`,
  `tag.html:20,55,73,77`, plus `share.html`, `head.html`,
  `site-sidebar.html`, `social.html`, `ref-urls.html`). No i18n filter or
  dictionary; each label is a one-off conditional.
- Nil-guards for undefined `site.vi_posts` repeat in ~8 files
  (`home.html`, `tag.html`, `post.html`, `head.html`, `site-sidebar.html`,
  `ref-urls.html`, `sitemap-alternates.html`, `vi/feed.xml`,
  `vi/tags.md`).

## Taxonomy

Four pillar tags; single source of truth `_data/tag_labels.yml`
(labels, EN/VI slugs, one-line descriptions). Post front matter keeps the
canonical key (e.g. `doi-song`); `tag-label.html` resolves label + slug per
`page.lang`. Tag pages: `tags/*.md` (4 EN) + `vi/tags/*.md`, rendered by
`tag.html`; indexes `tags.md` + `vi/tags.md` iterate the same pillar list.
Known wart: the lifestyle pillar key is `doi-song` while the EN page file is
`tags/life.md` (slug mapping hides it, `tags/life.md:1-11`).

## Comments

- Comments: provider switch in `comments.html` (giscus/disqus/none),
  included only by `post.html:255`. Theme sync via `giscus-theme.js`.
  Guarded by `test_comments.py`, `test_comments_markup.py` and `test_giscus_comments.py`.

## Image delivery

Deliberate design, not a gap (owner decision on #307, option A — keep
today's behaviour; #112 remainder closed): content images ship as single
width-constrained files with runtime JS lazy-load. No `srcset` variants,
no build-time `loading="lazy"`.

- Lazy-load: `assets/js/lazy-load.js` (#86) marks every image inside
  `.post-content` / `.page-content` / `article.post` as `loading="lazy"`
  except the first, which stays eager (it can be the LCP element); images
  that already declare a loading mode are never touched. No-JS readers get
  eager loading.
- No `srcset`: GitHub Pages builds with `--safe`, so there is no
  image-resize pipeline, and `assets/img/` already uses ~4.2MB of the 6MB
  `script/check-images` budget — generated variants would exceed it.
- No build-time `loading="lazy"`: kramdown cannot inject the attribute, so
  it would need IAL attributes on ~20 images — churn with LCP risk for
  marginal gain over the JS rule.
- Revisit (options B/C on #307) only if image delivery moves off
  Pages-safe builds (a resize pipeline or CI-generated variants) or the
  asset budget is raised.

## Boundaries

- List rendering belongs in includes, not layouts: `post-thumbnail.html`,
  `reading-time.html`, `post-tags.html` are shared, and since #293 the
  card itself is too (`post-card.html`, called with `post` + `lang`;
  tag pages pass `show_tags=false` to keep tag cards chipless).
- `ref-urls.html` owns cross-language resolution; nothing else may scan
  both collections for a `ref`.
- Taxonomy labels/slugs belong in `_data/tag_labels.yml`, never hardcoded
  in layouts (EN `life` slug vs `doi-song` key is resolved there).

## Coupling notes

- `base.html` → `head` → `lang-alternates` → `ref-urls`; `header` →
  `nav-items` + `lang-switcher` → `ref-urls`; `sub-footer` owns all global
  `<script>` tags with post-only gating (`page.layout == 'post'`,
  `sub-footer.html:65`).
- `home.html` and `tag.html` both render list items through the shared
  `post-card.html` (#293), which in turn calls `post-thumbnail.html`,
  `reading-time.html`, and (home only) `post-tags.html`.

## Known findings

- #293 — implemented: the duplicate post-card block is extracted into the
  shared `post-card.html` (home passes `post` + `lang`, tag adds
  `show_tags=false`); the pre/post `_site` list output is DOM-identical
  (whitespace-only byte diff from the single canonical indentation).
- #294 — implemented: orphan one-offs removed per owner decision
  (2026-10-21, delete all, no redirects) — `gift.html`, `fullmonth/`
  (2.4MB), and the two stale root PDFs; kept the live resume PDF.
- I18n switches and `vi_posts` nil-guards are scattered, not hoisted
  (no issue filed; below the #293-#297 bar, noted for the next audit).

## Open questions

- Should `vi/` hand-paginated pages (`vi/pageN/`, #155) move to
  jekyll-paginate like EN, unifying the `ref: home` first-match rule?
- Should the `doi-song` key be renamed to match the EN `life` slug?
