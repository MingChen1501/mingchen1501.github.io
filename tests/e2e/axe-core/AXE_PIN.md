# Vendored axe-core (offline accessibility scanner)

`axe.min.js` is the pinned, vendored copy of the axe-core scanner injected by
`tests/e2e/test_axe_a11y.py`. It is loaded from disk with Playwright's
`add_script_tag` — no CDN, no npm install, no network fetch — so the
accessibility smoke test is deterministic and runs offline in CI.

- Version: **axe-core 4.14.0** (header line: `/*! axe v4.14.0`).
- Source: `https://registry.npmjs.org/axe-core/-/axe-core-4.14.0.tgz`
  (`package/axe.min.js` inside the tarball).
- Integrity (SHA-512 of the tarball, as published by the npm registry):
  `sha512-9WTZxEjsZ7b13TH8JPmbV2z8CHbl80/2hm3XPEG4JgNdQLK81IBRXmSxHfMAOkSqQeRxT/0dwNDz2GOm3zzpcQ==`
- License: **Mozilla Public License 2.0** (Deque Systems, Inc.); the full
  copyright/MPL notice is preserved in the file header, as the license
  requires for every distributed copy.

## Updating the pin

1. Download the new version's tarball from the npm registry.
2. Verify its SHA-512 against the registry's `integrity` field.
3. Replace `axe.min.js` with the tarball's `package/axe.min.js`.
4. Update the version, source URL and integrity hash above, and the
   `AXE_VERSION` assertion in `test_axe_a11y.py`.
5. Re-run `python -m pytest tests/e2e/test_axe_a11y.py -v` — a scanner update
   may surface new violations or retire accepted exceptions.
