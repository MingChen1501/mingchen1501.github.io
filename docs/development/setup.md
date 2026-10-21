# Development setup

Status: active. Owns the setup command list; detail lives in the files
it points at.

1. `bundle install` (first time; Ruby gems for the Jekyll build).
2. `pip install -r tests/e2e/requirements.txt` (first time; Playwright
   plus guards).
3. Preview real content: `bundle exec jekyll serve` (uses `_config.yml`;
   never `script/server` for personal posts — minima sample content only).
4. Check build: `bundle exec jekyll build --trace`.
5. Tests: `python -m pytest tests/e2e -v`; visual compares opt in locally
   with `E2E_VISUAL=1`. Image budgets: `script/check-images`.
6. Dev-content preview uses `_config_theme-dev.yml` (theme-work config,
   not production).

`AGENTS.md` is normative when this file and that file disagree.
