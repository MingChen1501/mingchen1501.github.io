# Environment

Status: active. Owns the config/env matrix.

| Item | Role |
|---|---|
| `_config.yml` | production config: canonical `url`, minima skin `auto`, feeds/SEO/paginate, `vi_posts` collection, Giscus IDs |
| `_config_theme-dev.yml` | dev-content preview config (theme work, not production) |
| `JEKYLL_ENV=production` | enables production-only rendering (Giscus comments) |
| `E2E_PREBUILT_SITE` | points browser tests at the one shared CI build |
| `E2E_VISUAL=1` | opts local runs into visual compares (always on in CI) |
| `full=true` (workflow_dispatch) | forces the full suite on a content-only PR |

Ruby 3.3 in `ci.yaml`/`e2e.yml`; `demo_site.yml` still on Ruby 2.7
(stale candidate, see `docs/architecture/testing.md`).
