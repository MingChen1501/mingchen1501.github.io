"""Guards for the list-page sidebar (#58, reworked in #63): the home list and
the tag pages.

Both layouts (`_layouts/home.html`, `_layouts/tag.html`) wrap their list in the
same two-column shell — `.site-layout` > `.site-main` + `aside.site-sidebar` —
fed by one shared include, `_includes/site-sidebar.html`, whose two blocks are

1. the highlighted posts: the posts that opt in with `highlight: true` in their
   own front matter (`_posts/*.md`), newest first, at most five, each with its
   thumbnail (when the post has one), its title and its publication date — or,
   when no post is marked yet, the five newest posts with a heading that says
   so, and
2. every tag as a row collapsed by default (`<details>` without `open`)
   showing the tag chip and its post count, and — once opened — at most three
   post links plus a link to that tag's page.

Acceptance guarded here (issues #58 and #63):

- the shell exists in both layouts with the sidebar *after* the list in the DOM
  (the #47 chips must stay the first `a.tag-chip` in the document, and below
  960px the single column then stacks the sidebar under the list by itself),
- the highlight block is fed by the posts' own front matter, not by the newest
  posts and not by `paginator.posts` (the same list on every page),
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
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
POST_TAGS_INCLUDE = REPO_ROOT / "_includes" / "post-tags.html"
CUSTOM_STYLES = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
TAG_PAGES_DIR = REPO_ROOT / "tags"
POSTS_DIR = REPO_ROOT / "_posts"

HIGHLIGHT_LIMIT = 5
TAG_POSTS_LIMIT = 3

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280
SIDEBAR_WIDTH = 300
# `_sass/minima/custom-styles.scss` pins the sidebar only from this viewport
# height, at which the bounded column fits beside the list.
STICKY_VIEWPORT_HEIGHT = 740
# A desktop width that is too short for the pinned column: the sidebar must fall
# back to a normal in-flow block, so page scrolling still reaches every row.
SHORT_VIEWPORT_HEIGHT = 600

# One tag page to measure (all four pillars are covered by the same shell).
TAG_PAGE = f"/tags/{sorted(path.stem for path in TAG_PAGES_DIR.glob('*.md'))[0]}/"

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
      const chip = li.querySelector('a.tag-chip');
      const count = li.querySelector('.tag-index__count');
      const more = li.querySelector('a.sidebar-tag__more');
      const group = li.querySelector('details.sidebar-tag__group');
      return {
        tag: chip ? chip.getAttribute('href') : null,
        chipLabel: chip ? (chip.textContent || '').trim() : null,
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


# --- the posts' own front matter, the source of the highlight block (#63) ---

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


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


def _marked_highlights():
    """`(date, title, path)` of the posts that opted in, newest first."""
    marked = []
    for path in POSTS_DIR.glob("*.md"):
        front_matter = _front_matter(path)
        if _front_matter_value(front_matter, "published") == "false":
            continue
        if _front_matter_value(front_matter, "highlight") != "true":
            continue
        marked.append(
            (path.name[:10], _front_matter_value(front_matter, "title"), path)
        )
    # Newest first, like `site.posts` (so the same order as the sidebar).
    return sorted(marked, key=lambda post: (post[0], post[2].name), reverse=True)


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
def test_sidebar_highlights_are_opt_in_from_the_post_front_matter():
    html = _read(SIDEBAR_INCLUDE)
    # Enabling a highlight is static, in the post's own `.md` front matter.
    assert 'where: "highlight", true' in html
    assert f"sidebar_highlights limit: {HIGHLIGHT_LIMIT}" in html
    # Nothing marked yet: fall back to the newest posts, and let the heading say
    # which of the two the reader is looking at (never an empty block).
    assert "assign sidebar_highlights = site.posts" in html
    assert "Bài nổi bật" in html
    assert "Bài mới nhất" in html
    # Not the paginator's page: the block must not change while paging.
    markup = re.sub(r"\{%-?\s*comment.*?endcomment\s*-?%\}", "", html, flags=re.S)
    assert "paginator" not in markup


@pytest.mark.static
def test_sidebar_thumbnail_falls_back_to_the_first_body_image():
    html = _read(SIDEBAR_INCLUDE)
    assert "sidebar_post.image" in html
    assert "split: '<img'" in html
    assert """split: 'src="'""" in html
    # No placeholder art and no new image files: a post without an image simply
    # renders without a thumbnail (`assets/img/` runs close to its budget).
    assert "/assets/img/" not in html
    assert not re.search(r"thumb-[a-z0-9-]+\.(jpg|jpeg|png|webp)", html)


@pytest.mark.static
def test_sidebar_tag_block_reuses_the_shared_chip_include():
    html = _read(SIDEBAR_INCLUDE)
    assert "include post-tags.html" in html
    # No forked chip markup: the single source is `_includes/post-tags.html`
    # (#45/#47).
    assert 'class="tag-chip"' not in html
    assert re.search(
        r"'/tags/'\s*\|\s*append: sidebar_tag_name\s*\|\s*append: '/' \| relative_url", html
    )
    # Collapsed by default (#63) and bounded per tag: the tag's own page is one
    # click away (`Xem tất cả`), so the column stays short.
    assert '<details class="sidebar-tag__group">' in html
    assert '<details class="sidebar-tag__group" open>' not in html
    assert f"limit: {TAG_POSTS_LIMIT}" in html


@pytest.mark.static
def test_custom_styles_define_the_sidebar_grid():
    scss = _read(CUSTOM_STYLES)
    assert ".site-layout {" in scss
    # Two columns from 960px, one below it; `minmax(0, 1fr)` instead of a bare
    # `1fr` so a long unbreakable run cannot widen the phone layout (#50).
    assert "grid-template-columns: minmax(0, 1fr) 300px;" in scss
    assert "grid-template-columns: minmax(0, 1fr);" in scss
    assert "grid-template-columns: 1fr;" not in scss
    # The wider wrapper belongs to the list pages' content column only.
    assert ".layout-home main .wrapper," in scss
    assert ".layout-tag main .wrapper {" in scss
    # Pinned only where the sidebar fits beside the list: the desktop breakpoint
    # *and* a viewport tall enough for its bounded content (#63).
    assert (
        f"@media screen and (min-width: 960px) and (min-height: "
        f"{STICKY_VIEWPORT_HEIGHT}px)" in scss
    )
    assert re.search(
        r"@media screen and \(min-width: 960px\) and \(min-height: "
        r"[\d]+px\)\s*\{[^}]*\.site-sidebar\s*\{[^}]*position: sticky",
        scss,
    ), "the site sidebar must be sticky only where it fits beside the list"
    # Post pages keep their own sticky column (#45): pinned from desktop width
    # only, without the viewport-height gate, so post-page behaviour is unchanged.
    assert re.search(
        r"@media screen and \(min-width: 960px\)\s*\{[^}]*\.post-sidebar\s*\{[^}]*position: sticky",
        scss,
    ), "the post sidebar must keep its own sticky rule at min-width: 960px"
    # The thumbnail keeps the source ratio (the #50 guard measures real rects):
    # capped in a box, never cropped and never upscaled.
    assert re.search(
        r"\.sidebar-post__thumb img\s*\{[^}]*max-width: 96px;[^}]*max-height: 60px;", scss
    )
    assert "object-fit" not in scss, "thumbnails are not cropped to a fixed ratio"
    # `_sass/minima/_base.scss` gives every `img` 20px of padding inside its
    # border box, which would distort a two-`max-*` box (see the comment there);
    # the thumbnail resets it.
    assert re.search(r"\.sidebar-post__thumb img\s*\{[^}]*padding: 0;", scss)


@pytest.mark.static
def test_sidebar_height_is_bounded_instead_of_an_inner_scrollbar():
    """#63: the height budget replaces #58's `max-height` + `overflow-y` cap."""
    # Comments mention the removed cap, so only the declarations count.
    scss = re.sub(r"//[^\n]*", "", _read(CUSTOM_STYLES))
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


