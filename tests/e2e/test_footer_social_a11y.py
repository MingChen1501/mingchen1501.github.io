"""Guards for #146: footer social icon links need stable accessible names.

The social links in `_includes/social.html` used to expose their accessible
name only via the `title` attribute (an icon font glyph / inline SVG with no
text inside the link). `title` is not a reliable accessible name across
screen reader / browser combinations, so every link now carries an
`aria-label` (the feed link label is localized to match the page language),
the icons are hidden from assistive technology, and the visible design is
unchanged.

Since #254 the brand glyphs are inline SVGs instead of the Font Awesome
webfont: no external stylesheet is fetched, and every social link renders a
decorative SVG whose name comes from the link's `aria-label`.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) assert the rendered footer on the EN and VI homes.
"""

from __future__ import annotations

import re
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCIAL_INCLUDE = REPO_ROOT / "_includes" / "social.html"


def _social_list(page_html, url):
    """The rendered `<ul class="social-media-list">` block of a page."""
    match = re.search(
        r'<ul class="social-media-list">.*?</ul>', page_html, re.S
    )
    assert match, f"{url} renders no footer social list"
    return match.group(0)


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_social_links_carry_aria_labels_not_title_only():
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    anchors = re.findall(r"<a\b[^>]*>", html)
    assert anchors, "social.html renders no links to judge"
    for anchor in anchors:
        assert "aria-label=" in anchor, (
            f"social link exposes a title-only accessible name (#146): {anchor}"
        )


@pytest.mark.static
def test_social_icons_are_decorative():
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    assert 'aria-hidden="true"' in html, (
        "social icons must be hidden from assistive technology (#146)"
    )
    assert html.count('aria-hidden="true"') >= 2, (
        "every inline icon (brands + feed) must be decorative (#146)"
    )


@pytest.mark.static
def test_feed_label_matches_the_page_language():
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    assert "Subscribe to syndication feed" in html, (
        "the English feed label must survive (#146)"
    )
    assert "page.lang" in html, (
        "social.html must pick the feed label by page language (#146)"
    )


@pytest.mark.static
def test_social_icons_are_inline_svg_not_an_icon_font():
    """#254 retired the Font Awesome webfont: every brand link renders a
    decorative inline SVG (currentColor via `.svg-icon`), and no `fa-*`
    class may come back."""
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    assert "fa-brands" not in html and "fa-lg" not in html, (
        "social.html still uses Font Awesome icon-font classes (#254)"
    )
    assert "fontawesome" not in html.lower(), (
        "social.html still references Font Awesome (#254)"
    )
    assert "https://cdn.jsdelivr.net" not in html, (
        "social.html still fetches the retired CDN origin (#254)"
    )
    svgs = re.findall(r"<svg\b[^>]*>", html)
    # Five brand glyphs plus the feed icon.
    assert len(svgs) >= 6, (
        f"social.html must inline one SVG per icon (5 brands + feed), "
        f"found {len(svgs)} (#254)"
    )
    for svg in svgs:
        assert 'aria-hidden="true"' in svg, (
            f"inline social SVG must stay decorative (#146): {svg}"
        )
        assert "viewBox" in svg or "viewbox" in svg, (
            f"inline social SVG must scale with its viewBox (#254): {svg}"
        )


@pytest.mark.static
def test_focus_stays_visible_on_social_links():
    """#87's focus rule covers links, so the icon links never go dark."""
    assert "a:focus-visible" in conftest.custom_styles_text()


# --- build guards (need Ruby; no browser) -----------------------------------


def _assert_named_links(page_html, url, feed_label):
    social = _social_list(page_html, url)
    anchors = re.findall(r"<a\b[^>]*>", social)
    assert anchors, f"{url} footer social list holds no links"
    for anchor in anchors:
        label = re.search(r'aria-label="([^"]+)"', anchor)
        assert label and label.group(1).strip(), (
            f"{url} footer social link relies on a title-only "
            f"accessible name (#146): {anchor}"
        )
    assert f'aria-label="{feed_label}"' in social, (
        f"{url} footer feed link must be labelled {feed_label!r} (#146)"
    )
    # Icons stay decorative in the build (brand SVGs + feed SVG).
    assert social.count('aria-hidden="true"') >= 2, (
        f"{url} footer social icons must be decorative (#146)"
    )
    # #254: every social link renders its own inline SVG — no icon font.
    assert "fa-brands" not in social and "fa-lg" not in social, (
        f"{url} footer still uses Font Awesome icon-font classes (#254)"
    )
    assert "cdn.jsdelivr.net" not in page_html, (
        f"{url} still fetches the retired Font Awesome CDN origin (#254)"
    )
    bodies = re.findall(r"<a\b[^>]*>(.*?)</a>", social, re.S)
    assert bodies and all("<svg" in body for body in bodies), (
        f"{url} every footer social link must inline its icon SVG (#254)"
    )


def test_footer_social_links_have_accessible_names(built_site):
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    _assert_named_links(en_home, "/", "Subscribe to syndication feed")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    _assert_named_links(vi_home, "/vi/", "Đăng ký nhận tin RSS")
