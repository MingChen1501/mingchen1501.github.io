# Runbook

Status: active. Owns the when-it-breaks playbook.

- Geo redirect traps VN readers in Vietnamese (#423, Cloudflare
  dashboard — not in this repo): the VN `/ -> /vi/` redirect rule must
  skip requests carrying the reader's explicit choice, or EN is
  unreachable from VN. Rule shape: `(ip.geoip.country eq "VN" and
  http.request.uri.path eq "/" and not http.cookie contains "lang=en")`
  -> 302 to `/vi/`. First visits still land on `/vi/`; the switcher
  writes `lang=en|vi` (`path=/`, one year, `SameSite=Lax`), so EN sticks
  on reload and navigation. No cache change: page bytes are static per
  URL, the cookie varies nothing.
- Jekyll build red: run `bundle exec jekyll build --trace` locally,
  fix the Liquid/data error (`_data/*.yml` syntax is the usual suspect),
  push again. `master` keeps serving the last good deploy meanwhile.
- Image guards red: run `script/check-images`; recompress or drop the
  offending file (budgets: 500KB/file, 6MB total).
- Asset-budget red: `script/asset-budget.sh` ceilings moved — find the
  grown file, gate or trim it (precedent: #318, #342).
- E2E guard red: reproduce with `python -m pytest tests/e2e/<file> -v`
  against a local build; browser tests reuse the shared build via
  `E2E_PREBUILT_SITE`.
- LHCI red: fetch the report artifact (`.lighthouseci/`, uploaded per
  `e2e.yml` run) and check which category regressed; images and
  render-blocking CSS are the usual suspects.
- Classifier dispute: run `script/classify-content-only` on the PR diff;
  force the full suite with workflow_dispatch (`full=true`).
- Pages serving stale or Cloudflare issue: not actionable in this repo —
  confirm origin vs edge before filing anything.
