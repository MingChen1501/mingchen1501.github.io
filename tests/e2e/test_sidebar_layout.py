"""Guards for the list-page sidebar (#58, reworked in #63): the home list and
the tag pages.

Both layouts (`_layouts/home.html`, `_layouts/tag.html`) wrap their list in the
same two-column shell — `.site-layout` > `.site-main` + `aside.site-sidebar` —
fed by one shared include, `_includes/site-sidebar.html`, whose two blocks are

1. the highlighted posts: the post file names listed in `_data/highlights.yml`
   (#64, single source of truth), resolved against `site.posts` in the file's
   order, at most five, each with its thumbnail (when the post has one), its
   title and its publication date — or, when the file is empty/missing or no
   entry resolves to a post, the five newest posts with a heading that says
   so, and
2. every tag as a row collapsed by default (`<details>` without `open`)
   showing the tag name (a chip-styled, non-link label — links are invalid
   inside `<summary>`, #114) and its post count, and — once opened — at most three
   post links plus a link to that tag's page.

Acceptance guarded here (issues #58, #63 and #64):

- the shell exists in both layouts with the sidebar *after* the list in the DOM
  (the #47 chips must stay the first `a.tag-chip` in the document, and below
  960px the single column then stacks the sidebar under the list by itself),
- the highlight block is fed by `_data/highlights.yml` — the rendered order
  follows the file exactly (not date order), an unknown slug is skipped
  without breaking the build, a listed-but-unpublished slug never leaks, the
  cap of five binds, and the newest-posts fallback renders for an
  empty/missing/unmatched file — and never by `paginator.posts` (the same
  list on every page); English pages show `Featured`/`Latest posts`, the
  Vietnamese home (`/vi/`) shows `Bài nổi bật`/`Bài mới nhất`,
- the tag rows are collapsed and bounded, and they link to the tag's own newest
  posts,
- the sidebar never scrolls inside itself (#63): no `max-height`/`overflow-y`
  cap, pinned only where its bounded content fits (desktop width *and* enough
  viewport height), still scroll-free while a tag row is open, and
- no horizontal overflow at 375px on `/` *and* on a `/tags/<tag>/` page, with
  every image undistorted and never upscaled (the #50 rules), plus two columns
  beside each other on desktop.

The static assertions run without Ruby or a browser (`@pytest.mark.static`).
The browser assertions need the real site, so they use the session's shared
`built_site`/`built_site_url` fixtures from `conftest.py` (one
`bundle exec jekyll build` for the whole suite, served once over loopback
HTTP), exactly like the #50 and #47 guards. Third-party requests are aborted —
the local `style.css` fully defines the layout.
"""

import contextlib
import datetime
import os
import re
import shutil
import subprocess
import yaml
from pathlib import Path
from urllib.parse import urlparse

import conftest

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
POST_TAGS_INCLUDE = REPO_ROOT / "_includes" / "post-tags.html"
TAG_PAGES_DIR = REPO_ROOT / "tags"
POSTS_DIR = REPO_ROOT / "_posts"
VI_POSTS_DIR = REPO_ROOT / "_vi_posts"
VI_TAG_PAGES_DIR = REPO_ROOT / "vi" / "tags"

HIGHLIGHT_LIMIT = 5
TAG_POSTS_LIMIT = 3

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280
SIDEBAR_WIDTH = 300
# `_sass/minima/custom/_layout.scss` pins the sidebar only from this viewport
# height, at which the bounded column fits beside the list.
STICKY_VIEWPORT_HEIGHT = 740
# A desktop width that is too short for the pinned column: the sidebar must fall
# back to a normal in-flow block, so page scrolling still reaches every row.
SHORT_VIEWPORT_HEIGHT = 600

# One tag page per language to measure (all four pillars are covered by the
# same shell in each language).
TAG_PAGE = f"/tags/{sorted(path.stem for path in TAG_PAGES_DIR.glob('*.md'))[0]}/"
VI_TAG_PAGE = f"/vi/tags/{sorted(path.stem for path in VI_TAG_PAGES_DIR.glob('*.md'))[0]}/"

_MEASURE_JS = """
() => {
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height};
  };
  const main = document.querySelector('.site-main');
  const aside = document.querySelector('aside.site-sidebar');
  const images = [];
  for (const el of document.querySelectorAll('img')) {
    const cs = getComputedStyle(el);
    const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
    const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    const box = el.getBoundingClientRect();
    images.push({
      src: (el.currentSrc || el.src || '').split('/').pop(),
      inSidebar: !!el.closest('.site-sidebar'),
      right: box.right,
      contentWidth: box.width - padX,
      contentHeight: box.height - padY,
      naturalWidth: el.naturalWidth,
      naturalHeight: el.naturalHeight,
    });
  }
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    main: main ? rect(main) : null,
    aside: aside ? rect(aside) : null,
    asidePosition: aside ? getComputedStyle(aside).position : null,
    // #63: the column must fit its own content, not scroll it.
    asideOverflowY: aside ? getComputedStyle(aside).overflowY : null,
    asideScrollHeight: aside ? aside.scrollHeight : null,
    asideClientHeight: aside ? aside.clientHeight : null,
    images: images,
  };
}
"""

# The sidebar's own content: the highlighted posts and every tag row.
_SIDEBAR_JS = """
() => {
  const heading = document.querySelector('.sidebar__section .sidebar__heading');
  return {
    highlightsHeading: heading ? (heading.childNodes[0].textContent || '').trim() : null,
    highlights: Array.from(document.querySelectorAll('.sidebar-posts > .sidebar-post')).map((li) => {
      const title = li.querySelector('a.sidebar-post__title');
      const time = li.querySelector('time.sidebar-post__meta');
      const thumb = li.querySelector('.sidebar-post__thumb img');
      return {
        title: title ? (title.textContent || '').trim() : null,
        url: title ? title.getAttribute('href') : null,
        thumb: thumb ? thumb.getAttribute('src') : null,
        date: time ? (time.textContent || '').trim() : null,
        datetime: time ? time.getAttribute('datetime') : null,
      };
    }),
    tags: Array.from(document.querySelectorAll('.sidebar-tag')).map((li) => {
      const label = li.querySelector('.sidebar-tag__summary span.tag-chip');
      const count = li.querySelector('.tag-index__count');
      const more = li.querySelector('a.sidebar-tag__more');
      const group = li.querySelector('details.sidebar-tag__group');
      return {
        // #114: the summary holds a plain-text label (no link); the tag
        // page URL comes from the panel's own link.
        tag: more ? more.getAttribute('href') : null,
        chipLabel: label ? (label.textContent || '').trim() : null,
        count: count ? (count.textContent || '').trim() : null,
        more: more ? more.getAttribute('href') : null,
        open: group ? group.hasAttribute('open') : null,
        posts: Array.from(li.querySelectorAll('.sidebar-tag__posts a')).map(
          (a) => ({url: a.getAttribute('href'), title: (a.textContent || '').trim()})
        ),
      };
    }),
  };
}
"""

