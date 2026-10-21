# Non-functional requirements (NFR)

Status: active. Each item names the guard that enforces it; budgets are
declared once in `script/` and never redeclared here.

- NFR-1 Images: each file <= 500KB, `assets/img/` total <= 6MB.
  Guards: `script/check-images` (+ `image-budget.sh`), `test_check_images.py`.
- NFR-2 First-party JS/CSS bytes under the ceilings in
  `script/asset-budget.sh` (page 23,552 B, post 41,984 B, CSS main
  50,176 B, syntax companion 19,456 B). Guards: `test_asset_budget.py`,
  `test_syntax_highlight_css.py`; parity pinned by `test_css_parity.py`.
  `script/asset-budget.sh` is the single source of truth; the numbers
  here are informational only and must not be used to pin new ceilings.
- NFR-3 Lighthouse: desktop and mobile LHCI passes on every full-suite
  run (`.github/workflows/e2e.yml`, `lighthouserc.json`,
  `lighthouserc.mobile.json`); reports uploaded from `.lighthouseci/`.
- NFR-4 Accessibility: axe-core clean on audited pages plus targeted
  a11y guards (nav, footer social/email, alt text). Guards:
  `test_axe_a11y.py`, `test_nav_a11y.py`, `test_footer_*_a11y.py`,
  `test_en_alt_text.py`, `test_vi_alt_text.py`.
- NFR-5 Privacy: zero third-party requests except the Giscus embed on
  production post pages; no analytics, no webfonts. Guards:
  `test_about_privacy.py` and the inventory in
  `docs/architecture/privacy-csp.md`.
- NFR-6 Robustness: no broken internal links, no bare-URL posts, no
  layout overflow. Guards: `test_internal_link_crawl.py`,
  `test_post_bare_urls.py`, `test_layout_overflow.py`,
  `test_code_table_overflow.py`.
