# JavaScript

Purpose: inventory of the vanilla-JS layer — what runs on which page, and
the loading contract.

## Current structure

`assets/js/` holds 11 files, 1,502 LOC, no bundler, no framework, no
third-party runtime (giscus/disqus SDKs load only inside the comments
embed). Every file has at least one `<script>` caller (no orphan JS).

| File | Lines | Role | Loaded |
|---|---|---|---|
| `site-utils.js` | 32 | shared helpers (clipboard, DOM-ready, lang sniff, #246) | every page, first |
| `lazy-load.js` | 19 | content-image lazy loading (#86) | every page |
| `nav-toggle.js` | 45 | mobile nav disclosure (#114) | every page |
| `copy-code.js` | 53 | copy button on `pre > code` (#126) | every page |
| `lang-switch.js` | 102 | `ref`-based language switch | every page |
| `theme-toggle.js` | 79 | explicit light/dark pin (#220) | every page |
| `lightbox.js` | 292 | image lightbox dialog (#223) | every page |
| `share.js` | 60 | share intents + copy-link | posts only (#253) |
| `reading-progress.js` | 80 | progress bar + back-to-top | posts only (#253) |
| `giscus-theme.js` | 100 | repaint giscus iframe on theme flip (#258) | prod comments only |
| `toc-spy.js` | 640 | ToC scroll-spy + auto-expand (#345) | posts only |

Shipped byte budgets (`script/asset-budget.sh`, re-measured 2026-10-22):
page-source 10,069 B (5 files), post-source 55,241 B (11 files, prod).
Ceilings: page 23,552 B, post 59,904 B, CSS main 57,344 B, syntax
companion 19,456 B.
Guarded by `test_asset_budget.py`. (#342 removed `search.js`, 234 lines /
~8KB, with the search page.)

## Boundaries

- Shared primitives live only in `site-utils.js`; feature scripts must not
  reimplement clipboard/DOM-ready/lang-sniff (guarded by
  `test_site_utils.py`).
- Post-only gating owns `sub-footer.html:53` (`page.layout == 'post'`);
  new scripts default to the smallest page set that needs them.
- Every first-party `<script>` is `defer`red with the `?v=` build token
  (assigned once in `_includes/asset-version.html`, included at the top
  of `sub-footer.html`); the theme bootstrap in `head.html:83`
  is the only blocking inline script (must run before first paint).

## Coupling notes

- `sub-footer.html` is the single script manifest: 5 global scripts +
  5 post-only scripts.
- `lightbox.js` couples to post content images and `_lightbox.scss`.
- `toc-spy.js` (640 lines, largest module) couples to post ToC markup
  and `_toc.scss`.
- `giscus-theme.js` couples to the `data-*` mapping attributes in
  `comments.html:15-28`; either side changing the theme names breaks the
  other (guarded by `test_giscus_comments.py`, needs `JEKYLL_ENV=production`).

## Known findings

- #295 — implemented: the `asset_version` token lives once in
  `_includes/asset-version.html`, included by `sub-footer.html`
  (plus `head.html`).
- `toc-spy.js` is the largest single module (~24.5KB, ~44% of all JS
  bytes); it is single-purpose and correctly gated, so size alone is not
  a finding — recorded here so the next audit has a baseline.

## Open questions

- Should `copy-code.js` (53 lines, code pages only) join the post-only
  gate, or do non-post pages carry code blocks?