# Hrefs of the main post list — on a tag page that is the tag's own list.
_POST_LIST_JS = """
() => Array.from(
  document.querySelectorAll('.post-list a.post-link')
).map((a) => a.getAttribute('href'))
"""


def _read(path):
    return path.read_text(encoding="utf-8")


# --- `_data/highlights.yml`, the source of the highlight block (#64) ---------

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _front_matter(path):
    match = _FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _front_matter_value(block, key):
    match = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", block, re.M)
    if not match:
        return None
    value = match.group(1)
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _slug_matches(stem, slug):
    """The include accepts a file name with or without its `YYYY-MM-DD-` prefix."""
    return stem == slug or _DATE_PREFIX_RE.sub("", stem) == slug


def _data_highlights(lang="en"):
    """`(date, title, path)` of the posts listed in `_data/highlights.yml`,
    in file order, resolved against that language's post source (`_posts` for
    English, `_vi_posts` for Vietnamese — unknown or unpublished entries
    resolve to nothing and are skipped, like the include skips them)."""
    posts_dir = VI_POSTS_DIR if lang == "vi" else POSTS_DIR
    data_file = REPO_ROOT / "_data" / "highlights.yml"
    if not data_file.is_file():
        return []
    data = yaml.safe_load(data_file.read_text(encoding="utf-8")) or {}
    slugs = (data or {}).get(lang, []) or []
    result = []
    for slug in slugs:
        for path in sorted(posts_dir.glob("*.md")):
            if not _slug_matches(path.stem, str(slug)):
                continue
            front_matter = _front_matter(path)
            if _front_matter_value(front_matter, "published") == "false":
                continue
            # `_posts` names carry the date; `_vi_posts` names do not, so the
            # collection docs declare `date:` in front matter instead.
            date = path.name[:10]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                date = (_front_matter_value(front_matter, "date") or "")[:10]
            result.append(
                (date, _front_matter_value(front_matter, "title"), path)
            )
            break
    return result


