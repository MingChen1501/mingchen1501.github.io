# Test data

Status: active. Owns the test-data inventory; fixtures live in
`tests/e2e/fixtures/`.

- `tests/e2e/fixtures/`: canned inputs for guards that need them.
- Vendored `tests/e2e/axe-core/`: pinned accessibility engine, not
  fetched at test time.
- No production data is used in tests; no PII, no fixture contains
  reader information. External-image guards use allowlisted attachment
  hosts (`_data/image_hosts.yml`, #195).
- Visual baselines: regenerated only for intentional visual changes via
  `script/update-visual-baselines`, diff reviewed before commit.
