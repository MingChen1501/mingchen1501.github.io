# Error handling

Status: active. Owns how each failure class surfaces to readers and to CI.

| Failure | Reader sees | CI sees |
|---|---|---|
| Broken internal link / bare URL in post | 404 or unlinked text | `test_internal_link_crawl.py`, `test_post_bare_urls.py` fail |
| Failed Jekyll build | stale Pages site (no deploy) | `cibuild` / CI matrix red |
| Missing/oversize asset | broken image or slow page | `script/check-images`, `test_check_images.py`, `test_asset_budget.py` |
| Removed URL with no redirect (e.g. #294 orphans) | 404 page with suggestions (#335) | `test_404.py` |
| Unknown highlight slug | silent fallback to newest posts (known footgun) | `test_sidebar_layout.py` only |
| Giscus outage | empty/degraded comment section, article intact | nothing (third party, unmonitored) |
| Visual regression | wrong-looking page | visual compare baselines (CI full suite) |

Runbook for each row: `operations/runbook.md`.
