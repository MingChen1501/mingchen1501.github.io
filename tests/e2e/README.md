# Comments E2E tests

Browser end-to-end coverage for the post comments feature
(`_layouts/post.html` + `_includes/comments.html`, Disqus-based).

## What is covered

- Enabled post renders the `#disqus_thread` container.
- Enabled post requests `https://<shortname>.disqus.com/embed.js` for the
  configured shortname (Disqus is stubbed at the network layer, so no
  external service is contacted).
- `disqus_config` carries the canonical page URL and page identifier.
- A `<noscript>` fallback exists for readers without JavaScript.
- A post with `comments: false` shows the disabled message and makes zero
  Disqus requests.
- A page built without `site.disqus.shortname` renders no comment markup
  and makes zero Disqus requests.

`test_comments_markup.py` runs without a browser and guards the real Jekyll
templates against drifting away from what the fixtures assume.

## Run locally

```sh
pip install -r tests/e2e/requirements.txt
python -m playwright install chromium   # or reuse system Chrome automatically
python -m pytest tests/e2e -v
```

The browser tests prefer the local system Chrome (`channel="chrome"`) and
fall back to Playwright's bundled Chromium, so the `playwright install`
step can be skipped on machines that already have Chrome.

## CI

`.github/workflows/e2e.yml` installs Python, Playwright + Chromium, and runs
`python -m pytest tests/e2e -v` on pushes and pull requests to `master`.
