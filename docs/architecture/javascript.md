# JavaScript

Purpose: inventory of the vanilla-JS layer — what runs on which page, and
the loading contract.

## Current structure

`assets/js/` holds 11 files, 1,079 LOC, no bundler, no framework, no
third-party runtime (giscus/disqus SDKs load only inside the comments
embed). Every file has at least one `<script>` caller (no orphan JS).

| File | Lines | Role | Loaded |
|---|---|---|---|
| `site-utils.js` | 32 | shared helpers (clipboard, DOM-ready, lang sniff, #246) | every page, first |
| `lazy-load.js` | 19 | content-image lazy loading (#86) | every page |
| `nav-toggle.js` | 33 | mobile nav disclosure (#114) | every page |
| `copy-code.js` | 51 | copy button on `pre > code` (#126) | every page |
| `lang-switch.js` | 102 | `ref`-based language switch | every page |
| `theme-toggle.js` | 79 | explicit light/dark pin (#220) | every page |
| `lightbox.js` | 289 | image lightbox dialog (#223) | every page |
| `share.js` | 60 | share intents + copy-link | posts only (#253) |
| `reading-progress.js` | 80 | progress bar + back-to-top | posts only (#253) |
| `giscus-theme.js` | 100 | repaint giscus iframe on theme flip (#258) | prod comments only |
| `search.js` | 234 | offline search over `search.json` (#221) | search pages only |

Shipped byte budgets (`script/asset-budget.sh`, measured 2026-10-20):
page 21,225 B (7 files), post 29,689 B (10 files, prod), search
28,961 B (8 unique files). Guarded by `test_asset_budget.py`.

## Boundaries

- Shared primitives live only in `site-utils.js`; feature scripts must not
  reimplement clipboard/DOM-ready/lang-sniff (guarded by
  `test_site_utils.py`).
- Post-only gating owns `sub-footer.html:65` (`page.layout == 'post'`);
  search-only loading owns `_includes/search.html:77-78`. New scripts
  default to the smallest page set that needs them.
- Every first-party `<script>` is `defer`red with the `?v=` build token
  (assigned once in `_includes/asset-version.html`, included at the top
  of `sub-footer.html`); the theme bootstrap in `head.html:82`
  is the only blocking inline script (must run before first paint).

## Coupling notes

- `sub-footer.html` is the single script manifest: 7 global scripts +
  2 post-only scripts. `search.html` re-tags `site-utils.js` + `search.js`
  (browser-cache hit, counted once in budgets).
- `lightbox.js` (289 lines, largest module) couples to post content images
  and `_lightbox.scss`; `search.js` (234 lines) couples to the `search.json`
  field contract (title/desc/URL/lang/tags/date).
- `giscus-theme.js` couples to the `data-*` mapping attributes in
  `comments.html:14-44`; either side changing the theme names breaks the
  other (guarded by `test_giscus_comments.py`, needs `JEKYLL_ENV=production`).

## Known findings

- #295 — implemented: the `asset_version` token lives once in
  `_includes/asset-version.html`, included by `sub-footer.html`
  (plus `head.html` and `search.html`).
- `lightbox.js` and `search.js` together are ~48% of all JS bytes; both
  are single-purpose and correctly gated, so size alone is not a finding —
  recorded here so the next audit has a baseline.

## Open questions

- Should `copy-code.js` (51 lines, code pages only) join the post-only
  gate, or do non-post pages carry code blocks?
- Is the `search.html` double-tag of `site-utils.js` worth a comment in
  the manifest, or a structural dedup?
