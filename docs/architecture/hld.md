# High-level design (HLD)

Status: active (thin). Owns only the system-context diagram; all detail
defers to the specs below.

```text
Reader ──HTTPS──▶ Cloudflare (DNS + TLS + email obfuscation)
                    │
                    ▼
              GitHub Pages (Jekyll --safe build from master)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Static HTML  Giscus embed  GitHub Discussions
   (+ feeds,    (post pages,   (comment store;
   sitemap)     prod only)     only third party)
```

- Context and area map: `docs/architecture/overview.md`.
- Request path and trust boundaries: `docs/architecture/system-architecture.md`.
- Build pipeline stages: `docs/architecture/sequence.md`.
- Detail specs: `docs/architecture/content-pipeline.md` (Liquid), `docs/architecture/styling.md` (SCSS),
  `docs/architecture/javascript.md` (JS), `docs/architecture/data-model.md` (`_data/`).
