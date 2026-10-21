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
- Request path and trust boundaries: `architecture/system-architecture.md`.
- Build pipeline stages: `architecture/sequence.md`.
- Detail specs: `content-pipeline.md` (Liquid), `styling.md` (SCSS),
  `javascript.md` (JS), `data-model.md` (`_data/`).
