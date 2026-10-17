# Browser E2E tests

Browser end-to-end coverage for the post comments feature
(`_layouts/post.html` + `_includes/comments.html`), the site layout, the
home-list tag chips (#47, `test_home_tag_chips.py`), the list-page sidebar
(#58, `test_sidebar_layout.py`) and asset cache versioning
(#61, `test_stylesheet_cache_version.py`).

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

## List-page sidebar (`test_sidebar_layout.py`)

Guard for #58. The home list (`/`, `/page2/`…) and the tag pages
(`/tags/<tag>/`) wrap their list in one shell (`.site-layout` > `.site-main` +
`aside.site-sidebar`) fed by the shared `_includes/site-sidebar.html`.

- Static: both layouts render the shell with the include, the sidebar comes
  after the list in the DOM, the include holds both blocks exactly once, the
  recent-posts block comes from `site.posts` (not the paginator), the tag block
  reuses `_includes/post-tags.html` (no forked chip markup) and the styles
  define the `minmax(0, 1fr) [300px]` grid with a sticky sidebar only inside the
  `>=960px` media query.
- Browser (needs Ruby + a browser): exactly three recent posts on `/` and the
  same three on `/page2/`; every tag group lists only real posts of that tag
  (newest first, at most five, matching the tag page's own list and count) and
  every link returns HTTP 200; two columns beside each other with a sticky
  300px sidebar at 1280px, and one column with the sidebar under the list
  (not sticky) at 375px; no horizontal overflow at 375px on `/` and on a
  `/tags/<tag>/` page, with the sidebar thumbnail decoded, undistorted and
  never upscaled.

## Asset cache versioning (`test_stylesheet_cache_version.py`)

Guard for #61, a live-site defect: GitHub Pages serves `assets/**` with
`cache-control: max-age=14400` from a fixed URL, so a warm browser could render
the post-#58 HTML with the pre-#58 stylesheet (no `.site-layout` grid) and the
sidebar painted below the whole post list — "no sidebar on the index page",
while the post page (whose #45 rules exist in both stylesheets) looked fine.

Why the 13 sidebar guards and the 375/1280 overflow guards all passed: they load
ONE build's own HTML + CSS pair from the same freshly served directory, so HTML
and CSS always come from the same revision. Nothing asserted that the *deployed
asset URL* is cache-safe, and a single-build test cannot observe a client that
mixes new HTML with an old cached stylesheet.

- Static (no Ruby, no browser): `_includes/head.html` links the stylesheet
  through the build token (`?v=...`), every fixed-URL `/assets/` link in the
  head (stylesheet, favicon) uses the same token, no template keeps an
  unversioned `/assets/` link, and the matcher rejects the old unversioned
  markup (so the guard is sensitive to the regression it guards).
- Needs the real site: every page of one build (home, `/page2/`, `/tags/`, a
  `/tags/<tag>/` page, a post) carries the same versioned URL, which resolves
  over HTTP 200 and serves a stylesheet that really defines the #58 grid.
- Rebuilds: a rebuild with a different build identity (`time:` in a config
  override) publishes a different URL, and changing ONE CSS declaration in a copy
  of the site emits a different URL too (the owner's proof that the token tracks
  the CSS content).
- Browser: a client that still holds the old stylesheet under the unversioned
  URL (a cache keyed by URL) still gets the sidebar, because the HTML asks for a
  different URL; the same harness provably sees the sidebar vanish when the
  stale stylesheet *is* served.

Trade-off pinned by the guard: the token follows the *build*, not the CSS bytes,
so a deploy that does not touch the stylesheet re-fetches it once (~18KB). A real
content hash of the compiled CSS needs a Jekyll plugin, which GitHub Pages does
not run in its `--safe` build; a per-build token changes on a superset of the
cases where the CSS changes, which is why it can never pair stale CSS with fresh
HTML.

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
