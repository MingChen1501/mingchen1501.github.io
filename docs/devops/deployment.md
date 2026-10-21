# Deployment

Status: active. Owns the deploy path; build detail lives in
`docs/architecture/content-pipeline.md`.

GitHub Pages builds `master` with Jekyll `--safe` (no custom plugins) and
serves it at `mingchen.id.vn` (`CNAME` + `_config.yml` `url`). Only merges
to `master` deploy — never push directly; land via squash-merged PRs on
green CI. Rollback is a revert commit (see `release/rollback.md`). There is
no staging environment; preview with `bundle exec jekyll serve` and the
CI-built site instead.
