# Low-level design (LLD)

Status: active (thin). Owns no component detail; it records where each
component's design lives so there is exactly one owner per area.

| Component | Design owner |
|---|---|
| Layouts + includes (page assembly, cards, sidebar) | `docs/architecture/content-pipeline.md` |
| SCSS layers and cascade order | `docs/architecture/styling.md` |
| Vanilla JS modules and loading contract | `docs/architecture/javascript.md` |
| `_data/` files and taxonomy chains | `docs/architecture/data-model.md` |
| Front-matter + `_data/*.yml` schemas | `technical/schema-spec.md` |
| Giscus/Cloudflare/Pages integration | `technical/integration-spec.md` |
| Failure surfacing | `technical/error-handling.md` |
| Test layers and guard ownership | `docs/architecture/testing.md` |

Cross-component flows: `architecture/system-architecture.md` (request
path), `architecture/sequence.md` (build pipeline).
