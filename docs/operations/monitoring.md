# Monitoring

Status: active. Owns where the signals live; there is no uptime monitor
and no on-call (see `operations/incident-response.md`, stub).

- CI status per PR and per `master` push: the Actions tab (runs are the
  test report — no checked-in file).
- Lighthouse reports: `.lighthouseci/` artifacts on each `e2e.yml` run.
- Budgets as monitors: image budgets (`script/check-images`) and
  JS/CSS ceilings (`script/asset-budget.sh`) fail the build instead of
  paging anyone.
- Reader-visible failures arrive as Giscus comments or owner notice;
  triage via `operations/runbook.md`.