@contextlib.contextmanager
def _viewport(browser, built_site_url, width, height=900):
    """A context of the given width with third-party requests blocked."""
    context = browser.new_context(viewport={"width": width, "height": height})
    try:
        page = context.new_page()
        origin = urlparse(built_site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        yield page
    finally:
        context.close()


def _open(page, built_site_url, path):
    response = page.goto(f"{built_site_url}{path}", wait_until="load")
    assert response is not None and response.status == 200, (
        f"{path} did not load (status {response.status if response else 'none'})"
    )
    page.wait_for_selector("aside.site-sidebar", state="attached", timeout=10_000)
    return page


def _load_images(page):
    """Scroll the page so lazy images decode, then settle at the top."""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(150)


# --- throwaway content-state builds (#71) -----------------------------------
#
# The shared `built_site` fixture carries today's content (3 marked posts, no tag
# with more than 2 posts), so the highlight cap and the per-tag bound are never
# exercised at their documented maxima. These helpers build a *copy* of the
# repository with mutated front matter, so a guard can render the maximum content
# state without changing the committed site (or its build output).


def _bundler_env(source):
    import test_stylesheet_cache_version as _csv

    return _csv._bundler_env(source)


def _mutate_front_matter(path, mutator):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return
    front_matter = match.group(1)
    new_front_matter = mutator(front_matter)
    if new_front_matter == front_matter:
        return
    new_text = text.replace(match.group(0), "---\n" + new_front_matter + "\n---\n", 1)
    path.write_text(new_text, encoding="utf-8")


def _build_mutated_site(tmp_path, name, mutate):
    """Copy the repo, apply ``mutate(source)``, build it, return (source, dest)."""
    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip("`bundle` not found: this guard rebuilds the site with Ruby")
    lockfile = REPO_ROOT / "Gemfile.lock"
    if not lockfile.is_file():
        pytest.skip("no Gemfile.lock to reuse for the copied build (`bundle install`)")

    source = tmp_path / f"{name}-src"
    destination = tmp_path / f"{name}-site"
    if source.exists():
        shutil.rmtree(source)
    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(
        REPO_ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", "_site", ".jekyll-cache", ".sass-cache", ".bundle", "vendor",
            "tests", ".ao", ".opencode", "__pycache__", ".pytest_cache",
        ),
    )
    shutil.copy2(lockfile, source / "Gemfile.lock")

    mutate(source)

    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(source),
        env=_bundler_env(source),
        capture_output=True,
        text=True,
        timeout=conftest.BUILD_TIMEOUT_S,
    )
    assert result.returncode == 0, (
        f"{name} build failed ({result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert (destination / "index.html").is_file(), f"{name} build produced no index.html"
    return source, destination


def _unpublish(front_matter):
    """Add `published: false` to a post so Jekyll keeps it out of `site.posts`."""
    if "published: false" in front_matter:
        return front_matter
    return front_matter.rstrip() + "\npublished: false"


def _tag_all_published(front_matter, tag):
    if "published: false" in front_matter:
        return front_matter
    # Replace the tags line with a single tag so one pillar accumulates 4+ posts.
    lines = []
    for line in front_matter.splitlines():
        if re.match(r"\s*tags\s*:", line):
            lines.append(f"tags: [{tag}]")
        else:
            lines.append(line)
    return "\n".join(lines)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
@pytest.mark.parametrize("layout", [HOME_LAYOUT, TAG_LAYOUT], ids=["home", "tag"])
def test_list_pages_wrap_the_list_in_the_sidebar_shell(layout):
    html = _read(layout)
    assert 'class="site-layout"' in html
    assert 'class="site-main"' in html
    assert '<aside class="site-sidebar"' in html
    assert "{%- include site-sidebar.html -%}" in html

    main = html.index('class="site-main"')
    aside = html.index('<aside class="site-sidebar"')
    listing = html.index('class="post-list"', main)
    # Both blocks live in the shared include: no second copy in the layouts.
    assert 'class="sidebar__section"' not in html
    assert 'class="sidebar-posts"' not in html
    assert 'class="sidebar-tags"' not in html
    # The sidebar is after the list in the DOM (single column below 960px then
    # stacks it under the list without `order`), which also keeps the #47 chips
    # the first `a.tag-chip` on the page.
    assert main < listing < aside


@pytest.mark.static
def test_sidebar_include_holds_both_blocks_once():
    html = _read(SIDEBAR_INCLUDE)
    assert html.count('class="sidebar__section"') == 2
    assert html.count('class="sidebar__heading"') == 2
    assert 'class="sidebar-posts"' in html
    assert 'class="sidebar-tags"' in html


@pytest.mark.static
def test_sidebar_highlights_come_from_the_data_file():
    html = _read(SIDEBAR_INCLUDE)
    # Highlight selection lives in `_data/highlights.yml` (#64), resolved
    # against the page's language post source (no `highlight: true` front
    # matter flag anymore).
    assert "site.data.highlights" in html
    assert "sidebar_highlight_slugs" in html
    # Each entry resolves by file name first, then by bare slug, via `where` —
    # never via a nested Liquid loop over the post source (that was the
    # inherited O(entries x posts) double loop, re-rendered on every list page).
    assert html.count('sidebar_source | where: "path"') >= 2
    assert html.count('sidebar_source | where: "slug"') >= 2
    assert "for sidebar_post in sidebar_source" not in html, (
        "the post source must only be scanned via `where`, except the fallback"
    )
    assert "for sidebar_post in sidebar_newest limit: 5" in html
    # The cap binds in the render loop itself (#58/#63/#64).
    assert "sidebar_rendered < 5" in html
    # Nothing resolvable: fall back to the newest posts, and let the heading say
    # which of the two the reader is looking at (never an empty block) — in
    # both languages (#93).
    assert "Bài nổi bật" in html
    assert "Bài mới nhất" in html
    assert "Featured" in html
    assert "Latest posts" in html
    # Not the paginator's page: the block must not change while paging.
    markup = re.sub(r"\{%-?\s*comment.*?endcomment\s*-?%\}", "", html, flags=re.S)
    assert "paginator" not in markup


@pytest.mark.static
def test_sidebar_thumbnail_falls_back_to_the_first_body_image():
    html = _read(SIDEBAR_INCLUDE)
    assert "sidebar_post.image" in html
    assert "split: '<img'" in html
    assert """split: 'src="'""" in html
    # #308: local sources reuse the small cover-cropped variants from
    # `script/generate-thumbnails` (the same mapping as the list
    # thumbnails), never the full-size originals — with explicit dimensions
    # so the browser reserves the box (no CLS).
    assert "/assets/img/thumbs/" in html
    assert "-240.webp" in html
    assert 'width="120" height="90"' in html
    assert "?v=" in html
    # No placeholder art and no sidebar-specific image files: a post without
    # an image simply renders without a thumbnail.
    assert "post-thumb__placeholder" not in html
    assert "placeholder.svg" not in html


@pytest.mark.static
def test_sidebar_tag_summary_holds_no_links():
    """#114: no interactive content inside `<summary>` (EN + VI rows)."""
    html = _read(SIDEBAR_INCLUDE)
    summaries = re.findall(r"<summary.*?</summary>", html, re.S)
    assert summaries, "the sidebar tag rows must keep their summary elements"
    for summary in summaries:
        assert "<a " not in summary, (
            f"a link nests inside <summary>, which is invalid and breaks "
            f"keyboard/AT behaviour: {summary[:120]!r}"
        )
        assert "include post-tags.html" not in summary, (
            "the shared chip include renders links, so it cannot stay inside "
            "<summary>"
        )
    # The summary label reuses the chip look on a plain span (visuals
    # unchanged), and the tag-page link lives in the opened panel.
    # Labels and slugs resolve per language through the shared
    # `_includes/tag-label.html` partial (#129, #175), so the row links the
    # tag page of the current language.
    assert '<span class="tag-chip">' in html
    assert "include tag-label.html" in html
    assert "key=sidebar_tag_name" in html
    assert "lang=sidebar_lang" in html
    assert "site.data.tag_labels" not in html
    assert "sidebar_tag_label | escape" in html
    assert re.search(
        r"sidebar_tag_base\s*\|\s*append: sidebar_tag_slug\s*\|\s*append: '/' \| relative_url", html
    )
    # The tag links stay inside the page's language (#93).
    assert 'sidebar_tag_base = "/tags/"' in html
    assert 'sidebar_tag_base = "/vi/tags/"' in html
    # Collapsed by default (#63) and bounded per tag: the tag's own page is one
    # click away (`Xem tất cả`), so the column stays short.
    assert '<details class="sidebar-tag__group">' in html
    assert '<details class="sidebar-tag__group" open>' not in html
    assert f"limit: {TAG_POSTS_LIMIT}" in html


@pytest.mark.static
def test_custom_styles_define_the_sidebar_grid():
    scss = conftest.custom_styles_text()
    assert ".site-layout {" in scss
    # Two columns from the breakpoint, one below it; `minmax(0, 1fr)` instead of
    # a bare `1fr` so a long unbreakable run cannot widen the phone layout (#50).
    assert "grid-template-columns: minmax(0, 1fr) $site-sidebar-width;" in scss
    assert f"$site-sidebar-width: {SIDEBAR_WIDTH}px;" in scss
    assert "grid-template-columns: minmax(0, 1fr);" in scss
    assert "grid-template-columns: 1fr;" not in scss
    # The wider wrapper belongs to the list pages' content column only.
    assert ".layout-home main .wrapper," in scss
    assert ".layout-tag main .wrapper {" in scss
    # Pinned only where the sidebar fits beside the list: the desktop breakpoint
    # *and* a viewport tall enough for its bounded content (#63). The pixel
    # values live in the hoisted variables (#174); the browser viewports below
    # reuse the same constants so the two can never drift apart.
    assert "$two-column-breakpoint: 960px;" in scss
    assert f"$pinned-sidebar-min-height: {STICKY_VIEWPORT_HEIGHT}px;" in scss
    assert (
        "@media screen and (min-width: $two-column-breakpoint) and "
        "(min-height: $pinned-sidebar-min-height)" in scss
    )
    assert re.search(
        r"@media screen and \(min-width: \$two-column-breakpoint\) and "
        r"\(min-height: \$pinned-sidebar-min-height\)\s*\{[^}]*\.site-sidebar\s*\{[^}]*position: sticky",
        scss,
    ), "the site sidebar must be sticky only where it fits beside the list"
    # Post pages keep their own sticky column (#45): pinned from the desktop
    # breakpoint only, without the viewport-height gate, so post-page behaviour
    # is unchanged.
    assert re.search(
        r"@media screen and \(min-width: \$two-column-breakpoint\)\s*\{[^}]*\.post-sidebar\s*\{[^}]*position: sticky",
        scss,
    ), "the post sidebar must keep its own sticky rule at the two-column breakpoint"
    # The thumbnail keeps the source ratio (the #50 guard measures real rects):
    # capped in a box, never cropped and never upscaled. List-item thumbnails
    # (#226) intentionally differ: they crop inside a fixed 120x90 box, so the
    # no-crop rule below is scoped to the sidebar rule only.
    assert re.search(
        r"\.sidebar-post__thumb img\s*\{[^}]*max-width: 96px;[^}]*max-height: 60px;", scss
    )
    sidebar_thumb_rule = re.search(
        r"\.sidebar-post__thumb img\s*\{[^}]*\}", scss
    ).group(0)
    assert "object-fit" not in sidebar_thumb_rule, (
        "sidebar thumbnails are not cropped to a fixed ratio"
    )
    assert re.search(
        r"\.post-thumb img\s*\{[^}]*object-fit: cover;", scss
    ), "list thumbnails crop inside the fixed 120x90 box (#226)"
    # `_sass/minima/_base.scss` gives every `img` 20px of padding inside its
    # border box, which would distort a two-`max-*` box (see the comment there);
    # the thumbnail resets it.
    assert re.search(r"\.sidebar-post__thumb img\s*\{[^}]*padding: 0;", scss)


@pytest.mark.static
def test_sidebar_height_is_bounded_instead_of_an_inner_scrollbar():
    """#63: the height budget replaces #58's `max-height` + `overflow-y` cap."""
    # Comments mention the removed cap, so only the declarations count.
    scss = re.sub(r"//[^\n]*", "", conftest.custom_styles_text())
    assert "overflow-y" not in scss, "the sidebar must not scroll inside itself"
    assert "100vh" not in scss, "no viewport-height cap on the sidebar either"
    # The budget itself: a title that cannot spill, and a capped thumbnail.
    assert "-webkit-line-clamp: 2" in scss
    assert re.search(r"\.sidebar-post__thumb img\s*\{[^}]*max-height: 60px;", scss)


@pytest.mark.static
def test_post_page_and_comments_are_untouched_by_the_sidebar():
    """The list sidebar must not leak into the post page (#45 has its own)."""
    html = _read(POST_LAYOUT)
    assert 'class="post-layout"' in html
    assert 'class="post-sidebar"' in html
    assert "site-sidebar.html" not in html
    assert "site-sidebar" not in _read(REPO_ROOT / "_includes" / "comments.html")


# --- browser guards (need Ruby + a browser) ---------------------------------


@pytest.mark.parametrize(
    "home_path, lang, extra_paths, hit_heading, miss_heading",
    [
        ("/", "en", ("/page2/", TAG_PAGE), "Featured", "Latest posts"),
        ("/vi/", "vi", (VI_TAG_PAGE,), "Bài nổi bật", "Bài mới nhất"),
    ],
)
def test_sidebar_shows_the_same_highlights_on_every_page(
    home_path, lang, extra_paths, hit_heading, miss_heading,
    built_site, built_site_url, browser,
):
    """The highlights are the posts listed in `_data/highlights.yml`, in file order."""
    expected = _data_highlights(lang)[:HIGHLIGHT_LIMIT]

    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, home_path)
        sidebar = page.evaluate(_SIDEBAR_JS)

        if expected:
            assert sidebar["highlightsHeading"] == hit_heading, (
                f"with posts listed in `_data/highlights.yml` the {lang} block "
                f"is `{hit_heading}`"
            )
        else:
            # Nothing resolvable in the data file: the block falls back to the
            # newest posts and says so, instead of rendering an empty box.
            assert sidebar["highlightsHeading"] == miss_heading
            expected = [
                (None, title, None)
                for title in page.evaluate(
                    "() => Array.from(document.querySelectorAll('.post-list a.post-link')).map((a) => a.textContent.trim())"
                )[:HIGHLIGHT_LIMIT]
            ]

        assert len(sidebar["highlights"]) == len(expected), (
            f"expected {len(expected)} highlights, got {sidebar['highlights']}"
        )
        assert [entry["title"] for entry in sidebar["highlights"]] == [
            title for _, title, _ in expected
        ], (
            "the sidebar must list exactly the posts from `_data/highlights.yml`, "
            f"in the file's order: {sidebar['highlights']}"
        )

        for (date, title, path), entry in zip(expected, sidebar["highlights"]):
            assert entry["title"], f"sidebar entry without a title: {entry}"
            if path is not None:
                # Post-source order, thumbnail resolution and date all come
                # from the post's own file.
                assert entry["datetime"][:10] == date, (
                    f"{path.name} is dated {date} but the sidebar shows "
                    f"{entry['datetime']}"
                )
            # The compact `dd-mm-yyyy` label renders that same instant, because
            # the verbose date format does not fit a 300px column.
            assert re.fullmatch(r"\d{2}-\d{2}-\d{4}", entry["date"] or ""), (
                f"unexpected highlight date label: {entry['date']!r}"
            )
            published = datetime.datetime.fromisoformat(entry["datetime"])
            assert entry["date"] == published.strftime("%d-%m-%Y"), (
                f"the date label {entry['date']!r} does not match "
                f"{entry['datetime']}"
            )
            assert entry["url"].startswith("/")
            assert (built_site / entry["url"].lstrip("/")).is_file(), (
                f"highlight {entry['url']} is not in the build"
            )
            response = page.request.get(f"{built_site_url}{entry['url']}")
            assert response.status == 200, f"{entry['url']} returned {response.status}"

        # The same list on every list page of that language: it comes from the
        # language's post source, not from the paginator's page.
        for path in extra_paths:
            _open(page, built_site_url, path)
            assert page.evaluate(_SIDEBAR_JS)["highlights"] == sidebar["highlights"], (
                f"{path} shows a different sidebar than the {lang} home list"
            )


