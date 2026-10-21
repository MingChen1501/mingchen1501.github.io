# CI/CD

Status: active. Owns the workflow inventory; the classifier contract lives
in `tests/e2e/README.md` ("CI").

- `ci.yaml`: Jekyll matrix + image guards + `cibuild`.
- `e2e.yml`: shared content-only classifier → static guards → ONE shared
  site build → browser matrix + LHCI desktop and mobile (#320); reports
  uploaded from `.lighthouseci/`.
- `visual-baselines.yml`: baseline regeneration for intentional visual
  changes (diff reviewed before commit).
- `demo_site.yml`: legacy upstream-minima demo deploy (stale candidate,
  unrelated to the personal site).
- Shared step: `.github/actions/classify-content-only/`.
- Force the full suite: workflow_dispatch (`full=true`).

Failure playbook and re-runs: `operations/runbook.md`.
