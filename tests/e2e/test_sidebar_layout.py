"""Guards for the list-page sidebar (#58): the home list and the tag pages.

Both layouts (`_layouts/home.html`, `_layouts/tag.html`) wrap their list in the
same two-column shell — `.site-layout` > `.site-main` + `aside.site-sidebar` —
fed by one shared include, `_includes/site-sidebar.html`, whose two blocks are

1. the three most recent posts of the whole site (thumbnail when the post has
   one, short description), and
2. every tag with its posts (`<details>` expanded by default, at most five
   posts each, plus a link to the tag's own page).

Acceptance guarded here (issue #58):

- the shell exists in both layouts with the sidebar *after* the list in the DOM
  (the #47 chips must stay the first `a.tag-chip` in the document, and below
  960px the single column then stacks the sidebar under the list by itself),
- exactly three recent posts, the same three while paging (they come from
  `site.posts`, not `paginator.posts`),
- the tag block lists only real posts of that tag, and
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

RECENT_POSTS = 3
TAG_POSTS_LIMIT = 5

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280
SIDEBAR_WIDTH = 300

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
    main: main ? rect(main) : null,
    aside: aside ? rect(aside) : null,
    asidePosition: aside ? getComputedStyle(aside).position : null,
    images: images,
  };
}
"""

# The sidebar's own content: the three recent posts and every tag group.
_SIDEBAR_JS = """
() => ({
  recent: Array.from(document.querySelectorAll('.sidebar-posts > .sidebar-post')).map((li) => {
    const title = li.querySelector('a.sidebar-post__title');
    const thumb = li.querySelector('.sidebar-post__thumb img');
    return {
      title: title ? (title.textContent || '').trim() : null,
      url: title ? title.getAttribute('href') : null,
      thumb: thumb ? thumb.getAttribute('src') : null,
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
})
"""

# Hrefs of the main post list — on a tag page that is the tag's own list.
_POST_LIST_JS = """
() => Array.from(
  document.querySelectorAll('.post-list a.post-link')
).map((a) => a.getAttribute('href'))
"""


def _read(path):
    return path.read_text(encoding="utf-8")


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
def test_sidebar_lists_the_three_most_recent_posts_of_the_site():
    html = _read(SIDEBAR_INCLUDE)
    assert f"site.posts limit: {RECENT_POSTS}" in html
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
    # Expanded by default (decision D2) and bounded per tag.
    assert '<details class="sidebar-tag__group" open>' in html
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
    # Sticky only from the desktop breakpoint, where the sidebar is beside the
    # list.
    assert re.search(
        r"\.post-sidebar,\s*\.site-sidebar\s*\{[^}]*min-width: 960px\)\s*\{[^}]*position: sticky",
        scss,
    ), "the site sidebar must be sticky only inside the >=960px media query"
    # The thumbnail keeps the source ratio (the #50 guard measures real rects).
    assert re.search(
        r"\.sidebar-post__thumb img\s*\{[^}]*width: 100%;[^}]*height: auto;", scss
    )


@pytest.mark.static
def test_post_page_and_comments_are_untouched_by_the_sidebar():
    """The list sidebar must not leak into the post page (#45 has its own)."""
    html = _read(POST_LAYOUT)
    assert 'class="post-layout"' in html
    assert 'class="post-sidebar"' in html
    assert "site-sidebar.html" not in html
    assert "site-sidebar" not in _read(REPO_ROOT / "_includes" / "comments.html")


# --- browser guards (need Ruby + a browser) ---------------------------------


def test_sidebar_shows_the_same_three_latest_posts_on_every_page(
    built_site, built_site_url, browser
):
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        sidebar = page.evaluate(_SIDEBAR_JS)
        newest = page.evaluate(_POST_LIST_JS)[:RECENT_POSTS]

        assert len(sidebar["recent"]) == RECENT_POSTS, (
            "the sidebar must list exactly "
            f"{RECENT_POSTS} recent posts, got {sidebar['recent']}"
        )
        assert [post["url"] for post in sidebar["recent"]] == newest, (
            "the sidebar must list the site's newest posts in order: "
            f"{sidebar['recent']} != {newest}"
        )
        for post in sidebar["recent"]:
            assert post["title"], f"sidebar entry without a title: {post}"
            built = built_site / post["url"].lstrip("/")
            assert built.is_file(), f"sidebar post {post['url']} is not in the build"
            response = page.request.get(f"{built_site_url}{post['url']}")
            assert response.status == 200, f"{post['url']} returned {response.status}"

        # Page 2 serves a different list from the same sidebar.
        _open(page, built_site_url, "/page2/")
        second_page = page.evaluate(_SIDEBAR_JS)
        assert second_page["recent"] == sidebar["recent"], (
            "the sidebar comes from `site.posts`, so it must not change while paging"
        )


def test_sidebar_tag_block_lists_only_real_posts_of_that_tag(
    built_site, built_site_url, browser
):
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        groups = page.evaluate(_SIDEBAR_JS)["tags"]
        assert groups, "the sidebar must render the tag block"

        for group in groups:
            match = re.fullmatch(r"/tags/([a-z0-9-]+)/", group["tag"] or "")
            assert match, f"unexpected tag chip href: {group['tag']}"
            tag = match.group(1)
            assert group["chipLabel"] == tag, "the chip label is the tag itself"
            assert group["more"] == group["tag"]
            assert group["open"], f"tag `{tag}` must be expanded by default (D2)"
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

            _open(page, built_site_url, "/")


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
        # lazy image really decoded while we measured.
        for image in sidebar_images:
            assert image["naturalWidth"], (
                f"{path}: the sidebar thumbnail {image['src']} never decoded, so it "
                "was not measured"
            )