@pytest.mark.parametrize(
        "home_path, tag_base",
        [
            ("/", "/tags/"),
            ("/vi/", "/vi/tags/"),
        ],
    )
def test_sidebar_tag_rows_are_collapsed_bounded_and_expandable(
    home_path, tag_base, built_site, built_site_url, browser
):
    # Singular/plural copy (#149): "1 post tagged", "N posts tagged".
    intro_re = r"(\d+) bài viết" if tag_base.startswith("/vi/") else r"(\d+) posts? tagged"
    count_unit = "bài" if tag_base.startswith("/vi/") else "posts"
    # Singular/plural copy (#149): "1 post", "N posts"; VI is invariant.
    def _expected_count(total):
        if tag_base.startswith("/vi/"):
            return f"{total} bài"
        return f"{total} post" if total == 1 else f"{total} posts"
    # Localized slug -> label for this sidebar's language (#129).
    tag_labels = yaml.safe_load(
        (REPO_ROOT / "_data" / "tag_labels.yml").read_text(encoding="utf-8")
    )
    if tag_base.startswith("/vi/"):
        expected_labels = {
            entry["slug_vi"]: entry["vi"] for entry in tag_labels.values()
        }
    else:
        expected_labels = {
            entry["slug_en"]: entry["en"] for entry in tag_labels.values()
        }
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, home_path)
        groups = page.evaluate(_SIDEBAR_JS)["tags"]
        assert groups, "the sidebar must render the tag block"

        for index, group in enumerate(groups):
            match = re.fullmatch(
                re.escape(tag_base) + r"([a-z0-9-]+)/", group["tag"] or ""
            )
            assert match, f"unexpected tag chip href: {group['tag']}"
            tag = match.group(1)
            assert group["chipLabel"] == expected_labels[tag], (
                f"the chip label {group['chipLabel']!r} is not the localized "
                f"label for `{tag}`"
            )
            assert group["more"] == group["tag"]
            assert group["open"] is False, (
                f"tag `{tag}` must be collapsed by default (#63), so the column "
                "stays short"
            )
            assert 0 < len(group["posts"]) <= TAG_POSTS_LIMIT, (
                f"tag `{tag}` lists an unbounded or empty set: {group['posts']}"
            )

            # The tag's own page is the reference for which posts carry the tag.
            tag_dir = built_site / tag_base.strip("/") / tag / "index.html"
            assert tag_dir.is_file(), (
                f"{tag_base}{tag}/ is missing from the build"
            )
            response = page.request.get(f"{built_site_url}{tag_base}{tag}/")
            assert response.status == 200, (
                f"{tag_base}{tag}/ returned {response.status}"
            )

            _open(page, built_site_url, f"{tag_base}{tag}/")
            expected = page.evaluate(_POST_LIST_JS)
            tag_page_text = page.inner_text(".tag-page__intro")
            total = int(re.search(intro_re, tag_page_text).group(1))
            assert total == len(expected), (
                f"{tag_base}{tag}/ says {total} posts but lists {len(expected)}"
            )
            assert [post["url"] for post in group["posts"]] == expected[:TAG_POSTS_LIMIT], (
                f"the sidebar block for `{tag}` must list the tag's newest posts: "
                f"{group['posts']} != {expected[:TAG_POSTS_LIMIT]}"
            )
            assert group["count"] == _expected_count(total), (
                f"the sidebar count for `{tag}` must match the tag page: "
                f"{group['count']!r} vs {total}"
            )
            for post in group["posts"]:
                assert post["title"], f"tag block entry without a title: {post}"
                detail = page.request.get(f"{built_site_url}{post['url']}")
                assert detail.status == 200, (
                    f"tag block links to {post['url']}, which returned {detail.status}"
                )

            # Collapsed in the rendering too — not just in the markup — then one
            # click on the row opens it. The click lands on the count: the
            # label next to it is plain text (#114 — no link inside
            # `<summary>`), so the whole summary is the row's toggle area.
            _open(page, built_site_url, home_path)
            row = page.locator(".sidebar-tag").nth(index)
            assert not row.locator(".sidebar-tag__posts a").first.is_visible(), (
                f"the posts of `{tag}` must stay hidden until the row is opened"
            )
            assert not row.locator("a.sidebar-tag__more").is_visible()
            row.locator(".tag-index__count").click()
            assert row.locator("details").get_attribute("open") is not None, (
                f"clicking the `{tag}` row must open it"
            )
            for post in group["posts"]:
                assert row.locator(f'a[href="{post["url"]}"]').first.is_visible(), (
                    f"opening `{tag}` must reveal {post['url']}"
                )
            assert row.locator("a.sidebar-tag__more").is_visible(), (
                f"opening `{tag}` must offer the link to {tag_base}{tag}/"
            )


