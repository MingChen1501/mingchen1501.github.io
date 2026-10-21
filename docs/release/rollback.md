# Rollback

Status: active. Owns the revert procedure.

Rollback is a revert commit on `master` (squash-merge a PR that reverts
the offending merge), which redeploys via Pages. No database, no
migrations, no data to repair. If the revert touches visuals, visual
baselines recover through the normal flow: regenerate with
`script/update-visual-baselines` only for the intended end state and
review the diff before commit (content-only PRs never regenerate
baselines). Confirm recovery with a full-suite run
(workflow_dispatch `full=true`).