def test_sidebar_shows_the_same_highlights_on_every_page(
    built_site, built_site_url, browser
):
    """The highlights are the posts that opted in — not simply the newest."""
    marked = _marked_highlights()[:HIGHLIGHT_LIMIT]

    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        sidebar = page.evaluate(_SIDEBAR_JS)

        if marked:
            assert sidebar["highlightsHeading"] == "Bài nổi bật", (
                "with posts marked in their front matter the block is `Bài nổi bật`"
            )
        else:
            # No post opted in yet: the block falls back to the newest posts and
            # says so, instead of rendering an empty box.
            assert sidebar["highlightsHeading"] == "Bài mới nhất"
            marked = [
                (None, title, None)
                for title in page.evaluate(
                    "() => Array.from(document.querySelectorAll('.post-list a.post-link')).map((a) => a.textContent.trim())"
                )[:HIGHLIGHT_LIMIT]
            ]

        assert len(sidebar["highlights"]) == len(marked), (
            f"expected {len(marked)} highlights, got {sidebar['highlights']}"
        )
        assert [entry["title"] for entry in sidebar["highlights"]] == [
            title for _, title, _ in marked
        ], (
            "the sidebar must list exactly the posts marked `highlight: true`, "
            f"newest first: {sidebar['highlights']}"
        )

        for (date, title, path), entry in zip(marked, sidebar["highlights"]):
            assert entry["title"], f"sidebar entry without a title: {entry}"
            if path is not None:
                # `site.posts` order, thumbnail resolution and date all come
                # from the post's own file.
                assert entry["datetime"][:10] == date, (
                    f"{path.name} is dated {date} but the sidebar shows "
                    f"{entry['datetime']}"
                )
            # The compact `dd-mm-yyyy` label renders that same instant, because
            # `site.minima.date_format` ("Bài viết được đăng lúc: …") does not
            # fit a 300px column.
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

        # The same list on every list page: it comes from `site.posts`, not from
        # the paginator's page.
        for path in ("/page2/", TAG_PAGE):
            _open(page, built_site_url, path)
            assert page.evaluate(_SIDEBAR_JS)["highlights"] == sidebar["highlights"], (
                f"{path} shows a different sidebar than the home list"
            )


