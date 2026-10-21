# Data dictionary

Status: active. Owns the front-matter field reference; structural detail
lives in `docs/architecture/data-model.md` and `technical/schema-spec.md`.

| Field | Type | Required | Used by |
|---|---|---|---|
| `title` | string | yes | every page; `<title>`, cards, feeds |
| `date` | date | posts only | ordering, pagination, permalinks |
| `tags` | list of taxonomy keys | posts only | `tag.html` pages, chips, indexes |
| `lang` | `en` \| `vi` | yes | language switch, feeds, sitemap alternates |
| `ref` | string slug | translated pages | EN↔VI cross-link (`lang-switch.js`) |
| `image` | asset path | optional | cards, thumbnails, og image |
| `description` | string | optional | excerpts, meta/og description |
| `series*` | string/intent marker | optional | series pairing (e.g. orchestration sequel pair, #330) |

Defaults: site `lang: en` in `_config.yml`; every Vietnamese page sets
`lang: vi` (#93). Violations surface as build output or guard failures,
never silently — except `highlights.yml` slug typos, which fall back
silently (known footgun, see `docs/architecture/data-model.md`).
