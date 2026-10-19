# Jekyll built-in plugins vs custom code — audit (#90)

Date: 2026-10-20. Scope: analysis only, no replacements implemented.
Constraints: GitHub Pages builds with `--safe` (Jekyll 3.9.5); only the
`github-pages` gem whitelist is available in production. CI additionally builds
with Jekyll 4.2 (`script/cibuild` matrix), so any future plugin use must work
on both. There is no `_plugins/` directory — the site is already `--safe`
clean. There are no `.coffee` assets, no gist embeds, no emoji/mention markup
and no `site.github` usage anywhere in templates or posts (verified by grep).

## 1. Whitelisted plugins vs custom code

| Plugin (Pages-whitelisted) | In use / overlaps custom code? | Verdict |
|---|---|---|
| `jekyll-feed` | Enabled (`_config.yml`). Emits English `/feed.xml` only. `vi/feed.xml` is a line-by-line Liquid mirror over `site.vi_posts` (#98) because the plugin emits one feed per site. | **Keep** both. The plugin cannot do the second language. |
| `jekyll-seo-tag` | Enabled. Canonicals + prev/next head links come from it (#89). | **Keep**. |
| `jekyll-sitemap` | Available but **not** enabled. `sitemap.xml` is hand-built Liquid (#81, bilingual alternates #98) emitting per-URL `xhtml:link` hreflang alternates via `_includes/sitemap-alternates.html`. | **Keep custom, do NOT enable the plugin.** The plugin cannot emit hreflang alternates, and enabling it would collide on the `/sitemap.xml` URL. |
| `jekyll-paginate` (v1) | Enabled, single stream over the English-only `site.posts`. The Vietnamese home (`/vi/`) is deliberately unpaginated (#93) — v1 supports one stream only and `jekyll-paginate-v2` is not whitelisted. | **Keep**. |
| `jekyll-redirect-from` | Enabled. Used by `_vi_posts/*` (`redirect_from:` pre-#93 URLs) and `vi/about.md`. | **Keep**. |
| `jekyll-include-cache` | Available, **not** enabled. Only genuine candidate: `_includes/site-sidebar.html` renders identically for every page of the same language, so `{% include_cached site-sidebar.html lang=page.lang %}` could skip re-rendering it per page. Needs a small refactor (the include currently reads `page.lang` itself; cached includes vary only on explicit params) and the gain is unproven — the include does a handful of `where` lookups over a small post list. | **Follow-up experiment** → issue #102. Keep as-is until measured. |
| `jekyll-default-layout` | Available, unused. No `defaults:` key in `_config.yml`; every post/page declares `layout:` explicitly. Could drop the boilerplate, but that churns every post, weakens the `jekyll-post` authoring template, and saves nothing at build time. | **Keep explicit. No follow-up.** |
| `jekyll-github-metadata` | Nothing replicates `site.github` (no usage found). No custom repo/org metadata code exists. | **No action.** |
| `jekyll-relative-links` | No custom link-rewriting code. Posts already use absolute site paths (`/assets/img/<slug>/…`); the only relative links live in the standalone `fullmonth/` demo page. | **No action.** |
| `jekyll-titles-from-headings` | Every post ships an explicit `title:` (taxonomy template, #26). No title-less content. | **No action.** |
| `jekyll-optional-front-matter` | Every buildable `.md` has front matter. Files without it (`README.md`, `AGENTS.md`, `.opencode/…`) are already in `exclude:` (#82). | **No action.** |
| `jekyll-readme-index` | `index.md` exists; `README.md` is excluded from the build (#82) and must stay an author-facing file, not the homepage. | **No action.** |
| `jekyll-gist` | No `{% gist %}` tags in any post. | **No action.** |
| `jemoji` / `jekyll-mentions` | No emoji shortcodes or `@mention` markup in content (only code samples / email addresses). | **No action.** |
| `jekyll-avatar` | No avatar usage. | **No action.** |
| `jekyll-coffeescript` | No `.coffee` assets. | **No action.** |
| `jekyll-commonmark` | Markdown goes through kramdown GFM (`kramdown-parser-gfm`); no custom markdown handling to replace. | **No action.** |

Net result: **1 follow-up experiment out of 18 plugins** (`jekyll-include-cache`).
Everything else is either already used, has no overlapping custom code, or is
beaten by the custom implementation (sitemap hreflang, second-language feed).

## 2. Minima theme built-ins vs custom code

`minima.*` keys already consumed: `skin: classic`, `date_format`,
`show_excerpts: true`, `social_links` (5 entries), `nav_pages`
(`about.md`, `portfolio.md`, `tags.md`). All standard.

| Custom code | Built-in alternative? | Verdict |
|---|---|---|
| `_sass/minima/custom-styles.scss` (442 lines: post two-column #45, `.site-layout` grid #58, sticky rules #63, tag chips #45/#47, tag index #46, sidebar blocks) | Minima exposes only skins + variables; no variable produces layout grids, sticky columns or chip components. | **Keep.** Nothing to replace. |
| `_sass/minima/custom-variables.scss` | Currently the stock 1-line placeholder hook. | **Keep** as the override hook; no action. |
| `_sass/minima/initialize.scss`, `assets/css/style.scss` | Standard theme wiring (skin import + partial order). | **Keep.** |
| `_includes/head.html` additions: `?v={{ site.time }}` cache-buster (#61), jsdelivr preconnect (#86), per-language `feed_meta` (#98), hreflang via `lang-alternates.html` (#93) | No theme/plugin equivalent (content-hash versioning needs a non-whitelisted plugin; the bilingual feed/hreflang logic is site-specific). | **Keep.** |
| `_includes/site-sidebar.html` + `_data/highlights.yml` | Custom curation (per-language slug lists, newest-posts fallback, collapsed tag rows). See `jekyll-include-cache` row above for the only option. | **Keep** (+ experiment #102). |
| `_includes/lang-alternates.html`, `lang-switcher.html`, `sitemap-alternates.html`, `vi-fallback-notice.html` | Bilingual machinery (#93); no plugin available under `--safe` (no polyglot plugin whitelisted). | **Keep.** |
| `_includes/post-tags.html` | Single source of chip markup (#45/#47) linking inside the page language. No equivalent. | **Keep.** |
| `_includes/comments.html` (giscus/disqus switch, `comments.dev` gate) | Theme has no comment provider switch. | **Keep.** |
| `_includes/footer.html` (Font Awesome pin), `google-analytics.html` (gtag), `header.html`/`nav-items.html`/`social.html`/`sub-footer.html` | Site chrome overrides; `social.html` feeds off the already-standard `minima.social_links`. | **Keep.** |
| `_layouts/*` (base/home/page/post/tag) | Full overrides for the bilingual list/tag shells; `home.html`/`tag.html` encode the paginator-vs-collection split (#93). `jekyll-default-layout` cannot express this. | **Keep.** |
| `assets/js/lazy-load.js` (#86) | No Jekyll built-in; complements (not duplicates) the static `loading=` attributes on sidebar thumbnails — it covers Markdown content images. Same `?v=` versioning rule as the stylesheet. | **Keep.** |
| `tests/e2e/` guards, `script/check-images` (500KB/file, 6MB total) | Repo-specific policy, not plugin territory. | **Keep.** |
| `sitemap.xml` / `vi/feed.xml` Liquid templates | See plugin table: beat the plugins they stand in for. | **Keep.** |

## 3. Follow-up implementation issues

- #102 — Experiment: `{% include_cached %}` for `_includes/site-sidebar.html`
  (the single candidate worth measuring; everything else is keep/no-action).

No other replacements were found, so no further follow-ups are filed. If a
future audit finds new overlap, file one issue per replacement as usual.

## 4. How this was verified

- `grep` over layouts/includes/posts/collections: no `site.github`,
  `include_cached`, gist/emoji/mention usage; every buildable `.md` has front
  matter; no `defaults:` key; all posts carry explicit `title:`.
- `bundle exec jekyll build` passes with `docs/` excluded (leak check: no
  `docs/` or `AGENTS.md` in `_site`); `script/check-images` untouched (no
  image changes); static E2E guard `test_comments_markup.py` passes.