def test_sidebar_sets_two_columns_on_desktop_and_one_on_phones(built_site_url, browser):
    for path in ("/", TAG_PAGE):
        with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
            _open(page, built_site_url, path)
            metrics = page.evaluate(_MEASURE_JS)
            assert metrics["main"] and metrics["aside"], (
                f"{path}: the sidebar shell is missing at desktop width"
            )
            assert metrics["main"]["right"] <= metrics["aside"]["left"] + 0.5, (
                f"{path}: the sidebar must sit beside the list at {DESKTOP_WIDTH}px "
                f"(main right {metrics['main']['right']} > aside left {metrics['aside']['left']})"
            )
            assert abs(metrics["aside"]["width"] - SIDEBAR_WIDTH) <= 10, (
                f"{path}: the desktop sidebar should be {SIDEBAR_WIDTH}px wide, "
                f"got {metrics['aside']['width']}"
            )
            assert metrics["asidePosition"] == "sticky", (
                f"{path}: the sidebar must be sticky on desktop (D5), got "
                f"{metrics['asidePosition']}"
            )
            assert metrics["scrollWidth"] <= metrics["innerWidth"], (
                f"{path}: horizontal overflow at {DESKTOP_WIDTH}px"
            )

        # Pinned right at the height threshold: the whole column still fits, so
        # nothing sits unreachable under the fold (#63).
        with _viewport(browser, built_site_url, DESKTOP_WIDTH, STICKY_VIEWPORT_HEIGHT) as page:
            _open(page, built_site_url, path)
            metrics = page.evaluate(_MEASURE_JS)
            assert metrics["asidePosition"] == "sticky", (
                f"{path}: the sidebar is pinned from {STICKY_VIEWPORT_HEIGHT}px of "
                "viewport height"
            )
            assert metrics["aside"]["bottom"] <= metrics["innerHeight"], (
                f"{path}: the pinned sidebar must fit the "
                f"{STICKY_VIEWPORT_HEIGHT}px viewport, bottom "
                f"{metrics['aside']['bottom']} > {metrics['innerHeight']}"
            )

        # A desktop viewport too short to hold the column: not pinned, so page
        # scrolling still reaches every row instead of clipping the last one.
        with _viewport(browser, built_site_url, DESKTOP_WIDTH, SHORT_VIEWPORT_HEIGHT) as page:
            _open(page, built_site_url, path)
            metrics = page.evaluate(_MEASURE_JS)
            assert metrics["main"]["right"] <= metrics["aside"]["left"] + 0.5, (
                f"{path}: still two columns at {DESKTOP_WIDTH}px"
            )
            assert metrics["asidePosition"] == "static", (
                f"{path}: at {SHORT_VIEWPORT_HEIGHT}px of viewport height the "
                f"sidebar must not be pinned, got {metrics['asidePosition']}"
            )

        with _viewport(browser, built_site_url, PHONE_WIDTH) as page:
            _open(page, built_site_url, path)
            metrics = page.evaluate(_MEASURE_JS)
            assert metrics["aside"]["top"] >= metrics["main"]["bottom"] - 0.5, (
                f"{path}: at {PHONE_WIDTH}px the sidebar must come after the list "
                f"(aside top {metrics['aside']['top']} < main bottom "
                f"{metrics['main']['bottom']})"
            )
            assert metrics["asidePosition"] == "static", (
                f"{path}: the sidebar must not be sticky on phones, got "
                f"{metrics['asidePosition']}"
            )
            assert metrics["aside"]["width"] <= metrics["innerWidth"], (
                f"{path}: the sidebar is wider than the {PHONE_WIDTH}px viewport"
            )


