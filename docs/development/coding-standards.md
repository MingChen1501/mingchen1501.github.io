# Coding standards

Status: active. Owns the conventions actually in force; `AGENTS.md` is
normative on conflicts.

- English in every public artefact (PRs, commits, issues, review
  comments, code comments); Vietnamese only for internal AO reporting.
- Every artefact signed with its role (`docs/ao-rules.md`).
- Squash merge only, on green CI; never push directly to `master`.
- Branch retention: squash merges pass `--delete-branch`, so a merged
  topic branch disappears from the remote at merge time; a session
  `ao/*` root goes the same way once its last topic PR merges. If a
  merged branch survives (merge without delete, direct push), whoever
  merged deletes it in the same session after verifying it is fully
  merged (`git branch -r --merged origin/master`, always keeping
  `master`, `HEAD`, `gh-pages`, and `2.5-stable`). Unmerged branches
  are never deleted unilaterally — list them in the PR for the owner
  to decide. Keep local remote-tracking refs honest with
  `git fetch origin --prune`.
- Exactly one risk label per issue and PR
  (`risk-low` / `risk-medium` / `risk-high` / `risk-very-high`);
  `risk-high` and above need explicit owner approval.
- `CNAME`, `url`, and Giscus IDs need owner confirmation.
- Never hand-edit build outputs (`_site/`, caches, `vendor/`,
  `Gemfile.lock`); change dependencies via `bundle install`/`update`.
- Images: each file <= 500KB, `assets/img/` total <= 6MB
  (`script/check-images`); asset caching via the single `asset_version`
  token. Image conventions: `docs/conventions-173.md`.
