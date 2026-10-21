# Schema specification

Status: active. Owns the `_data/*.yml` schemas; front-matter fields are
owned by `requirements/data-dictionary.md`, structural role by
`docs/architecture/data-model.md`. This file adds only the shapes.

- `highlights.yml`: `{ en: [slug...], vi: [slug...] }`, ≤5 ordered slugs
  per language; unknown/unpublished slugs skipped silently, empty/missing
  list falls back to the 5 newest posts of that language.
- `tag_labels.yml`: canonical key → `{ en, vi, slug_en, slug_vi,
  description_en, description_vi, pillar, order }` (`pillar: true` entries
  are the curated sidebar set, ordered by `order`, capped at 6); per-tag `tags/*.md` and `vi/tags/*.md`
  bodies must be kept in sync by hand (header comment in the file).
- `image_hosts.yml` (temporary, #195): `{ scheme: https, allowed_hosts,
  attachment_path_prefixes }`; migration checklist in the file header.

Readers and guard chains per file: `docs/architecture/data-model.md`.
