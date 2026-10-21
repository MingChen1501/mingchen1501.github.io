# Test plan

Status: active (thin). Owns the per-change test selection; scope matrix
detail lives in the `jekyll-verify` skill and `tests/e2e/README.md`.

- Content-only change (`_posts/`, `_vi_posts/`, `assets/img/`,
  `_data/highlights.yml`): build + static guards; browser matrix,
  baselines, and Lighthouse are skipped (#229). Never regenerate visual
  baselines for content-only PRs.
- Layout/include/SCSS/JS/config change: full suite (static + browser +
  both LHCI passes + visual compares in CI).
- New behaviour: add or extend a guard in the same PR; record ownership
  in the guard docstring (#302 convention).
- Classifier contract: `script/classify-content-only`, pinned by
  `test_content_only_classification.py`.
