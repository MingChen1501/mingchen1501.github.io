"""Bilingual 404 guard (#281).

The failure page is a reader surface like any other: a single static
`404.html` (kept on `layout: base` so the header, footer, theme toggle and
theme bootstrap stay) shows English and Vietnamese guidance inline — one
static file serves both languages, no JS redirect and no meta refresh
(#154 stays Cloudflare-only) — and links back to `/`, `/vi/`, `/search/`,
`/vi/tim-kiem/`, `/tags/` and `/vi/tags/`, plus the newest post per
language (#335). It reuses the site stylesheet (the minima
`post`/`post-header`/`post-title`/`post-content` classes), so dark mode
follows `html[data-theme]` with no page-specific `<style>` and no
third-party request.

Guarded here:

- static (no Ruby, no browser): the source keeps `layout: base`, carries
  both languages' copy with `lang` attributes, links the five destinations
  through `relative_url`, and ships no `<style>`, no inline `style=`, no
  script and no remote URL;
- build (needs Ruby): the built `404.html` serves with status 200, keeps
  the EN+VI guidance and the five links (each resolving to a built file),
  carries the site stylesheet plus the theme bootstrap ahead of it, and
  references no third-party origin;
- browser (needs Ruby + a browser): no horizontal scroll at 375px and
  1280px, the dark colour scheme paints the dark theme, the skip link
  takes keyboard focus, and the vendored axe scanner reports no
  serious/critical violations.
"""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NOT_FOUND = REPO_ROOT / "404.html"
AXE_JS = REPO_ROOT / "tests" / "e2e" / "axe-core" / "axe.min.js"
SITE_URL = "https://mingchen.id.vn"

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280
VIEWPORT_HEIGHT = 800

# Every destination the lost reader is offered, as rendered in the build
# (`baseurl` is empty, so `relative_url` emits these verbatim).
EXPECTED_LINKS = ("/", "/vi/", "/search/", "/vi/tim-kiem/", "/tags/", "/vi/tags/")


def _read(path):
    return path.read_text(encoding="utf-8")


def _built_404(built_site):
    page = built_site / "404.html"
    assert page.is_file(), "the build emits no 404.html"
    return _read(page)


def _file_for(site_dir, url_path):
    """Map a site path onto the file that serves it (GitHub Pages rules)."""
    if url_path in ("", "/"):
        return site_dir / "index.html"
    clean = url_path.lstrip("/")
    if clean.endswith("/"):
        return site_dir / clean / "index.html"
    return site_dir / clean


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_404_keeps_base_layout_with_a_title():
    block = re.match(r"\A---\s*\n(.*?)\n---\s*\n", _read(NOT_FOUND), re.S)
    assert block, "404.html has no front matter"
    front_matter = block.group(1)
    assert re.search(r"^layout:\s*base\s*$", front_matter, re.M), (
        "404.html must keep `layout: base` (header/footer/theme stay, #281)"
    )
    assert re.search(r"^title:\s*.+\S", front_matter, re.M), (
        "404.html needs a title for the document head"
    )


@pytest.mark.static
def test_404_source_has_no_inline_style_script_or_refresh():
    source = _read(NOT_FOUND)
    assert "<style" not in source.lower(), (
        "404.html must reuse the site stylesheet, not a page `<style>`"
    )
    assert "style=" not in source.lower(), (
        "404.html must not carry inline `style=` attributes"
    )
    assert "<script" not in source.lower(), (
        "404.html must not add scripts (no JS redirect, #154)"
    )
    assert "http-equiv" not in source.lower(), (
        "404.html must not use a meta refresh redirect (#154)"
    )


@pytest.mark.static
def test_404_source_carries_bilingual_copy():
    source = _read(NOT_FOUND)
    for snippet in ("Page not found", "does not exist or has moved"):
        assert snippet in source, f"404.html is missing the English copy: {snippet!r}"
    for snippet in ("Không tìm thấy trang", "không tồn tại hoặc đã được di chuyển"):
        assert snippet in source, f"404.html is missing the Vietnamese copy: {snippet!r}"
    assert 'lang="vi"' in source, (
        "the Vietnamese copy needs a `lang` attribute on its element"
    )


@pytest.mark.static
def test_404_source_links_home_search_and_tags_in_both_languages():
    source = _read(NOT_FOUND)
    for target in EXPECTED_LINKS:
        assert f"'{target}' | relative_url" in source, (
            f"404.html must link {target} through `relative_url`"
        )


