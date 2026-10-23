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

## Dark mode theme toggle (`test_theme_toggle.py`)

Guard for #220. Every page carries an icon-only `.theme-toggle` button in
the header row that flips the whole site between light and dark: first
visit follows the OS `prefers-color-scheme` (even without JS, via the
`auto` minima skin, with an inline bootstrap in `_includes/head.html`
setting `html[data-theme]` before first paint so there is no flash);
an explicit choice persists in `localStorage`. The name/tooltip follow the
page language, the control is a real 44px keyboard-operable `<button>`
with visible focus, transitions respect `prefers-reduced-motion`, and
contrast stays >= 4.5:1 in both modes (axe `color-contrast`, home + post +
tag pages, phone + desktop, EN + VI). Dark mode has no visual baselines:
`test_visual_regression.py` pins the light colour scheme, so dark-only
changes never touch baselines.

## Share buttons (`test_share_buttons.py`)

Guard for #222. Post pages render a small tracker-free share row (via
`_includes/share.html`) below the content: a copy-link button, a
`navigator.share` button revealed only where the API exists, and three
plain share-intent links (X, Facebook, LinkedIn) — no third-party SDK.
Labels are localized with stable accessible names; the copy button carries
the canonical post URL through the Clipboard API with a textarea +
`execCommand` fallback announced in a `role="status"` line; the copy-link
item ships hidden and is revealed by the script, with a `noscript`
fallback showing the canonical URL as a plain link so no-JS pages have
zero dead controls (#244).

## Reading progress + back-to-top (`test_reading_progress.py`)

Guard for #224. `_layouts/post.html` ships a thin fixed progress bar
(0-100% width + `aria-valuenow`) and a back-to-top pill past ~600px of
scroll, both `hidden` in the markup so no-JS readers render neither;
`assets/js/reading-progress.js` reveals the bar and drives both at
runtime. Labels follow the page language; `prefers-reduced-motion` jumps
instantly instead of smooth-scrolling. The script is linked through the
`?v=` build token like every other fixed-URL asset (#61). Browser guards
scroll a long EN post and its VI twin (progress advances, button appears,
activate, top reached) plus short-page, keyboard, focus, and no-JS cases.

## Print styles (`test_print_styles.py`)

Guard for #225. `_sass/minima/custom/_print.scss` trims print output to
the article column only, in both languages (all selectors are
language-neutral). The partial is imported exactly once and last (so it
wins the cascade) and carries no rules outside its single `@media print`
block — screen rendering stays byte-identical, and the Chromium visual
baselines (screen media only) never regenerate for print changes. The
block hides every chrome selector (header/nav, sidebars, TOC mounts,
share row, Related posts, comments, footer, reading progress,
back-to-top, lightbox, skip link), keeps readable print typography,
appends destination URLs to outbound links, and refuses breaks inside
headings/images/code. #242 pins dark-mode printing to the readable light
colours (`color-scheme: light` + light Rouge tokens).

## Post-only JS gating (`test_post_only_js.py`)

Guard for #253, extended by #318. `_includes/sub-footer.html` wraps the
`copy-code.js`, `lightbox.js`, `share.js` and `reading-progress.js` tags
(in that order, all after `site-utils.js`, each with the `?v=` build
token) in a single `page.layout == 'post'` conditional; the five scripts
every page needs stay unconditional. Built non-post pages (home EN/VI,
tag index + one tag page, about, resume) link none of
the four scripts (9 → 5 sub-footer requests) while EN/VI post pages still
link all four.

## Shared JS helper (`test_site_utils.py`)

Guard for #246. Six deferred scripts re-implemented the same primitives
inline (clipboard fallback, `readyState` guard, VI sniff); they now share
`assets/js/site-utils.js` (`window.SiteUtils` with `copyText` / `onReady`
/ `isVietnamese`), loaded first with the same `?v=` build token
site-wide (`sub-footer.html`).
The guard pins the helper contract, the removal of the duplicated blocks
at every call site, and that total `assets/js` bytes do not grow.
Byte ceilings per page kind live in `script/asset-budget.sh` (single
source of truth), pinned by `tests/e2e/test_asset_budget.py` (#267):
bump both files together, deliberately.

## Giscus theme sync (`test_giscus_comments.py`)

Guard for #211 with theme sync for #258. Comments stay gated off in dev
builds (`site.comments.dev` is false), so every test here builds with
`JEKYLL_ENV=production`: the enabled post renders the `section#comments`
container and the `https://giscus.app/client.js` script with every
configured data attribute, while Giscus traffic is intercepted and
aborted (zero real requests). `assets/js/giscus-theme.js` primes the
embed's `data-theme` to the site-mapped Giscus theme before the lazy
iframe boots and re-sends the Giscus `setConfig` postMessage on every
theme flip and iframe load, without reloading — pinned statically
(template wiring, postMessage shape/origin, silent fallback) and in the
browser with a mocked Giscus client (initial paint + toggle flip in all
four OS x site combos, EN + VI). See also "Comments" above for the Disqus
stubs and the `comments: false` / provider-off negatives.

## Post social image + JSON-LD image (`test_post_social_image.py`)

Guard for #256. `jekyll-seo-tag` already renders a complete `BlogPosting`
JSON-LD block plus `og:image` / `twitter:image` from `page.image` — but no
post declared `image:`, so image-bearing posts emitted no image. Every
published post whose body embeds a local `/assets/img/` image (or that
declared `thumbnail:`) now declares root-relative `image:` (the former
`thumbnail`, else the first body image), in both languages of each pair;
image-less posts declare nothing. Never hand-write a second `BlogPosting`
block: it would duplicate seo-tag's graph with conflicting entities.

## Guard ownership map (#297)

The suite's overlap clusters: which file owns which assertion area, what is
deliberately duplicated across layers, and what was merged. Static guards
(no Ruby, no browser) pin the source contract; build guards (needs Ruby, no
browser) pin the emitted site; browser guards pin runtime behavior. No
production code changed for this map.

### Comments (`test_comments*.py` + `test_giscus_comments.py`)

Two providers, two owners — the Disqus branch and the Giscus branch are
separate templates paths, not duplicates of each other:

- Disqus branch template contract (thread div, `disqus_config` URL/ident,
  embed URL, noscript, per-post and provider-off negatives): static in
  `test_comments_markup.py`, runtime with stubbed fixtures in
  `test_comments.py`.
- Giscus branch template contract (client script + every data attribute,
  section container, unconfigured branch, theme mapping, sync script tag)
  plus the production render (section + script, `data-lang`, sync script
  link, negatives) plus the mocked-client theme-sync behavior: all in
  `test_giscus_comments.py`, which owns every production build the comments
  guards need.
- Comments heading localization (`Bình luận` / `Comments`): the
  template-branch contract for both branches stays in
  `test_post_chrome_i18n.py`; the production-render assertion moved to
  `test_giscus_comments.py`
  (`test_production_build_localizes_comments_heading`), reusing its
  production build instead of paying for a second identical one.

Deliberately duplicated (kept): static template guards plus browser/fixture
behavior guards assert the same invariants at different layers — the markup
contract versus the runtime behavior. Merged: one duplicate production
Jekyll build removed (see above); assertion coverage unchanged.

### Footer (`test_footer_*.py`)

Three files, three includes — they read the same built EN/VI homes but
assert disjoint DOM:

- Description + author-name language (`site.description_en` /
  `author.name_en` vs the Vietnamese defaults, with cross-language leak
  checks): `test_footer_i18n.py` (owns `_includes/footer.html` language
  branching; description walks home/page/tag/post in both languages, author
  name walks home/post).
- Email accessible name (#150/#213, visually-hidden span, no `aria-label`,
  mailto + visible address): `test_footer_email_a11y.py` (owns the
  `u-email` link only).
- Social accessible names (#146, `aria-label`, decorative icons) + inline
  SVG retirement (#254): `test_footer_social_a11y.py` (owns
  `_includes/social.html` only).

Deliberately duplicated (kept): the static-source plus built-page layering
inside each file, and the shared EN/VI home reads across files. Merged: the
repeated first-post discovery preamble in `test_footer_i18n.py` is now one
`_first_post_rel` helper; assertions unchanged.

### i18n (`test_i18n.py` + `test_seo_bilingual.py` + `test_post_chrome_i18n.py` + `test_footer_i18n.py`)

- Post/collection language plumbing (`lang`/`ref`/pillars, switcher +
  alternates + fallback notice, canonicals, sidebar/tag language, EN/VI
  pagination): `test_i18n.py`.
- Bilingual SEO surface (sitemap alternates per entry + head agreement,
  llms.txt language sections + URL resolution, feed language split, feed
  discovery link per language): `test_seo_bilingual.py`.
- Sitemap structure (parses, unique locs, exclusions, paginated coverage)
  + `robots.txt`: `test_robots_sitemap_llms.py`.
- Post chrome headings (sidebar tags heading, comments heading branches):
  `test_post_chrome_i18n.py` (static); comments heading production render in
  `test_giscus_comments.py` (see above).
- Footer description/author language: `test_footer_i18n.py` (footer-only,
  not `test_i18n.py`); feed language split: `test_seo_bilingual.py` (not
  `test_i18n.py`).

Deliberately duplicated (kept): sidebar/tag language (`test_i18n.py`, list
pages) versus footer language (`test_footer_i18n.py`) versus chrome
headings (`test_post_chrome_i18n.py`) assert different DOM on different page
kinds. Merged: per-loc file resolution removed from
`test_robots_sitemap_llms.py` (every sitemap entry's loc resolution is
asserted, strictly stronger, by the seo alternates guard together with head
agreement); llms.txt URL resolution consolidated in the seo guard, including
the `Canonical:` header — the robots-module llms test is deleted with no
assertion lost.

### Images (`test_check_images.py` + `test_content_images.py` + `test_external_images.py` + `test_vi_alt_text.py`)

- Local budgets (500KB/file, 6MB total, lowercase-hyphen names, dimension
  ceilings) via `script/check-images`: `test_check_images.py` — the single
  source of the budget values. (`test_asset_budget.py` owns the JS/CSS byte
  budgets, a different budget file, not images.)
- Content-image dimensions/captions/figures (intrinsic `width`/`height`,
  titled images as figures, excerpt preference, aspect-ratio box):
  `test_content_images.py`.
- External attachment URLs (allowlisted hosts from `_data/image_hosts.yml`,
  no network I/O, alt + dimensions required) via
  `script/check-external-images`: `test_external_images.py`, including the
  boundary pin that `script/check-images` still owns only the local budgets.
- Vietnamese alt meaningfulness (beyond merely non-empty):
  `test_vi_alt_text.py`.

Deliberately duplicated (kept): intrinsic dimensions (local Markdown,
`test_content_images.py`) versus external dimensions
(`test_external_images.py`, different guard + script) versus VI
meaningfulness (`test_vi_alt_text.py`, qualitative) are three scopes, one
per image kind. Nothing merged in this cluster.

### Consolidation tally (#297)

- Test count: 751 collected before → 750 after (one llms test deleted as
  subsumed, one comments-heading test moved — net one fewer module-level
  production build per run).
- Assertion coverage is preserved: the per-loc sitemap resolution, every
  llms.txt URL (bullets + `Canonical:`), and the EN/VI comments heading in
  production are still asserted, now each in exactly one owner file (see the
  clusters above for where).
- Runtime: one fewer full production Jekyll build per suite run (the
  `test_post_chrome_i18n.py` production build is gone; the shared dev build
  plus the `test_giscus_comments.py` production builds remain).

## Shared fixtures (#56)

`tests/e2e/conftest.py` owns the plumbing every module reuses, so a suite run
does the expensive work once:

- `built_site` - one `bundle exec jekyll build` per session, into a temp dir
  (the fixture logs its invocation to stderr, and to `$E2E_BUILD_LOG` when set);
  when `$E2E_PREBUILT_SITE` points at a built tree (CI's shared `site`
  artifact, #266), the fixture serves that directory instead of rebuilding;
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
  axe only flags the `/resume/` PDF `<object>` when its fallback
  renders zero boxes (the PDF plugin area covers it); headless WebKit has
  no PDF plugin intercept, renders the fallback link inline, and the rule
  never fires there. The waiver stays enforced where it applies.
- Measured runtime for `-m "not static"` (one shared Jekyll build
  plus 230 browser tests): locally ~2-3 min per engine; CI engine-job
  durations (shared-build download + `install --with-deps` + suite) also
  ~2-3 min per engine, with the single shared build in its own job
  (#266).
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
`/resume/`, each at
375px and 1280px in the light colour scheme.

- Fails on any `serious`/`critical` violation: the four #207 exceptions
  were resolved for real in #213, so `ACCEPTED` is empty (a future waiver
  needs a rule + node-target + deferred-fix reason). Fixed nodes that must
  keep rendering (`.lang-switcher`, `.u-email`, `blockquote`, the
  resume `<object>`) plus the shipped rule ids are re-asserted so the
  green run cannot go vacuous.
- `minor`/`moderate` findings are printed but non-blocking.

## Visual regression baselines (`test_visual_regression.py`)

Guard for #208. Markup and layout-math guards cannot see a page *looking*
broken, so this module screenshots a fixed page set at 375/768/1280px and
fails when a fresh capture differs from the committed baseline beyond a small
threshold: the home list, one EN post with its VI twin, the `/tags/` index
with its VI twin, one tag page with its VI twin, about with its VI twin, and
resume with its VI twin (12 pages x 3 viewports = 36 captures in
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
  captures. Local failure captures under `tests/e2e/visual/fresh/` (via
  `$SAVE_FRESH_DIR`) are gitignored (#265).

  Pixel compares skip locally by default (#265): a plain
  `python -m pytest tests/e2e` run leaves the 36 `test_visual_baseline`
  cases skipped with an explicit reason, while the static
  `test_baseline_budget` guard still runs. CI always runs the compares
  (`CI`/`GITHUB_ACTIONS` is set there), so CI stays the gate. To run them
  locally — e.g. after an intentional visual change, before pushing for
  CI-rendered baselines — opt in:

```sh
E2E_VISUAL=1 python -m pytest tests/e2e/test_visual_regression.py -q
```

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

Visual pixel compares (`test_visual_baseline`, #208) skip locally by
default and always run in CI; opt in locally with `E2E_VISUAL=1` (#265).
The static `test_baseline_budget` guard always runs.

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

`.github/workflows/e2e.yml` runs the merged E2E + Lighthouse suite
(Python 3.12, with pip and Playwright browser caches, and Ruby 3.3 with
`bundler-cache`):

- `Classify content-only vs full run` (composite action
  `.github/actions/classify-content-only`, #320, over
  `script/classify-content-only`, #229) — see the classification table
  below;
- `E2E static guards` - `pytest tests/e2e -m static`: no Ruby, no browser.
  Always runs, including on content-only PRs;
- `Build site once` (#320) - one `bundle exec jekyll build` shared by the
  whole workflow, uploaded as the `site` artifact. Skipped on
  content-only PRs;
- `E2E browser (<engine>)` - one job per engine (`chromium`, `firefox`,
  `webkit`, `fail-fast: false` so one engine never hides the others):
  downloads the `site` artifact and runs
  `E2E_BROWSER=<engine> E2E_PREBUILT_SITE=<artifact> pytest tests/e2e
  -m "not static"`, so no engine rebuilds the site or sets up Ruby (the
  `built_site` fixture serves the shared directory as-is; assertions are
  unchanged). Skipped on content-only PRs;
- Hang/retry policy (#421): the suite itself takes ~3-5 min per engine,
  but `playwright install --with-deps` runs apt on every job even with a
  warm browser cache, and stalled mirrors have held that step 10-40 min
  (all three engines, at different times — runner infra, not an engine
  defect; dispatch 39897137841 even failed the install on a cache hit).
  So the install is cache-conditional: on a cache hit the job runs a
  plain `playwright install` (fast no-op) and proves the engine really
  launches with a headless smoke test (`about:blank`, 60 s cap) — only
  a failed smoke triggers `install-deps`, and only a cache miss runs
  `--with-deps`, bounded (6 min per attempt, one retry, then fail
  fast) with a 25-min job backstop. Pinned by
  `tests/e2e/test_browser_install_smoke.py` (static). On failure the job summary
  names the failing specs with the head SHA, and the pytest log (when
  the suite ran) plus fresh visual captures upload as artifacts
  (`warn`, not `error`, when the suite never ran because install failed
  first — the job is already red for the real cause); attempts are
  timestamped and the dpkg lock is awaited (holder logged) before the
  first attempt and between retries — fresh runners boot with
  unattended-upgrades, which the Quiesce apt step stops + masks up
  front (never kill -9 a running apt) — so a red reads as mirror stall
  (~360 s attempts) vs lock contention (seconds, exit 100);
- `Lighthouse CI (desktop)` (`lighthouserc.json`, `preset: desktop`) and
  `Lighthouse CI (mobile)` (`lighthouserc.mobile.json`, default mobile
  emulation, `numberOfRuns: 3` with median assertion) — both served from
  the same shared `site` artifact, so the mobile pass costs no extra
  build. The desktop pass asserts `lighthouserc.json` (`preset: desktop`)
  thresholds; the mobile pass (`lighthouserc.mobile.json`, default mobile
  emulation, `numberOfRuns: 3` with median assertion) covers `/`, the
  photo-heavy Tet 2023 posts (EN/VI), and `/tags/`. Both passes assert
  performance warn-only at 0.85 and
  accessibility/best-practices/SEO as errors at 0.90, so a mobile
  regression is visible per PR without blocking on noise. Both run on PRs,
  manual dispatches, and the daily `master` schedule (#418) — never on
  master pushes — and are skipped on content-only PRs
  alongside the browser matrix;
- `E2E suite result` and `Lighthouse suite result` - aggregators for
  branch protection: each passes when its jobs passed, or when a
  content-only PR skipped them with green static guards (Lighthouse also
  passes on master pushes, where it never runs). Protect these jobs, not
  the matrix jobs (a skipped job reports "skipped", never "success").

Runtime savings (#320): a full PR previously built the identical site
twice — once per workflow (`E2E build site once` + `Lighthouse build
site once`), each with its own Ruby/bundler setup and artifact
round-trip — and now builds it once. Billed minutes drop by roughly one
ruby-setup + build + artifact round-trip; wall-clock is unchanged (the
consumers still run in parallel), and no guard is weakened: same tests,
same engines, same thresholds (before #266 each engine built it
separately; that collapse into one build per workflow is what #320
extends across workflows).

The Jekyll builds (3.9 and 4.2 via `script/cibuild`), the link crawl /
sitemap+feed XML validation, and `script/check-images` (+ external-image
and alt-text checks) in `ci.yaml` always run, including on content-only
PRs. The merged workflow skips its heavy jobs on content-only change
sets instead of a smoke/nightly split.

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
| | `assets/css/**` |
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
manually with `full=true` (the default): the Actions tab → `E2E + Lighthouse` → `Run workflow` on the PR branch. `full=false` on a
dispatch re-runs classification against the branch instead.

Both workflows run on pushes and pull requests to `master`; a superseded push cancels its
in-flight run (`concurrency` with `cancel-in-progress`, #418). `E2E +
Lighthouse` additionally runs on a daily schedule (`0 6 * * *` UTC) so
`master` gets an LHCI signal even though Lighthouse never runs on
master pushes (#418).
