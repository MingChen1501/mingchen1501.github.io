# Browser E2E tests

Browser end-to-end coverage for the post comments feature
(`_layouts/post.html` + `_includes/comments.html`), the site layout and the
home-list tag chips (#47, `test_home_tag_chips.py`).

## Comments (`test_comments*.py`)

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

`test_comments_markup.py` and `test_post_layout_markup.py` run without a
browser and guard the real Jekyll templates against drifting away from what
the fixtures and the rendered pages assume.

## Home list tag chips (`test_home_tag_chips.py`)

Guard for #47 (epic #44). The chips come from a Liquid include, so this guard
needs the real site: it uses the session's shared `built_site` build and
`built_site_url` server (`conftest.py`), which serve the result over loopback
HTTP (dev environment, so the external giscus embed is never fetched;
third-party requests are aborted).

- Every home list item shows its post's tags as chips linking to
  `/tags/<tag>/`, in the same order and with the same labels as the post
  page's sidebar chips (`_includes/post-tags.html` is the single source).
- Every chip href resolves to a `tags/<tag>.md` page that exists in the build
  (and returns HTTP 200 from the served build).
- The home chip's computed style (size, padding, pill radius, colour) equals
  the post sidebar chip's.
- At 360px and 375px the chips stay inside the viewport and their list wraps.
  The document-level `scrollWidth <= innerWidth` assertion allows exactly the
  measured image overhang while the tracked #50 image regression is present
  (PR #51 owns that fix) and becomes strict once images stop overhanging.

## Layout overflow guard (`test_layout_overflow.py`)

Regression guard for #50. `img { max-width: 100%; padding: 20px }` used the
default content-box sizing, so a full-width image rendered `100% + 40px` wide
and every page showing one scrolled ~40px sideways at phone widths.

- Needs the real site, so it uses the session-wide `built_site` fixture
  (`conftest.py` runs exactly one `bundle exec jekyll build` for the whole
  suite; dev environment: the external giscus embed is not fetched) and the
  matching `built_site_url` server. Third-party requests are blocked; the
  local `style.css` fully defines the layout.
- Asserts `document.documentElement.scrollWidth <= window.innerWidth` at 375px
  for a post page, the home list, the `/tags/` index and every `/tags/<tag>/`
  page, in the light and dark colour scheme, and that no image overhangs the
  viewport or loses its aspect ratio.
- The `/tags/<tag>/` case skips with an explicit reason while those pages are
  absent from the build (PR #48 adds them); it starts measuring them as soon as
  they exist.
- `test_img_rule_keeps_padding_inside_max_width` is a static backstop for the
  `_sass/minima/_base.scss` `img` rule that needs neither Ruby nor a browser.

## Shared fixtures (#56)

`tests/e2e/conftest.py` owns the plumbing every module reuses, so a suite run
does the expensive work once:

- `built_site` - one `bundle exec jekyll build` per session, into a temp dir
  (the fixture logs its invocation to stderr, and to `$E2E_BUILD_LOG` when set);
- `built_site_url` - one loopback HTTP server for that build;
- `browser` - one headless Chromium for every browser test (each test still
  gets a fresh context/page);
- `e2e_server` - the `tests/e2e/fixtures/` server for the comments tests.

Guards that need neither Ruby nor a browser are marked `static`; they run first
locally and in their own CI job.

## Run locally

```sh
pip install -r tests/e2e/requirements.txt
python -m playwright install chromium   # or reuse system Chrome automatically
python -m pytest tests/e2e -v
```

`-m static` runs only the fast browser-free guards, `-m "not static"` only the
browser ones.

The browser tests prefer the local system Chrome (`channel="chrome"`) and
fall back to Playwright's bundled Chromium, so the `playwright install`
step can be skipped on machines that already have Chrome.

The guards that need the real site additionally need Ruby + `bundle install`;
without a `bundle` executable they skip themselves with an explicit reason.

## CI

`.github/workflows/e2e.yml` runs two jobs (Python 3.12, with pip and Playwright
browser caches, and Ruby 3.3 with `bundler-cache`):

- `E2E static guards` - `pytest tests/e2e -m static`: no Ruby, no Chromium;
- `E2E browser: comments, layout, tag chips` - `pytest tests/e2e -m "not static"`:
  uses the shared session build (one Jekyll build) and browser.

Both run on pushes and pull requests to `master`; a superseded push cancels its
in-flight run (`concurrency` with `cancel-in-progress`).
