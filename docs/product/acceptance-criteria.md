# Acceptance criteria

Status: active. A change is done when all of the following hold.

1. `bundle exec jekyll build --trace` is green and `docs/` stays excluded
   from the built site (`_config.yml` `exclude:`, leak-checked on every
   build).
2. The CI suite for the change class is green: content-only PRs
   (`_posts/`, `_vi_posts/`, `assets/img/`, `_data/highlights.yml`) take
   the short path, everything else runs the full suite — classifier
   `script/classify-content-only`, contract in `tests/e2e/README.md`.
3. New or changed behaviour has a guard test; budgets (images, JS/CSS
   bytes) still pass. Guard map: `docs/architecture/testing.md`; FR/NFR
   to guard map: `testing/traceability.md`.
4. Review flow satisfied: exactly one risk label, English artefacts, squash
   merge on green CI (conventions: `development/coding-standards.md`).
5. No new source of truth: docs either own content or defer with a link
   (index: `docs/README.md`).
