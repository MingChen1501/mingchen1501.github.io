# Pinned upstream minima baseline (#184)

Follow-up of #169 (upstream-minima drift audit).

## Baseline

This site is forked from `jekyll/minima` at baseline commit `4de3223`
("Update history to reflect merge of #924 [ci skip]", 2026-04-07).

- Sync history: PR #3 (merge `3bb26af`, with `4de3223` as second parent)
  brought upstream master in; PR #5 (`30f52c9`, merged 2026-10-13) completed
  conflict resolution.
- Verification (2026-10-20, read-only): `git fetch
  https://github.com/jekyll/minima.git master` resolved `FETCH_HEAD ==
  4de3223` — upstream master equalled the baseline, 0 commits after it.
  `minima.gemspec` is `3.0.0.dev`, matching upstream's v3-direction master.

## Policy: pinned, no routine sync

The site is intentionally diverged (211 differing files, including 15
same-path theme overrides and 181 new local files for bilingual content,
tests, and tooling). Do not routinely sync upstream; audit recommendation is
pin-and-stop (option B) with periodic checks only.

## Checking future upstream changes

No remote is needed; this stays read-only:

```sh
git fetch https://github.com/jekyll/minima.git master
git log --oneline 4de3223..FETCH_HEAD
```

An empty log means upstream has not moved past the baseline.

## If a sync is ever attempted

1. Open a dedicated issue first; do not sync ad hoc.
2. Diff the baseline against the site head (`4de3223..HEAD`) to review local
   divergence before touching anything.
3. Expect conflicts at the known hotspots: `_layouts/home.html`,
   `_layouts/post.html`, `custom-styles.scss`, `_config.yml`,
   `_includes/head.html`.
