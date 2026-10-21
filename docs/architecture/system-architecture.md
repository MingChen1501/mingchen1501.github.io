# System architecture

Status: active (thin). Owns the request-path view; build detail lives in
`architecture/sequence.md`, component detail in the per-area specs.

```text
Reader browser
  │  HTTPS (Cloudflare terminates TLS; email obfuscation rewrites
  │  plaintext addresses in served HTML)
  ▼
Cloudflare edge (DNS + cache + TLS)
  │  origin pull on miss
  ▼
GitHub Pages (serves the Jekyll --safe build of master; CNAME +
_config.yml url pin the canonical domain mingchen.id.vn)
  │
  ├─ static HTML/CSS/JS, feeds, sitemap, llms.txt (first party only)
  └─ post pages (production): iframe + client.js from giscus.app,
     which reads/writes GitHub Discussions (see
     technical/integration-spec.md for trust boundaries)
```

What is trusted: Pages build env and first-party output fully; Cloudflare
for transport only; Giscus/Discussions as an untrusted embed (lazy-loaded,
theme-synced, never blocking render). Threat view:
`technical/security-threat-model.md`.