@pytest.mark.parametrize("path", ["/", TAG_PAGE])
def test_sidebar_never_scrolls_inside_itself(path, built_site_url, browser):
    """#63: the column is sized to fit instead of scrolling its own content."""
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, path)
        metrics = page.evaluate(_MEASURE_JS)

        assert metrics["asideOverflowY"] == "visible", (
            f"{path}: the sidebar must not clip its content into a scroll box "
            f"(#58 capped it with `max-height` + `overflow-y`); got "
            f"overflow-y: {metrics['asideOverflowY']}"
        )
        assert metrics["asideScrollHeight"] <= metrics["asideClientHeight"] + 1, (
            f"{path}: the sidebar overflows its own box: "
            f"scrollHeight {metrics['asideScrollHeight']} > clientHeight "
            f"{metrics['asideClientHeight']}"
        )
        assert metrics["aside"]["height"] <= metrics["innerHeight"], (
            f"{path}: the sidebar is taller than the viewport it is pinned in"
        )

        # Opening a tag row grows the column in the page instead of starting a
        # scroll area (the reader can then scroll the page back to it).
        page.locator(".sidebar-tag").first.locator(".tag-index__count").click()
        expanded = page.evaluate(_MEASURE_JS)
        assert expanded["asideScrollHeight"] <= expanded["asideClientHeight"] + 1, (
            f"{path}: with a tag row open the sidebar scrolls inside itself: "
            f"scrollHeight {expanded['asideScrollHeight']} > clientHeight "
            f"{expanded['asideClientHeight']}"
        )


@pytest.mark.parametrize("path", ["/", TAG_PAGE])
def test_no_horizontal_overflow_from_the_sidebar_at_375px(path, built_site_url, browser):
    with _viewport(browser, built_site_url, PHONE_WIDTH) as page:
        _open(page, built_site_url, path)
        _load_images(page)
        metrics = page.evaluate(_MEASURE_JS)

        assert metrics["scrollWidth"] <= metrics["innerWidth"], (
            f"{path}: horizontal overflow at {PHONE_WIDTH}px: scrollWidth "
            f"{metrics['scrollWidth']} > innerWidth {metrics['innerWidth']}"
        )

        sidebar_images = [image for image in metrics["images"] if image["inSidebar"]]
        for image in metrics["images"]:
            if not image["naturalWidth"] or not image["naturalHeight"]:
                continue
            assert image["right"] <= metrics["innerWidth"] + 0.5, (
                f"{path}: image {image['src']} overhangs the {PHONE_WIDTH}px viewport"
            )
            assert image["contentWidth"] <= image["naturalWidth"] + 1, (
                f"{path}: image {image['src']} is upscaled at {PHONE_WIDTH}px: "
                f"{image['contentWidth']}px > {image['naturalWidth']}px"
            )
            natural_ratio = image["naturalWidth"] / image["naturalHeight"]
            rendered_ratio = image["contentWidth"] / image["contentHeight"]
            assert abs(rendered_ratio - natural_ratio) <= 0.01 * natural_ratio, (
                f"{path}: image {image['src']} is distorted: rendered ratio "
                f"{rendered_ratio:.3f} != natural {natural_ratio:.3f}"
            )

        # A pass on the sidebar's own thumbnail only means something if the
        # lazy image really decoded while we measured (the `max-width`/
        # `max-height` box must not squeeze the source ratio).
        assert sidebar_images, f"{path}: no sidebar thumbnail to measure"
        for image in sidebar_images:
            assert image["naturalWidth"], (
                f"{path}: the sidebar thumbnail {image['src']} never decoded, so it "
                "was not measured"
            )


