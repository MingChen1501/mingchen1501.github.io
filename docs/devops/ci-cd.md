# CI/CD

Status: active. Owns the workflow inventory; the classifier contract lives
in `tests/e2e/README.md` ("CI").

- `ci.yaml`: Jekyll matrix + image guards + `cibuild`. A superseded push
  cancels its in-flight run (`concurrency` with `cancel-in-progress`,
  same group pattern as `e2e.yml`, #418).
- `e2e.yml`: shared content-only classifier → static guards → ONE shared
  site build → browser matrix + LHCI desktop and mobile (#320); reports
  uploaded from `.lighthouseci/`. Lighthouse never runs on master pushes
  by design, so a daily schedule (`0 6 * * *` UTC, #418) gives `master`
  its LHCI signal and catches squash/base drift before the next PR.
- `visual-baselines.yml`: baseline regeneration for intentional visual
  changes (diff reviewed before commit).
- Shared step: `.github/actions/classify-content-only/`.
- Force the full suite: workflow_dispatch (`full=true`).

Failure playbook and re-runs: `operations/runbook.md`.
