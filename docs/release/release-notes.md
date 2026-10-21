# Release notes

Status: active. Changelog driven by merged PRs; newest first, seeded with
the recent wave (2026-10-21).

- #352 — role-footer signing for every artefact.
- #349 — static client-side search removed (page + `search.js` + guard).
- #335/#336 — no-JS search fallback, 404 suggestions, VI alt text.
- #334 — Giscus exposure wording fix on EN/VI about pages.
- #329/#332 — deliberate no-CSP decision recorded (`privacy-csp.md`).
- #328/#331 — sidebar fallback never suggests posts newer than the page.
- #330 — orchestration sequel pair with bidirectional cross-links.
- #320/#325 — one shared site build across E2E and Lighthouse.
- #319/#324 — Lighthouse reports uploaded from dot-directory.
- #318/#323 — lightbox.js and copy-code.js gated to post pages.
- #322 — Tet 2023 and coffee originals recompressed in place.
- #313/#317 — EN tag-page visual coverage gap and sidebar thumbnail chain.
- #316 — generated-file claim fix, audit numbers refresh.
- #310/#315 — shared og image across the orchestration pairs.
- #309/#314 — EN post alt text parity (#147).

There is no versioning and no staged release: every squash merge to
`master` ships via Pages. Rollback: `release/rollback.md`.
