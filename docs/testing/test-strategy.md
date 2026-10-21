# Test strategy

Status: active (thin). Owns the strategy statement; structure and overlap
map live in `docs/architecture/testing.md`, per-feature coverage in
`tests/e2e/README.md`.

Two layers by design: static guards (markup, budgets, image rules — no
browser, run always) and browser tests (Playwright + LHCI + visual
compares — full-suite PRs, opt-in locally via `E2E_VISUAL=1`). One shared
Jekyll build feeds every layer (`E2E_PREBUILT_SITE`). Budgets are declared
once in `script/` and parsed by both shell and Python guards — never
redeclared. FR/NFR to guard map: `testing/traceability.md`. CI runs are
the report; no checked-in report file (see `testing/test-report.md`,
stub).