# --- content-state guards (#71/#64): exercise the documented maxima ---------
#
# The shared `built_site` fixture carries today's content (3 listed posts, no
# tag with more than 2 posts), so the highlight cap, the file-order rule and
# the per-tag bound are never exercised at their documented maxima. These
# helpers build a *copy* of the repository with a mutated `_data/highlights.yml`
# (and/or mutated front matter), so a guard can render the maximum or exotic
# content state without changing the committed site (or its build output).


def _published_stems(source):
    """File-name stems (without `.md`) of the published posts, sorted."""
    stems = []
    for path in sorted((source / "_posts").glob("*.md")):
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", path.read_text(encoding="utf-8"), re.S)
        front_matter = match.group(1) if match else ""
        if _front_matter_value(front_matter, "published") == "false":
            continue
        stems.append(path.stem)
    return stems


def _write_highlights(source, text):
    data_dir = source / "_data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "highlights.yml").write_text(text, encoding="utf-8")


def _mutate_list_all_published(source):
    """List every published English post in `_data/highlights.yml` (6 today):
    the cap must bind at 5, in the file's (sorted) order."""
    _write_highlights(source, "en: [" + ", ".join(_published_stems(source)) + "]\n")


def _mutate_delete_highlights(source):
    """The missing-file fallback case."""
    data_file = source / "_data" / "highlights.yml"
    if data_file.is_file():
        data_file.unlink()


def _mutate_empty_highlights(source):
    """The empty-file fallback case."""
    _write_highlights(source, "en: []\n")


def _mutate_unknown_only_highlights(source):
    """A file whose entries all resolve to nothing must also fall back."""
    _write_highlights(source, "en: [no-such-post-xyzzy]\n")


# A listed slug that is real today but unpublished at build time, and a bare
# (dateless) slug, mixed into a deliberately non-chronological order.
_ORDER_DRAFT_POST = "2023-01-31-my-tet-holiday-2023"


def _mutate_order_skip_draft(source):
    """File order != date order, plus an unknown and an unpublished entry.

    The rendered block must keep the file's order, skip the unknown entry
    silently and never leak the unpublished post.
    """
    _mutate_front_matter(source / "_posts" / f"{_ORDER_DRAFT_POST}.md", _unpublish)
    _write_highlights(
        source,
        "en:\n"
        "  - no-such-post-xyzzy\n"
        "  - 2022-10-27-brewing-vietnamese-coffee\n"
        f"  - {_ORDER_DRAFT_POST}\n"
        "  - switching-from-windows-11-to-fedora\n"
        "  - 2022-12-25-explaining-the-internet\n",
    )


def _mutate_tag_all_ai_agent(source):
    for path in (source / "_posts").glob("*.md"):
        _mutate_front_matter(path, lambda fm: _tag_all_published(fm, "ai-agent"))
    # Drop tag pages for pillars that no longer have any published post, so the
    # build does not try to sort a null `site.tags[...]` collection.
    tags_dir = source / "tags"
    if tags_dir.is_dir():
        for path in tags_dir.glob("*.md"):
            if path.stem != "ai-agent":
                path.unlink()
    # The tags index sorts every pillar; pillars with no posts become null.
    tags_index = source / "tags.md"
    if tags_index.is_file():
        tags_index.unlink()


def _post_title(path):
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", path.read_text(encoding="utf-8"), re.S)
    return _front_matter_value(match.group(1) if match else "", "title")


def test_sidebar_highlight_cap_holds_with_six_listed_posts(tmp_path, browser):
    """Content-state guard (#71/#64): with 6 posts listed, only 5 render.

    Today's data file lists 3 posts, so a wrong limit of 3/4 is invisible to
    the browser tier. Listing all 6 published posts forces the cap to bind,
    and the rows must be the file's first 5 entries in the file's order.
    """
    _source, destination = _build_mutated_site(tmp_path, "hl-six", _mutate_list_all_published)

    stems = _published_stems(REPO_ROOT)
    assert len(stems) > HIGHLIGHT_LIMIT, "this guard needs more published posts than the cap"
    expected = [
        _post_title(POSTS_DIR / f"{stem}.md")
        for stem in stems[:HIGHLIGHT_LIMIT]
    ]

    with conftest._served(destination) as url:
        with _viewport(browser, url, DESKTOP_WIDTH) as page:
            _open(page, url, "/")
            sidebar = page.evaluate(_SIDEBAR_JS)
            assert sidebar["highlightsHeading"] == "Featured", (
                "with posts listed in the data file the block is `Featured`"
            )
            assert len(sidebar["highlights"]) == HIGHLIGHT_LIMIT, (
                f"expected the highlight cap of {HIGHLIGHT_LIMIT} rows with 6 "
                f"listed posts, got {len(sidebar['highlights'])}: "
                f"{sidebar['highlights']}"
            )
            # The cap binds on the file's first 5 entries, in file order — not
            # on date order (here the same, but asserted from the file).
            assert [entry["title"] for entry in sidebar["highlights"]] == expected, (
                "the capped block must show the data file's first 5 entries in "
                f"the file's order: {sidebar['highlights']} != {expected}"
            )
            # The 6th listed post must not appear.
            sixth = _post_title(POSTS_DIR / f"{stems[HIGHLIGHT_LIMIT]}.md")
            assert sixth not in [entry["title"] for entry in sidebar["highlights"]], (
                f"the highlight limit did not cap the block: {sixth} rendered"
            )


