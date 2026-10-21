# Coding standards

Status: active. Owns the conventions actually in force; `AGENTS.md` is
normative on conflicts.

- English in every public artefact (PRs, commits, issues, review
  comments, code comments); Vietnamese only for internal AO reporting.
- Every artefact signed with its role (`docs/ao-rules.md`).
- Squash merge only, on green CI; never push directly to `master`.
- Exactly one risk label per issue and PR
  (`risk-low` / `risk-medium` / `risk-high` / `risk-very-high`);
  `risk-high` and above need explicit owner approval.
- `CNAME`, `url`, and Giscus IDs need owner confirmation.
- Never hand-edit build outputs (`_site/`, caches, `vendor/`,
  `Gemfile.lock`); change dependencies via `bundle install`/`update`.
- Images: each file <= 500KB, `assets/img/` total <= 6MB
  (`script/check-images`); asset caching via the single `asset_version`
  token. Image conventions: `docs/conventions-173.md`.