def test_sidebar_tag_rows_are_collapsed_bounded_and_expandable(
    built_site, built_site_url, browser
):
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        groups = page.evaluate(_SIDEBAR_JS)["tags"]
        assert groups, "the sidebar must render the tag block"

        for index, group in enumerate(groups):
            match = re.fullmatch(r"/tags/([a-z0-9-]+)/", group["tag"] or "")
            assert match, f"unexpected tag chip href: {group['tag']}"
            tag = match.group(1)
            assert group["chipLabel"] == tag, "the chip label is the tag itself"
            assert group["more"] == group["tag"]
            assert group["open"] is False, (
                f"tag `{tag}` must be collapsed by default (#63), so the column "
                "stays short"
            )
            assert 0 < len(group["posts"]) <= TAG_POSTS_LIMIT, (
                f"tag `{tag}` lists an unbounded or empty set: {group['posts']}"
            )

            # The tag's own page is the reference for which posts carry the tag.
            assert (built_site / "tags" / tag / "index.html").is_file(), (
                f"/tags/{tag}/ is missing from the build"
            )
            response = page.request.get(f"{built_site_url}/tags/{tag}/")
            assert response.status == 200, f"/tags/{tag}/ returned {response.status}"

            _open(page, built_site_url, f"/tags/{tag}/")
            expected = page.evaluate(_POST_LIST_JS)
            tag_page_text = page.inner_text(".tag-page__intro")
            total = int(re.search(r"(\d+) bài viết", tag_page_text).group(1))
            assert total == len(expected), (
                f"/tags/{tag}/ says {total} posts but lists {len(expected)}"
            )
            assert [post["url"] for post in group["posts"]] == expected[:TAG_POSTS_LIMIT], (
                f"the sidebar block for `{tag}` must list the tag's newest posts: "
                f"{group['posts']} != {expected[:TAG_POSTS_LIMIT]}"
            )
            assert group["count"] == f"{total} bài", (
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
            # click on the row opens it. The click lands on the count: the chip
            # next to it links to the tag page (asserted above), so the row's own
            # toggle area is the rest of the summary.
            _open(page, built_site_url, "/")
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
                f"opening `{tag}` must offer the link to /tags/{tag}/"
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
