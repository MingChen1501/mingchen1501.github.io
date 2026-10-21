# Integration specification

Status: active. Owns the trust/timeout/failure contract of each external
integration; privacy inventory lives in `docs/architecture/privacy-csp.md`.

- GitHub Pages build env: Jekyll `--safe` (no custom plugins), Ruby 3.3
  in CI; `master` deploys, `CNAME` + `_config.yml` `url` pin the canonical
  domain. Trusted fully. Failure: build error blocks deploy and fails CI.
- Giscus (`giscus.app/client.js`, Discussions store): untrusted embed,
  lazy-loaded (`data-loading="lazy"`), rendered on post pages in
  production builds only. No timeout control (third-party script); failure
  mode is degraded comments, never a broken article. Theme synced at
  runtime (#258). Config: `_config.yml` `giscus:`; IDs need owner
  confirmation.
- Cloudflare: DNS + TLS termination + email obfuscation; trusted for
  transport only, never for content integrity. Failure mode is
  reader-visible but outside this repo's control (see
  `operations/runbook.md` for what is actionable here).
