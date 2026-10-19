"""Pagination discoverability guards (#89).

The English home (`/`, paginated by jekyll-paginate) must expose visible
pagination controls inside a semantic ``<nav aria-label="Pagination">``
landmark with ``rel="prev"`` / ``rel="next"`` links, and both paginated
pages must carry the matching ``<link rel="next|prev">`` head tags (emitted
by jekyll-seo-tag) so crawlers get the prev/next signal. The Vietnamese
home (`/vi/`) lists every post with no paginator, so it must stay pager-free.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _nav_block(html):
    match = re.search(
        r'<nav class="pager" aria-label="Pagination">(.*?)</nav>', html, re.S
    )
    assert match is not None, "page must render <nav class=\"pager\" aria-label=\"Pagination\">"
    return match.group(1)


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


def test_vietnamese_home_stays_pager_free(built_site):
    """`/vi/` lists every post with no paginator and no pager (#89, #93)."""
    html = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Pagination"' not in html
    assert 'class="pager"' not in html