@pytest.mark.parametrize(
    "mutate, kind",
    [
        (_mutate_delete_highlights, "missing-file"),
        (_mutate_empty_highlights, "empty-file"),
        (_mutate_unknown_only_highlights, "unknown-slugs-only"),
    ],
)
def test_sidebar_highlight_fallback_shows_five_newest(tmp_path, browser, mutate, kind):
    """Content-state guard (#71/#64): the fallback renders the 5 newest.

    An empty file, a missing file, or a file whose entries all resolve to
    nothing must all take the `Bài mới nhất` path at its documented maximum
    (5 rows), in newest-first order.
    """
    _source, destination = _build_mutated_site(tmp_path, f"hl-none-{kind}", mutate)

    newest = sorted(
        (path.stem[:10] for path in POSTS_DIR.glob("*.md")
         if _front_matter_value(_front_matter(path), "published") != "false"),
        reverse=True,
    )[:HIGHLIGHT_LIMIT]

    with conftest._served(destination) as url:
        with _viewport(browser, url, DESKTOP_WIDTH) as page:
            _open(page, url, "/")
            sidebar = page.evaluate(_SIDEBAR_JS)
            assert sidebar["highlightsHeading"] == "Latest posts", (
                f"with a {kind} data file the block falls back to `Latest posts`"
            )
            assert len(sidebar["highlights"]) == HIGHLIGHT_LIMIT, (
                f"expected {HIGHLIGHT_LIMIT} fallback highlights, got "
                f"{len(sidebar['highlights'])}: {sidebar['highlights']}"
            )
            assert [entry["datetime"][:10] for entry in sidebar["highlights"]] == newest, (
                "the fallback must show the 5 newest posts, newest first: "
                f"{sidebar['highlights']} != {newest}"
            )


def test_sidebar_highlights_follow_file_order_and_skip_unknown_and_draft(tmp_path, browser):
    """Content-state guard (#64): file order wins; bad entries are skipped.

    The data file lists posts in a deliberately non-chronological order, mixed
    with an unknown slug and a real-but-unpublished slug:

    - the rendered order must follow the file exactly (the oldest listed post
      first — so an implementation that silently re-sorts by date fails),
    - the unknown slug must be skipped without breaking the build, and
    - the unpublished post must never leak into the sidebar (Jekyll keeps it
      out of `site.posts`; the lookup must not resurrect it).

    One entry is written as a bare slug (without the `YYYY-MM-DD-` prefix) to
    pin the documented "with or without the prefix" resolution.
    """
    _source, destination = _build_mutated_site(tmp_path, "hl-order", _mutate_order_skip_draft)

    draft_title = _post_title(POSTS_DIR / f"{_ORDER_DRAFT_POST}.md")
    expected_titles = [
        _post_title(POSTS_DIR / "2022-10-27-brewing-vietnamese-coffee.md"),  # oldest, first
        _post_title(POSTS_DIR / "2026-01-01-switching-from-windows-11-to-fedora.md"),  # bare slug
        _post_title(POSTS_DIR / "2022-12-25-explaining-the-internet.md"),
    ]
    expected_dates = [
        path.stem[:10]
        for path in (
            POSTS_DIR / "2022-10-27-brewing-vietnamese-coffee.md",
            POSTS_DIR / "2026-01-01-switching-from-windows-11-to-fedora.md",
            POSTS_DIR / "2022-12-25-explaining-the-internet.md",
        )
    ]
    # The guard only proves "order follows the file" if file order differs
    # from date order; fail loudly if content drift makes it vacuous.
    assert expected_dates != sorted(expected_dates, reverse=True), (
        "reorder `_mutate_order_skip_draft` so the file order differs from date order"
    )

    with conftest._served(destination) as url:
        with _viewport(browser, url, DESKTOP_WIDTH) as page:
            _open(page, url, "/")
            sidebar = page.evaluate(_SIDEBAR_JS)

            assert sidebar["highlightsHeading"] == "Featured", (
                "with resolvable entries the block is `Featured` (the build "
                "did not fail — the unknown entry was skipped)"
            )
            assert [entry["title"] for entry in sidebar["highlights"]] == expected_titles, (
                "the sidebar must follow `_data/highlights.yml` order, skipping "
                f"unknown and unpublished entries: {sidebar['highlights']} != "
                f"{expected_titles}"
            )
            assert draft_title not in [entry["title"] for entry in sidebar["highlights"]], (
                f"the unpublished post {draft_title!r} leaked into the highlights"
            )
            sidebar_text = page.inner_text("aside.site-sidebar")
            assert draft_title not in sidebar_text, (
                f"the unpublished post {draft_title!r} leaked into the sidebar text"
            )
            for entry in sidebar["highlights"]:
                assert (destination / entry["url"].lstrip("/")).is_file(), (
                    f"highlight {entry['url']} is not in the build"
                )
                response = page.request.get(f"{url}{entry['url']}")
                assert response.status == 200, f"{entry['url']} returned {response.status}"


def test_sidebar_tag_bound_holds_with_four_plus_posts_in_one_tag(tmp_path, browser):
    """Content-state guard (#71): a tag with 4+ posts shows at most 3 rows.

    Today's biggest tag has 2 posts, so `0 < len(tag posts) <= 3` is vacuous.
    Collapsing every published post onto one tag forces the per-tag bound to bind.
    """
    _source, destination = _build_mutated_site(tmp_path, "tag-many", _mutate_tag_all_ai_agent)

    with conftest._served(destination) as url:
        with _viewport(browser, url, DESKTOP_WIDTH) as page:
            _open(page, url, "/")
            groups = page.evaluate(_SIDEBAR_JS)["tags"]
            target = next((g for g in groups if "ai-agent" in (g["tag"] or "")), None)
            assert target is not None, "the ai-agent tag row must render"
            assert 0 < len(target["posts"]) <= TAG_POSTS_LIMIT, (
                f"tag `ai-agent` lists an unbounded or empty set: {target['posts']}"
            )
            assert len(target["posts"]) == TAG_POSTS_LIMIT, (
                f"expected the per-tag cap of {TAG_POSTS_LIMIT} rows with 4+ posts, "
                f"got {len(target['posts'])}: {target['posts']}"
            )
