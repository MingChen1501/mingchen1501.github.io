# Build pipeline sequence

Status: active (thin). Owns the stage diagram; stage detail lives in
`docs/architecture/content-pipeline.md` (Jekyll) and `devops/ci-cd.md` (CI).

```text
push/PR ─▶ CI classifier (script/classify-content-only)
  ├─ content-only (_posts, _vi_posts, assets/img, highlights.yml)
  │    └─ Jekyll build + static guards (no browser, no baselines)
  └─ full suite
       └─ ONE shared Jekyll build ─┬─ static guards
                                   ├─ Playwright browser matrix
                                   ├─ LHCI desktop + mobile
                                   └─ visual compares (opt-in locally
                                      via E2E_VISUAL=1, always in CI)
                                             │
                                             ▼
                                   GitHub Pages deploy (master only)
```

The shared-build contract (`E2E_PREBUILT_SITE`) and the classifier
contract live in `tests/e2e/README.md` ("CI") and are pinned by
`test_content_only_classification.py`. Re-run/failure playbook:
`operations/runbook.md`.