@pytest.mark.static
def test_404_source_suggests_the_newest_post_per_language():
    """#335: beyond the fixed doors, each language names its newest post
    (looked up at build time, so the suggestion never goes stale)."""
    source = _read(NOT_FOUND)
    for snippet in ("Latest post:", "Bài mới nhất:"):
        assert snippet in source, f"404.html misses the newest-post copy: {snippet!r}"
    assert "site.posts.first" in source, (
        "404.html must look up the newest English post at build time"
    )
    assert "site.vi_posts" in source and "== nil" in source, (
        "404.html must look up the newest Vietnamese post with the "
        "upstream theme-dev nil-guard"
    )


@pytest.mark.static
def test_404_source_references_no_remote_origin():
    source = _read(NOT_FOUND)
    assert "http://" not in source and "https://" not in source, (
        "404.html must reference no remote URL (zero third-party requests)"
    )
    assert "//" not in re.sub(r"{{.*?}}", "", source).replace("://", ""), (
        "404.html must not use protocol-relative URLs"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def test_built_404_serves_bilingual_guidance(built_site):
    html = _built_404(built_site)
    for snippet in ("Page not found", "does not exist or has moved"):
        assert snippet in html, f"built 404.html is missing English guidance: {snippet!r}"
    for snippet in ("Không tìm thấy trang", "không tồn tại hoặc đã được di chuyển"):
        assert snippet in html, f"built 404.html is missing Vietnamese guidance: {snippet!r}"
    assert re.search(r"<h1[^>]*>404</h1>", html), (
        "built 404.html keeps no prominent 404 heading"
    )
    assert 'lang="vi"' in html, (
        "built 404.html marks no Vietnamese region with `lang`"
    )


def test_built_404_links_every_destination_and_each_resolves(built_site):
    html = _built_404(built_site)
    for target in EXPECTED_LINKS:
        assert f'href="{target}"' in html, (
            f"built 404.html links nowhere to {target}"
        )
        assert _file_for(built_site, target).is_file(), (
            f"built 404.html links {target}, which is not in the build"
        )


def test_built_404_section_suggestions_all_resolve(built_site):
    """#335: every suggestion inside the EN/VI sections resolves — the
    site-wide link crawl never visits 404.html (documented orphan), so
    the per-language doors (including the build-time newest posts) are
    resolved here instead."""
    html = _built_404(built_site)
    sections = re.findall(r'<section lang="(?:en|vi)".*?</section>', html, re.S)
    assert len(sections) == 2, "built 404.html must keep one section per language"
    checked = 0
    for section in sections:
        for href in re.findall(r'href="([^"]+)"', section):
            if href.startswith(("http", "mailto:")):
                continue
            assert _file_for(built_site, href).is_file(), (
                f"built 404.html links {href}, which is not in the build"
            )
            checked += 1
    assert checked >= 8, (
        f"built 404.html offers only {checked} section links, expected 4 per language"
    )


def test_built_404_inherits_the_theme_stylesheet_without_inline_style(
    built_site,
):
    """The page paints like every other page: site stylesheet, theme
    bootstrap ahead of it, no page-specific style block (#220, #281)."""
    html = _built_404(built_site)
    assert "<style" not in html.lower(), (
        "built 404.html must not contain a `<style>` block"
    )
    assert "style=" not in html.lower(), (
        "built 404.html must not contain inline `style=` attributes"
    )
    stylesheet = html.find('id="main-stylesheet"')
    assert stylesheet != -1, "built 404.html links no site stylesheet"
    bootstrap = html.find("localStorage.getItem")
    assert bootstrap != -1, "built 404.html misses the theme bootstrap"
    assert bootstrap < stylesheet, (
        "built 404.html paints the stylesheet before the theme bootstrap"
    )
    assert "data-theme" in html, (
        "built 404.html must inherit the `html[data-theme]` theme hook"
    )


def test_built_404_makes_no_third_party_request(built_site):
    """Only the site origin is ever fetched: scripts, stylesheets, images
    and hinted origins stay local. Plain outbound anchors (footer social
    links, `mailto:`) are links, not requests, and are out of scope."""
    html = _built_404(built_site)
    fetched = re.findall(
        r"""<(?:script|img|link|source|video|audio|object)[^>]*?"""
        r"""(?:src|href)=["']([^"']+)["']""",
        html,
    )
    assert fetched, "built 404.html fetches nothing at all"
    for url in fetched:
        if url.startswith(("http://", "https://")):
            assert url.startswith(SITE_URL), (
                f"built 404.html fetches a third-party origin: {url}"
            )
    assert 'rel="preconnect"' not in html and 'rel="dns-prefetch"' not in html, (
        "built 404.html must not hint any remote origin"
    )


# --- browser guards (need Ruby + a browser) ---------------------------------


@contextlib.contextmanager
def _open_404(browser, site_url, width, scheme="light"):
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        color_scheme=scheme,
    )
    try:
        page = context.new_page()
        origin = urlparse(site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        response = page.goto(f"{site_url}/404.html", wait_until="load")
        assert response is not None and response.status == 200, (
            f"/404.html did not load (status {response.status if response else 'none'})"
        )
        page.wait_for_selector(".post-title", state="visible", timeout=10_000)
        yield page
    finally:
        context.close()


@pytest.mark.parametrize("width", (PHONE_WIDTH, DESKTOP_WIDTH))
def test_404_has_no_horizontal_scroll(width, built_site_url, browser):
    """The failure page fits phone and desktop viewports alike."""
    with _open_404(browser, built_site_url, width) as page:
        overflow = page.evaluate(
            "() => ({scroll: document.documentElement.scrollWidth, "
            "inner: window.innerWidth})"
        )
        assert overflow["scroll"] <= overflow["inner"], (
            f"/404.html scrolls sideways at {width}px "
            f"(scrollWidth {overflow['scroll']} > {overflow['inner']})"
        )


def test_404_dark_scheme_paints_the_dark_theme(built_site_url, browser):
    """With a dark OS preference and no stored choice, the bootstrap pins
    `data-theme="dark"` and the page paints dark (#220)."""
    with _open_404(browser, built_site_url, DESKTOP_WIDTH, scheme="dark") as page:
        theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        assert theme == "dark", (
            f"/404.html data-theme is {theme!r} under a dark scheme, expected 'dark'"
        )
        background = page.evaluate(
            "() => getComputedStyle(document.body).backgroundColor"
        )
        match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", background)
        assert match, f"cannot parse body background {background!r}"
        channels = [int(match.group(i)) / 255 for i in (1, 2, 3)]
        linearized = [
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        luminance = 0.2126 * linearized[0] + 0.7152 * linearized[1] + 0.0722 * linearized[2]
        assert luminance < 0.25, (
            f"/404.html body paints {background} in dark mode (not dark)"
        )


def test_404_skip_link_takes_keyboard_focus(built_site_url, browser):
    """First Tab lands on the skip link and reveals it (#87)."""
    with _open_404(browser, built_site_url, DESKTOP_WIDTH) as page:
        page.keyboard.press("Tab")
        focused = page.evaluate(
            "() => document.activeElement.className"
        )
        assert "skip-link" in focused, (
            f"first Tab on /404.html focuses {focused!r}, not the skip link"
        )
        box = page.evaluate(
            "() => { const r = document.activeElement.getBoundingClientRect();"
            " return {x: r.x, y: r.y, w: r.width, h: r.height}; }"
        )
        assert box["w"] > 0 and box["h"] > 0, (
            "the 404 skip link takes focus but stays invisible"
        )


@pytest.mark.parametrize("width", (PHONE_WIDTH, DESKTOP_WIDTH))
def test_404_has_no_serious_axe_violations(
    width, built_site_url, browser
):
    """Vendored axe scan over the failure page: no serious/critical (#207)."""
    with _open_404(browser, built_site_url, width) as page:
        page.add_script_tag(path=str(AXE_JS))
        page.wait_for_function("() => !!window.axe", timeout=15_000)
        violations = page.evaluate(
            "() => window.axe.run(document, {resultTypes: ['violations']})"
            ".then((results) => results.violations.map((v) => ({"
            "  id: v.id,"
            "  impact: v.impact,"
            "  nodes: v.nodes.map((n) => n.target.join(' ')),"
            "})))"
        )
        blocking = [v for v in violations if v["impact"] in ("serious", "critical")]
        assert not blocking, (
            f"/404.html axe violations at {width}px: {blocking}"
        )
