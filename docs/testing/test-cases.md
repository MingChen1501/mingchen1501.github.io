# Test cases

Status: active (pointer). This file owns no case list; cases are the
`test_*.py` files themselves plus their docstrings.

- Index intent: `tests/e2e/README.md` documents per-feature coverage.
- Ownership convention (#302): each guard docstring records what it owns;
  overlap clusters (comments, footer, i18n, images) are mapped in
  `docs/architecture/testing.md`.
- FR/NFR to guard map: `testing/traceability.md`.
- Largest guards: `test_sidebar_layout.py`, `test_giscus_comments.py`,
  `test_i18n.py`; JS-adjacent coverage consolidated in
  `test_site_utils.py` after #349 removed search.
