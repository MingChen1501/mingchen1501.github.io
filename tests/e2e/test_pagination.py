"""Pagination discoverability guards (#89, #155).

The English home (`/`, paginated by jekyll-paginate) must expose visible
pagination controls inside a semantic ``<nav aria-label="Pagination">``
landmark with ``rel="prev"`` / ``rel="next"`` links, and both paginated
pages must carry the matching ``<link rel="next|prev">`` head tags (emitted
by jekyll-seo-tag) so crawlers get the prev/next signal.

The Vietnamese home (`/vi/`, `vi/page2/`, ...) is paginated by hand
(Pages-safe: Liquid ``slice`` + explicit ``vi/pageN/index.html`` files with
``vi_page_num`` front matter, ``site.paginate`` posts per page (#176) —
jekyll-paginate supports a single stream). It reuses the same pager
markup/classes with localized labels ("Bài mới hơn" / "Bài cũ hơn") and
explicit head prev/next links (emitted in `_includes/head.html`, since
jekyll-seo-tag only knows the English paginator stream).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

VI_PER_PAGE = 5


def _nav_block(html):
    match = re.search(
        r'<nav class="pager" aria-label="Pagination">(.*?)</nav>', html, re.S
    )
    assert match is not None, "page must render <nav class=\"pager\" aria-label=\"Pagination\">"
    return match.group(1)


def _post_links(html):
    return re.findall(r'class="post-link" href="([^"]+)"', html)


def _published_vi_posts():
    return sorted(
        p for p in (REPO_ROOT / "_vi_posts").glob("*.md")
        if "published: false" not in p.read_text(encoding="utf-8")
    )


def _generated_vi_pages():
    """Explicit ``vi/pageN/index.html`` source files (page 1 is ``vi/index.html``)."""
    return sorted((REPO_ROOT / "vi").glob("page*/index.html"))


def test_home_pager_is_a_labelled_nav_with_rel_links(built_site):
    """`/` renders visible Older/Newer controls with rel prev/next (#89)."""
    html = (built_site / "index.html").read_text(encoding="utf-8")
    nav = _nav_block(html)
    assert "Older posts" in nav, "the pager must show a visible 'Older posts' control"
    next_link = re.search(r'<a[^>]*rel="next"[^>]*>', nav)
    assert next_link is not None, "the next-page control must carry rel=\"next\""
    assert 'href="/page2/"' in next_link.group(0)
    assert 'rel="prev"' not in nav, "page 1 has no previous page to link"


def test_home_head_carries_rel_next(built_site):
    """`/` advertises the next paginated page in `<head>` (#89)."""
    html = (built_site / "index.html").read_text(encoding="utf-8")
    head = html.split("</head>")[0]
    assert re.search(r'<link[^>]*rel="next"[^>]*href="[^"]*\/page2\/"', head), (
        "`/` must carry <link rel=\"next\"> to /page2/ in <head>"
    )


def test_page2_pager_links_back_with_rel_prev(built_site):
    """`/page2/` links back via rel=prev in both the nav and `<head>` (#89)."""
    html = (built_site / "page2" / "index.html").read_text(encoding="utf-8")
    nav = _nav_block(html)
    assert "Newer posts" in nav, "the pager must show a visible 'Newer posts' control"
    prev_link = re.search(r'<a[^>]*rel="prev"[^>]*>', nav)
    assert prev_link is not None, "the previous-page control must carry rel=\"prev\""
    assert 'rel="next"' not in nav, "the last page has no next page to link"
    head = html.split("</head>")[0]
    assert re.search(r'<link[^>]*rel="prev"', head), (
        "`/page2/` must carry <link rel=\"prev\"> in <head>"
    )


def test_vietnamese_home_shows_newest_five_with_localized_pager(built_site):
    """`/vi/` shows the 5 newest VI posts with a localized pager to `/vi/page2/` (#155)."""
    html = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    nav = _nav_block(html)
    links = _post_links(html)
    assert len(links) == VI_PER_PAGE, (
        f"`/vi/` must show exactly {VI_PER_PAGE} posts, found {len(links)}"
    )
    assert "Bài cũ hơn" in nav, "the VI pager must show a visible 'Bài cũ hơn' control"
    assert "Older posts" not in nav, "the VI pager must not use the English label"
    next_link = re.search(r'<a[^>]*rel="next"[^>]*>', nav)
    assert next_link is not None, "the VI next-page control must carry rel=\"next\""
    assert 'href="/vi/page2/"' in next_link.group(0)
    assert 'rel="prev"' not in nav, "VI page 1 has no previous page to link"
    assert 'class="previous-page"' not in nav, "VI page 1 has no newer-posts link"
    assert '<div class="current-page">1</div>' in nav


def test_vietnamese_home_lists_newest_first(built_site):
    """`/vi/` starts with the newest VI post (same order as the feed) (#155)."""
    html = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    links = _post_links(html)
    assert links, "`/vi/` lists no posts"
    assert links[0].startswith("/vi/"), f"VI home lists a non-VI post: {links[0]}"


def test_vietnamese_page2_shows_remainder_with_newer_link_back(built_site):
    """`/vi/page2/` shows the remaining VI posts with a localized link back (#155)."""
    page1 = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    page1_links = _post_links(page1)
    html = (built_site / "vi" / "page2" / "index.html").read_text(encoding="utf-8")
    nav = _nav_block(html)
    links = _post_links(html)
    assert links, "`/vi/page2/` must exist and list the remaining posts"
    assert not (set(links) & set(page1_links)), (
        f"`/vi/page2/` duplicates posts from `/vi/`: {set(links) & set(page1_links)}"
    )
    for link in links:
        assert link.startswith("/vi/"), f"`/vi/page2/` lists a non-VI post: {link}"
    assert "Bài mới hơn" in nav, "the VI pager must show a visible 'Bài mới hơn' control"
    assert "Newer posts" not in nav, "the VI pager must not use the English label"
    prev_link = re.search(r'<a[^>]*rel="prev"[^>]*>', nav)
    assert prev_link is not None, "the VI previous-page control must carry rel=\"prev\""
    assert 'href="/vi/"' in prev_link.group(0)
    assert 'rel="next"' not in nav, "the last VI page has no next page to link"
    assert '<div class="current-page">2</div>' in nav


def test_vietnamese_pagination_covers_every_post_exactly_once(built_site):
    """Every published VI post appears on exactly one paginated VI page (#155)."""
    import xml.etree.ElementTree as ET

    shown = []
    for name in ("index.html", "page2/index.html"):
        html = (built_site / "vi" / name).read_text(encoding="utf-8")
        shown.extend(_post_links(html))
    assert len(shown) == len(set(shown)), f"a VI post appears twice: {shown}"

    feed = ET.fromstring((built_site / "vi" / "feed.xml").read_text(encoding="utf-8"))
    ns = "{http://www.w3.org/2005/Atom}"
    feed_hrefs = {
        entry.find(f"{ns}link").attrib["href"] for entry in feed.findall(f"{ns}entry")
    }
    site_url = "https://mingchen.id.vn"
    shown_absolute = {
        href if href.startswith("http") else f"{site_url}{href}" for href in shown
    }
    assert shown_absolute == feed_hrefs, (
        "the paginated VI pages must cover exactly the published VI posts"
    )


def test_vietnamese_head_carries_prev_next(built_site):
    """`/vi/` and `/vi/page2/` advertise each other via head prev/next (#155)."""
    page1_head = (built_site / "vi" / "index.html").read_text(encoding="utf-8").split("</head>")[0]
    assert re.search(r'<link[^>]*rel="next"[^>]*href="[^"]*/vi/page2/"', page1_head), (
        "`/vi/` must carry <link rel=\"next\"> to /vi/page2/ in <head>"
    )
    assert not re.search(r'<link[^>]*rel="prev"', page1_head), (
        "`/vi/` must not carry <link rel=\"prev\"> in <head>"
    )
    page2_head = (built_site / "vi" / "page2" / "index.html").read_text(encoding="utf-8").split("</head>")[0]
    assert re.search(r'<link[^>]*rel="prev"[^>]*href="[^"]*/vi/"', page2_head), (
        "`/vi/page2/` must carry <link rel=\"prev\"> to /vi/ in <head>"
    )


def test_vietnamese_pager_hidden_when_collection_fits_on_one_page():
    """No pager markup renders when the VI collection fits on one page (#155).

    Static guard over the layout source: the unified pager block renders
    only when its ``pager_show`` flag is set, which the VI branch sets
    exactly when the page count derived from ``site.paginate`` exceeds 1
    (same single-page behavior as EN).
    """
    layout = (REPO_ROOT / "_layouts" / "home.html").read_text(encoding="utf-8")
    assert "vi_total_pages" in layout, "the VI pager must be gated on a page count"
    assert re.search(
        r"vi_total_pages\s*>\s*1",
        layout,
    ), "the VI pager must render only when the collection spans 2+ pages"
    assert re.search(
        r"if\s+pager_show.{0,3000}class=\"pager\"",
        layout,
        re.S,
    ), "the unified pager must render only when its show flag is set"


@pytest.mark.static
def test_per_page_count_has_a_single_source():
    """The per-page count lives only in ``paginate:`` (#176).

    ``_layouts/home.html`` (VI slice + unified pager) and
    ``_includes/head.html`` (VI head prev/next) must derive the count from
    ``site.paginate``; a bare ``= 5`` per-page assignment in either file
    would silently desync VI/EN pagination and head metadata again. The
    only allowed literal is the ``default: 5`` fallback for configs
    without ``paginate:`` (e.g. upstream theme-dev).
    """
    config = (REPO_ROOT / "_config.yml").read_text(encoding="utf-8")
    assert re.search(r"^paginate:\s*\d+\s*$", config, re.M), (
        "`_config.yml` must keep `paginate:` as the single source of truth"
    )
    for template in ("_layouts/home.html", "_includes/head.html"):
        source = (REPO_ROOT / template).read_text(encoding="utf-8")
        assert "site.paginate" in source, (
            f"`{template}` must derive the per-page count from `site.paginate`"
        )
        for match in re.finditer(r"=\s*5\b", source):
            window = source[max(0, match.start() - 20):match.start()]
            assert re.search(r"default:\s*$", window), (
                f"`{template}` reintroduces a hard-coded per-page count: "
                f"...{window}{match.group(0)}... (only `default: 5` is allowed)"
            )
    layout = (REPO_ROOT / "_layouts" / "home.html").read_text(encoding="utf-8")
    assert layout.count('<nav class="pager"') == 1, (
        "the home layout must keep a single parameterized pager block (#176)"
    )


@pytest.mark.static
def test_vietnamese_pagination_capacity_covers_collection():
    """The generated ``vi/pageN`` files must fit every VI post (#155).

    Explicit page files are static: adding an 11th VI post needs a
    ``vi/page3/index.html`` (copy ``vi/page2/index.html`` with
    ``vi_page_num: 3``). This fails first, naming the file to add, so no VI
    post can silently disappear off all paginated pages.
    """
    vi_posts = _published_vi_posts()
    generated = _generated_vi_pages()
    # Page 1 (`vi/index.html`) always exists; each extra `vi/pageN` file adds
    # another full page of capacity.
    capacity = VI_PER_PAGE * (1 + len(generated))
    assert len(vi_posts) <= capacity, (
        f"{len(vi_posts)} published VI posts exceed the {capacity}-post capacity "
        f"of {1 + len(generated)} generated VI page(s); copy "
        f"vi/page{2 + len(generated)}/index.html from vi/page2/index.html "
        f"with `vi_page_num: {2 + len(generated)}`"
    )
