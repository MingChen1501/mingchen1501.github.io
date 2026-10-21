# Security threat model

Status: active. Owns the threat list; the privacy inventory and the
deliberate no-CSP decision (#329) live in
`docs/architecture/privacy-csp.md`.

- Supply chain via Actions: third-party workflows and `npx`'d LHCI are
  the widest channel; pin versions, review workflow diffs as code.
- Secret leakage in build: no secrets are used by the build; Giscus IDs
  are public identifiers, not secrets. Never add tokens to `_config.yml`.
- Self-XSS via comments: out of scope — comments render inside the
  Giscus iframe under GitHub's origin, not this site's.
- Email harvesting: mitigated by Cloudflare email obfuscation; footer
  address rendering is guarded by `test_footer_email_a11y.py`.
- Dependency drift: gems via `Gemfile`/`bundle`; vendored `axe-core`
  helper is pinned in-tree. Upstream minima baseline:
  `docs/upstream-baseline-184.md`.
- No CSP by decision, not by omission: rationale in `privacy-csp.md`;
  revisit if a new third party is ever added.
