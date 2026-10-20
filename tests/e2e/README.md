# Browser E2E tests

Browser end-to-end coverage for the post comments feature
(`_layouts/post.html` + `_includes/comments.html`), the site layout, the
home-list tag chips (#47, `test_home_tag_chips.py`), the list-page sidebar
(#58, reworked in #63, `test_sidebar_layout.py`) and asset cache versioning
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

## List thumbnails (`test_list_thumbnails.py`)

Guard for #226. The home/tag lists show post imagery again, but every item
shares one fixed 120x90 (4:3) box (`_includes/post-thumbnail.html`), so the
list never shifts while images load.

- Source chain per post: front matter `thumbnail`, else front matter `image`,
  else the first image of the post body, else a single theme-aware
  placeholder tile for posts with no image: a `post-thumb__placeholder` div
  (never an `img`, so no hidden lazy twin can break image decoding), painted
  light (`#e8e8e8`/`#9a9a9a`) by default and dark (`#262626`/`#8c8c8c` with a
  `#3a3a3a` hairline) under `html[data-theme]` with the OS
  `prefers-color-scheme` fallback (#245).
- Local sources map to small 240x180 cover-cropped WebP variants
  (`assets/img/thumbs/...`, from `script/generate-thumbnails` — rerun it
  after adding or changing a post image and commit the variants), so lists
  never download the 1600px originals. External issue-attachment URLs cannot
  be resized and keep the same fixed CSS box.
- Static (no Ruby, no browser): the chain order, the 120x90 attributes, the
  `object-fit: cover` box, and the freshness of every expected variant; the
  tile artwork stays byte-identical to `assets/img/placeholder(-dark).svg`
  and repaints per theme while light mode stays unchanged (#245).
- Built HTML: every list item on the EN/VI homes and tag pages carries exactly
  one thumbnail resolving to a file in the build (placeholder items carry
  the single CSS tile and no `img`); the three source cases
  hold (front matter wins, else first body image, else placeholder).
- Browser: every thumbnail box renders at an identical 120x90 CSS px at
  375/768/1280px on the EN/VI homes and tag pages — including with images
  blocked, so the reserved box alone already has the final size (no CLS).
  The single placeholder tile keeps the box in both themes, and the dark tile
  meters comfortably darker than the light one
  (#245). Dark mode has no visual baselines: `test_visual_regression.py`
  pins the light colour scheme, so dark-only changes never touch baselines.

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

## Code and table overflow (`test_code_table_overflow.py`)

Guard for #151 (follow-up of the #112 reader-UX audit). Wide code blocks and
Markdown tables must scroll *inside* their own container at real-device
widths instead of pushing the page sideways.

- Static (no Ruby, no browser): the site-wide `pre` rule keeps
  `overflow-x: auto` and the phone-width `table` rule keeps `display: block`
  + `overflow-x: auto` in `_sass/minima/_base.scss`.
- Browser (needs Ruby + a browser): a fixture with a wide fenced block, a
  rouge line-number block (`figure.highlight` + `table.rouge-table`, as
  produced by `{% highlight ... linenos %}`) and a wide Markdown table is
  injected into a real built page with the real copy-code script running.
  At 360px and 320px the document keeps
  `scrollWidth <= innerWidth`, every element wider than the viewport sits
  inside an active scroll container, each wide block really scrolls
  (`scrollWidth > clientWidth`, so content is reachable, not clipped), and
  the copy buttons keep their 44px target without adding page overflow.
- Verification for #151 found no page-level overflow (including the
  unpublished code-heavy 2016 post rendered with `--unpublished`), so there
  is deliberately no CSS change: desktop rendering is untouched and this
  guard pins the existing containment against future regressions.

## Image lightbox (`test_lightbox.py`)

Guard for #223. Post content images open full-size in an accessible overlay:
click (or Enter/Space on the focused image) shows the already-loaded source
(`currentSrc`, so no new image variants) with its alt/caption text, arrow
keys move prev/next within the post, and Esc closes and returns focus to
the invoking image. Decorative repeats (`aria-hidden`, #147) and linked
images never join the set; the dialog is built at runtime, so without JS
the page ships no overlay markup at all.

- Static (no Ruby, no browser): the script stays vanilla, tiny and localized
  (EN/VI from `<html lang>`); only informative images become triggers;
  dialog semantics (`role="dialog"`, `aria-modal`, focus trap + restore,
  Escape/arrows, swipe) live in the script; the template links it with the
  `?v=` build token (#61); the SCSS partial joins the cascade and scopes
  every new box under `.lightbox` (`hidden` hides, 44px controls, trigger
  focus, reduced motion) without changing trigger geometry.
- Build (needs Ruby, no browser): the EN/VI coffee posts ship no dialog
  markup and no trigger attributes (progressive enhancement); the script
  URL carries a non-empty epoch token.
- Browser (needs Ruby + a browser): click opens with the full-size source
  and caption; keyboard-only flow (focus, Enter/Space, arrows, live
  counter, Esc restores focus); focus stays trapped while open;
  single-image sets hide prev/next; external attachment URLs (#195) open
  the same way; axe is clean with the overlay open; no-JS pages stay plain
  images; opening adds no page overflow at 375px/1280px.

The overlay is runtime-built and hidden by default, so baselined pages
render pixel-identical with or without the script: lightbox work never
regenerates the visual baselines below unless the trigger/overlay styling
itself changes page pixels.

## Offline search (`test_search.py`)

Guard for #221. A build-time JSON index (`search.json`, emitted by Liquid
over `site.posts` + `site.vi_posts` — title, description, URL, lang, tags,
date; drafts and generated pages excluded) plus a vanilla-JS page pair
(`/search/` + `/vi/tim-kiem/`, shared `ref: search`) that filters the index
in the reader's browser. No plugin, no external service, no SDK.

- Static (no Ruby, no browser): the index template emits exactly the six
  metadata fields (never the body) with the `site.vi_posts` nil-guard the
  upstream theme-dev build needs; both pages carry lang/ref/permalink and
  include the shell; the shell wires label/input/landmark/`aria-live`
  status/results plus the `?v=` build token on the script and the index URL
  (#61); the script stays vanilla, tiny and offline; nothing outside the
  shell loads either asset (the index is fetched only on the search page);
  both navs link the page; the SCSS partial joins the cascade.
- Build (needs Ruby, no browser): `search.json` parses, holds one entry per
  published post per language with all six fields, and every URL resolves
  to a built file; both pages render with a numeric version token and
  switch to each other.
- Browser (needs Ruby + a browser): a fixture query returns the expected
  post first on both paths — including a diacritics-free Vietnamese query
  (`bai bien` finds `bãi biển`) and the shared `fedora` query, which ranks
  the same-language post top; empty query shows guidance, nonsense query
  shows the localized no-results state announced via the live region; the
  control is keyboard-operable (autofocus, Enter filters in place, Tab
  reaches results, Escape clears); neither page scrolls sideways at 375px
  or 1280px.

The search pages are deliberately outside the visual-baseline set below:
the baselines already use ~1.9 of the 2 MB budget, and the page is a simple
form covered by the guards above. Adding the search link to both navs still
changes the header on every baselined page, so the full set regenerates
with any search/header change.

## Shared fixtures (#56)

`tests/e2e/conftest.py` owns the plumbing every module reuses, so a suite run
does the expensive work once:

- `built_site` - one `bundle exec jekyll build` per session, into a temp dir
  (the fixture logs its invocation to stderr, and to `$E2E_BUILD_LOG` when set);
- `built_site_url` - one loopback HTTP server for that build;
- `browser` - one headless browser for every browser test (each test still
  gets a fresh context/page); the engine is Chromium by default and
  `--browser-name firefox|webkit` (or `$E2E_BROWSER`) selects another (#209);
- `e2e_server` - the `tests/e2e/fixtures/` server for the comments tests.

Guards that need neither Ruby nor a browser are marked `static`; they run first
locally and in their own CI job.

## List-page sidebar (`test_sidebar_layout.py`)

Guard for #58, reworked for #63. The home list (`/`, `/page2/`…) and the tag
pages (`/tags/<tag>/`) wrap their list in one shell (`.site-layout` > `.site-main`
+ `aside.site-sidebar`) fed by the shared `_includes/site-sidebar.html`.

- Static: both layouts render the shell with the include, the sidebar comes after
  the list in the DOM, the include holds both blocks exactly once, the highlight
  block reads `_data/highlights.yml` (an ordered list of post slugs, rendered in
  file order; unknown and unpublished slugs are skipped silently; at most five
  rows; an empty or missing file falls back to the five newest posts under
  "Bài mới nhất"), the tag block reuses
  `_includes/post-tags.html` (no forked chip markup) and is collapsed with at
  most three posts, and the styles define the `minmax(0, 1fr) [300px]` grid, the
  capped thumbnail and a sidebar pinned only where it fits (desktop width *and*
  `>=720px` of viewport height), never a `max-height`/`overflow-y` cap of its
  own.
- Browser (needs Ruby + a browser): the same highlighted posts (title, compact
  date, URL from the front matter) on `/`, `/page2/` and a tag page; every tag
  row collapsed, bounded to at most three posts, matching the tag page's own list
  and count, opening on one click with every link returning HTTP 200; two columns
  beside each other with a sticky 300px sidebar at 1280px, not sticky at 1280x600
  or 375px, and one column with the sidebar under the list at 375px; the sidebar
  never scrolls inside itself (not even with a tag row open); no horizontal
  overflow at 375px on `/` and on a `/tags/<tag>/` page, with the sidebar
  thumbnail decoded, undistorted and never upscaled.

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

## Browser matrix (#209)

The browser guards run on Chromium, Firefox and WebKit. The engine is
Chromium by default; `--browser-name firefox|webkit` (or `$E2E_BROWSER`)
selects another:

```sh
E2E_BROWSER=firefox python -m pytest tests/e2e -m "not static"
```

- Pixel comparison (`test_visual_regression.py`, #208) runs Chromium-only:
  the committed baselines are Chromium renders, and other engines
  rasterize differently, so the case skips on Firefox/WebKit with an
  explicit reason. Every other browser guard runs unmodified on all three
  engines (layout and style assertions read geometry and computed styles
  through the DOM, never pixels).
- `test_copy_code.py` narrows two things per engine: the clipboard grants
  run on Chromium only (Firefox allows clipboard over loopback HTTP with
  no grant and rejects the grant call), and the two click-to-copy
  read-backs skip on WebKit — headless WebKit denies
  `navigator.clipboard` (`NotAllowedError`) and Playwright grants no
  clipboard permission there. Each skip carries its reason inline.
- `test_axe_a11y.py` scopes the `object-alt` waiver to Chromium/Firefox:
  axe only flags the `/portfolio/` PDF `<object>` when its fallback
  renders zero boxes (the PDF plugin area covers it); headless WebKit has
  no PDF plugin intercept, renders the fallback link inline, and the rule
  never fires there. The waiver stays enforced where it applies.
- Measured runtime for `-m "not static"` (one shared Jekyll build
  plus 230 browser tests): locally ~2-3 min per engine; CI job durations
  (build + `install --with-deps` + suite) also ~2-3 min per engine.
  The three CI jobs run in parallel, so a full-run PR wall-clock is the
  slowest engine, not the sum. Content-only PRs skip this matrix entirely
  (#229, see "CI" below) instead of a smoke/nightly split.

Local WebKit runs need the system libraries (`python -m playwright
install --with-deps webkit`, requires sudo); without them the WebKit
process fails to start or flakes on page creation.

## Accessibility smoke (`test_axe_a11y.py`)

Guard for #207. The pinned, vendored axe-core scanner
(`tests/e2e/axe-core/axe.min.js`, version/source/hash/license in
`tests/e2e/axe-core/AXE_PIN.md` — no CDN, offline-capable) is injected into
`/`, one EN post plus its VI counterpart, `/tags/`, `/vi/`, `/about/`,
`/portfolio/` and the `/search/` + `/vi/tim-kiem/` pair (#221), each at
375px and 1280px in the light colour scheme.

- Fails on any `serious`/`critical` violation: the four #207 exceptions
  were resolved for real in #213, so `ACCEPTED` is empty (a future waiver
  needs a rule + node-target + deferred-fix reason). Fixed nodes that must
  keep rendering (`.lang-switcher`, `.u-email`, `blockquote`, the
  portfolio `<object>`) plus the shipped rule ids are re-asserted so the
  green run cannot go vacuous.
- `minor`/`moderate` findings are printed but non-blocking.

## Visual regression baselines (`test_visual_regression.py`)

Guard for #208. Markup and layout-math guards cannot see a page *looking*
broken, so this module screenshots a fixed page set at 375/768/1280px and
fails when a fresh capture differs from the committed baseline beyond a small
threshold: the home list, one EN post with its VI twin, the `/tags/` index
with its VI twin, one tag page with its VI twin, about with its VI twin, and
portfolio with its VI twin (12 pages x 3 viewports = 36 captures in
`tests/e2e/visual/baseline/`).

- Determinism: the shared dev build (no giscus embed, no analytics), the
  light colour scheme with reduced motion, third-party requests blocked,
  animations/transitions/caret blinking disabled via injected CSS, and a
  settle step (`document.fonts.ready`, every image decoded after one scroll
  through the page) before each full-page screenshot.
- Comparison: captures are downscaled to half size (Lanczos) and stored as
  JPEG quality 60, so all 36 baselines stay under the 2 MB budget (currently
  ~1.9 MB; `test_baseline_budget` pins the ceiling and the per-case file
  list). A pixel counts as changed when any channel differs by more than 12,
  and the capture fails past 1% changed pixels — a 30px layout shift measures
  ~18%, while identical renders measure 0%.
- Update after an intentional visual change (CI never sets this, so drifts
  fail there):

```sh
script/update-visual-baselines
# i.e. UPDATE_BASELINES=1 python -m pytest tests/e2e/test_visual_regression.py -q
```

  Baselines are canonical on the CI runner (`ubuntu-latest`): screenshot
  bytes depend on the machine's font rasterization and JPEG encoder, so
  locally generated captures fail on CI. To refresh them, push the branch
  (or run the `Visual baselines` dispatch workflow once merged) and
  download the `visual-fresh-chromium` artifact from the failed browser-E2E run
  into `tests/e2e/visual/baseline/` — never commit locally rendered
  captures.

  Content-only PRs never need baseline regeneration (#229): adding a post
  changes the home list, so pixel captures drift by design, and the
  browser matrix (including this module) is skipped for content-only
  change sets. If a content-only PR touches baselines, that alone forces
  the full run.

## Run locally

```sh
pip install -r tests/e2e/requirements.txt
python -m playwright install chromium firefox webkit   # or reuse system Chrome automatically
python -m pytest tests/e2e -v
```

`-m static` runs only the fast browser-free guards, `-m "not static"` only the
browser ones. Append `--browser-name firefox` (or `webkit`) to run the
browser guards on another engine; `$E2E_BROWSER` does the same (this is how
CI selects the engine per job).

The browser tests prefer the local system Chrome (`channel="chrome"`) and
fall back to Playwright's bundled Chromium, so the `playwright install`
step can be skipped on machines that already have Chrome. Firefox and
WebKit always use Playwright's bundled builds, and WebKit additionally
needs its system libraries (`install --with-deps`, requires sudo).

The guards that need the real site additionally need Ruby + `bundle install`;
without a `bundle` executable they skip themselves with an explicit reason.

## CI

`.github/workflows/e2e.yml` runs (Python 3.12, with pip and Playwright
browser caches, and Ruby 3.3 with `bundler-cache`):

- `Classify content-only vs full run` (`script/classify-content-only`,
  #229) — see the classification table below;
- `E2E static guards` - `pytest tests/e2e -m static`: no Ruby, no browser.
  Always runs, including on content-only PRs;
- `E2E browser (<engine>)` - one job per engine (`chromium`, `firefox`,
  `webkit`, `fail-fast: false` so one engine never hides the others):
  `E2E_BROWSER=<engine> pytest tests/e2e -m "not static"`, each with the
  shared session build (one Jekyll build) and browser. Skipped on
  content-only PRs;
- `E2E suite result` - aggregator for branch protection: passes when the
  full matrix passed, or when a content-only PR skipped the matrix with
  green static guards. Protect this job, not the matrix jobs (a skipped
  job reports "skipped", never "success").

The Jekyll builds (3.9 and 4.2 via `script/cibuild`), the link crawl /
sitemap+feed XML validation, and `script/check-images` (+ external-image
and alt-text checks) in `ci.yaml` always run, including on content-only
PRs. Lighthouse (`.github/workflows/lighthouse.yml`) is skipped on
content-only PRs with its own `Lighthouse suite result` aggregator.

### Content-only classification (#229)

`content_only=true` only when **every** changed file matches the left
column. Any changed file in the right column — or any unknown path, or
an unavailable diff — forces the full run. No silent skip.

| `content_only=true` (content paths) | Forces full run (code paths) |
|---|---|
| `_posts/**` | `_layouts/**` |
| `_vi_posts/**` | `_includes/**` |
| `assets/img/**` (content images) | `_sass/**` |
| `_data/highlights.yml` (sidebar highlight list) | `assets/js/**` |
| | `_config.yml`, `_config*.yml` |
| | `tests/**` |
| | `script/**` |
| | `.github/**` |
| | Any other path not in the left column |

Rules:

- A new post (Markdown/content only, e.g. the #228 article files) cannot
  break layout, JS, or Sass, so content-only PRs run fast and green
  **without regenerating visual baselines** — baseline files
  (`tests/e2e/visual/baseline/**`) are code paths, so committing them
  forces the full run.
- When classification is uncertain (diff unavailable, empty change list),
  the workflows default to the full matrix exactly as before.
- Local check: `git diff --name-only <base>...<head> |
  script/classify-content-only`, pinned by
  `tests/e2e/test_content_only_classification.py` (static).

### Full-run override

To force the full suite on a content-only PR, dispatch the workflow
manually with `full=true` (the default): the Actions tab → `E2E` (or
`Lighthouse CI`) → `Run workflow` on the PR branch. `full=false` on a
dispatch re-runs classification against the branch instead.

Both run on pushes and pull requests to `master`; a superseded push cancels its
in-flight run (`concurrency` with `cancel-in-progress`).
