# Architecture overview

Purpose: map of the whole site for audit and refactor work. Detail lives in
the per-area specs; this file stays a map and a set of numbers.

Canonical workflow rules live in `AGENTS.md`; the working method for
architecture work lives in the `architecture` skill. This directory records
the current state, not the process.

## What this site is

Personal bilingual (EN/VI) blog at `mingchen.id.vn`, forked from the Jekyll
minima theme, deployed with GitHub Pages from `master` (`CNAME`, `url` in
`_config.yml`). No custom plugins: every dynamic feature (search, comments,
theme toggle) is build-time Liquid plus vanilla JS, because Pages builds
with `--safe`.

## Area map

| Area | Spec | Size (2026-10-20) |
|---|---|---|
| Layouts + includes (Liquid) | `content-pipeline.md` | 5 layouts (541 LOC) + 24 includes (1,362 LOC) |
| SCSS layers | `styling.md` | 27 files, ~3,200 LOC |
| Vanilla JS modules | `javascript.md` | 11 files, 1,079 LOC |
| Data files + taxonomy | `data-model.md` | 3 files, 80 LOC |
| Tests + scripts + CI | `testing.md` | 62 e2e files (~19,500 LOC), 14 scripts, 5 workflows (597 LOC) |
| Content (posts) | `content-pipeline.md` | 7 EN files (6 published + 1 unpublished sample) + 6 VI posts |
| Decisions | `decisions/` | ADR template + first ADRs |

348 tracked files total (`git ls-files`, excluding `_site/`).

Counting convention: raw `wc -l` per area; the E2E headline counts `test_*.py` lines.

## Bloat headline numbers

- The E2E suite (~19,500 LOC) is the largest area of the repo — larger than
  layouts + includes + SCSS + JS combined (~6,200 LOC). See `testing.md`
  for the overlap clusters and follow-up #297.
- `assets/img/` holds 4.2MB of the 6MB budget (`script/check-images`);
  the largest single file is 236KB against the 500KB limit.
- Unbudgeted published weight is gone (#294, owner decision 2026-10-21:
  delete all, no redirects, 404 acceptable): `gift.html` (209-line
  standalone page, zero inbound refs), `fullmonth/` (2.4MB standalone
  invitation page for the Nov 2025 event + images), and the two stale
  PDFs at `assets/` root (`CV-Tran-Cong-Minh-14-5-23.pdf`,
  `resume-26-5-23.pdf`, 656KB each, unreferenced) were removed —
  ~3.7MB freed. Kept: `assets/resume-tran-cong-minh.pdf` (72KB, live
  on `portfolio.md` / `vi/portfolio.md`).
- Unreachable code: the three solarized skins (no importer while
  `minima.skin: auto`). Follow-up: #296.

## Follow-up refactor issues (from #290)

1. #293 — shared post-card include for home/tag lists (duplicated card
   markup in `_layouts/home.html` / `_layouts/tag.html`).
2. #294 — implemented: orphan one-offs removed per owner decision
   (2026-10-21, delete all, no redirects) — `gift.html`, `fullmonth/`,
   and the two stale root PDFs; kept `assets/resume-tran-cong-minh.pdf`
   (live on portfolio pages). `risk-medium` (reader-visible URLs).
3. #295 — hoist the thrice-pasted `asset_version` token into one include.
4. #296 — delete the unreachable solarized skins.
5. #297 — map and consolidate overlapping E2E guards.

All `risk-low` except #294. None is implemented here.

## Boundaries

- `docs/architecture/` records the tree as it is; behavior changes go
  through normal PRs, one per issue.
- `_site/` and `.jekyll-cache/` outputs are never hand-edited and never
  specified here beyond their generators. `sitemap.xml` and `llms.txt`
  are Liquid sources (hreflang alternates, bilingual link map) edited
  like other pages; `robots.txt` is static.
- `AGENTS.md` and `.opencode/` stay excluded from the built site
  (`_config.yml` `exclude:`, leak-checked on every build).
