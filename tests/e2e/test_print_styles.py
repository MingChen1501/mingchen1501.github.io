"""Guards for #225: print stylesheet for clean article printing.

The site had no `@media print` rules, so printing (or save-to-PDF) a post
dumped the header nav, sidebar, Related posts, share row, comments and footer
around the article. `_sass/minima/custom/_print.scss` trims print output to
the article column only, in both languages (all selectors are
language-neutral; there are deliberately no per-language rules).

Guarded here:

- the partial exists, is imported exactly once and last (so it wins the
  cascade), and carries no rules outside the single `@media print` block —
  screen rendering stays byte-identical (the Chromium visual baselines in
  `test_visual_regression.py` capture screen media only) (static);
- the block hides every chrome selector (header/nav, sidebars, TOC mounts,
  share row, Related posts, comments, footer, reading progress, back-to-top,
  lightbox, skip link), expands the article column, keeps readable print
  typography, appends destination URLs to outbound links, avoids page breaks
  inside headings/images/code and bounds images (static);
- the print partial introduces none of the tokens the #148 legibility guard
  forbids past its marker (`overflow-y`, `max-height`, `100vh`,
  `position: sticky`) (static);
- the built `assets/css/style.css` ships the print block with the chrome
  hidden (build);
- under Chromium print-media emulation the chrome computes to `display: none`
  while the article stays visible, code/images refuse breaks inside, and an
  outbound link exposes its URL through `::after` — on one EN and one VI post
  each (browser).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

import conftest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRINT_PARTIAL = REPO_ROOT / "_sass" / "minima" / "custom" / "_print.scss"

# Canonical EN/VI post pair (shared with the visual baselines): rich in
# images, rendered in both languages.
EN_POST_PATH = "/2022/10/27/brewing-vietnamese-coffee.html"
VI_POST_PATH = "/vi/2022/10/27/cach-pha-ca-phe.html"

# EN/VI pair carrying outbound (`http`) links in the article body, for the
# link-URL browser guard below.
EN_LINK_POST_PATH = "/2026/01/01/switching-from-windows-11-to-fedora.html"
VI_LINK_POST_PATH = "/vi/2026/01/01/migrate-windows-11-to-fedora.html"

# Every chrome selector the print block must hide.
HIDDEN_SELECTORS = (
    ".site-header",
    ".site-nav",
    ".post-sidebar",
    ".site-sidebar",
    ".post-toc-mount",
    ".post-toc",
    ".share",
    ".related-posts",
    ".comments",
    ".comments-disabled-message",
    ".site-footer",
    ".reading-progress",
    ".back-to-top",
    ".lightbox",
    ".skip-link",
)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _print_scss():
    return _read(PRINT_PARTIAL)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_print_partial_is_imported_once_and_last():
    """The index imports the print partial exactly once, after all screens."""
    assert PRINT_PARTIAL.is_file(), (
        f"{PRINT_PARTIAL.relative_to(REPO_ROOT)} is missing"
    )
    index = _read(conftest.CUSTOM_SCSS_INDEX)
    assert index.count("minima/custom/print") == 1, (
        "the index must import the print partial exactly once"
    )
    names = []
    for block in re.finditer(r"@import\s+(.*?);", index, re.S):
        for item in block.group(1).split(","):
            name = item.strip().strip("\"'")
            if name.startswith("minima/custom/"):
                names.append(name[len("minima/custom/"):])
    assert names[-1] == "print", (
        "the print partial must come last so it wins the cascade"
    )


@pytest.mark.static
def test_no_rules_live_outside_the_print_media_block():
    """Screen safety: nothing in the partial applies to screen media."""
    scss = _print_scss()
    head, sep, _ = scss.partition("@media print")
    assert sep, "the partial must hold a single `@media print` block"
    code_before = "\n".join(
        line for line in head.splitlines()
        if line.strip() and not line.strip().startswith("//")
    )
    assert "{" not in code_before, (
        "no rule may precede `@media print`: the partial must not change "
        "screen rendering"
    )
    assert "@media screen" not in scss, (
        "the partial must not add screen-media rules"
    )


@pytest.mark.static
def test_the_print_block_hides_every_chrome_selector():
    """Nav, sidebars, TOC, share, related, comments, footer stay off paper."""
    scss = _print_scss()
    assert "display: none" in scss, (
        "the print block must hide the page chrome with `display: none`"
    )
    for selector in HIDDEN_SELECTORS:
        assert selector in scss, (
            f"the print block never hides `{selector}`"
        )


@pytest.mark.static
def test_the_article_column_expands_to_full_width():
    """The two-column post grid collapses; the wrapper relaxes."""
    scss = _print_scss()
    assert ".post-layout" in scss and "display: block" in scss, (
        "the print block must collapse `.post-layout` to a single column"
    )
    assert "max-width: 100%" in scss, (
        "the print block must let the article column use the full page width"
    )


@pytest.mark.static
def test_print_typography_stays_readable():
    """Point-sized dark-on-white body copy with a comfortable measure."""
    scss = _print_scss()
    assert "12pt" in scss, (
        "the print block must set a point-sized body copy"
    )
    assert "#fff" in scss and "#000" in scss, (
        "the print block must print dark text on a white page"
    )


@pytest.mark.static
def test_outbound_link_urls_are_shown():
    """External destinations print next to the link text."""
    scss = _print_scss()
    assert 'a[href^="http"]::after' in scss, (
        "the print block must append URLs to outbound links"
    )
    assert "attr(href)" in scss, (
        "the appended URL must come from the link target (`attr(href)`)"
    )


@pytest.mark.static
def test_breaks_avoid_splitting_content():
    """Headings, code, figures, images, tables and quotes stay whole."""
    scss = _print_scss()
    assert "break-inside: avoid" in scss, (
        "the print block must keep blocks from splitting across pages"
    )
    for selector in ("pre", "figure", "img", "table", "blockquote"):
        assert selector in scss, (
            f"the print block never protects `{selector}` from page breaks"
        )


@pytest.mark.static
def test_images_stay_bounded():
    """Print images never overflow the text column."""
    scss = _print_scss()
    assert "max-width: 100%" in scss, (
        "the print block must bound images to the text column"
    )


@pytest.mark.static
def test_the_print_block_needs_no_per_language_rules():
    """Both languages share the language-neutral selectors (issue scope)."""
    scss = _print_scss()
    assert "'vi'" not in scss and '"vi"' not in scss, (
        "the print block must not branch per language (#225: no per-language "
        "rules)"
    )


@pytest.mark.static
def test_the_print_block_keeps_clear_of_the_legibility_guard():
    """The #148 tail scan forbids scrollbar/height tokens past its marker."""
    scss = _print_scss()
    for banned in ("overflow-y", "max-height", "100vh", "position: sticky"):
        assert banned not in scss, (
            f"the print partial must not introduce `{banned}`: it sits after "
            "the #148 legibility block, whose guard scans everything past "
            "its own marker"
        )


# --- build guards (need Ruby; no browser) ----------------------------------


def test_the_built_stylesheet_ships_the_print_block(built_site):
    """The compiled CSS carries the print rules with the chrome hidden."""
    css = (built_site / "assets" / "css" / "style.css").read_text(
        encoding="utf-8"
    )
    assert "@media print" in css, (
        "the built stylesheet ships no print rules"
    )
    print_block = css.split("@media print", 1)[1]
    for selector in HIDDEN_SELECTORS:
        assert selector in print_block, (
            f"the built print block never hides `{selector}`"
        )
    assert "break-inside: avoid" in print_block
    assert "attr(href)" in print_block


# --- browser guards (need Ruby + a browser) ---------------------------------


def _print_context(browser):
    """A Chromium print-media context with third-party requests blocked."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        color_scheme="light",
    )
    page = context.new_page()
    origin_holder = {}

    def _route(route):
        if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost"):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", _route)
    page.emulate_media(media="print")
    origin_holder["page"] = page
    return context, page


def _open(page, built_site_url, path):
    response = page.goto(f"{built_site_url}{path}", wait_until="load")
    assert response is not None and response.status == 200, (
        f"{path} did not load (status {response.status if response else 'none'})"
    )
    page.wait_for_selector(".post-content", state="visible", timeout=10_000)
    return page


_DISPLAY_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return null;
  return getComputedStyle(el).display;
}
"""


@pytest.mark.parametrize("path", [EN_POST_PATH, VI_POST_PATH])
def test_print_emulation_hides_the_chrome(built_site_url, browser, path):
    """Under print media the article stands alone: no chrome is rendered."""
    context, page = _print_context(browser)
    try:
        _open(page, built_site_url, path)
        for selector in (
            ".site-header",
            ".share",
            ".site-footer",
            ".reading-progress",
            ".back-to-top",
            ".lightbox",
        ):
            assert page.evaluate(_DISPLAY_JS, selector) == "none", (
                f"{path} (print): `{selector}` must be hidden, got "
                f"{page.evaluate(_DISPLAY_JS, selector)!r}"
            )
        for selector in (".post-sidebar", ".comments"):
            display = page.evaluate(_DISPLAY_JS, selector)
            if display is not None:
                assert display == "none", (
                    f"{path} (print): `{selector}` must be hidden, got "
                    f"{display!r}"
                )
        assert page.evaluate(_DISPLAY_JS, ".post-content") != "none", (
            f"{path} (print): the article content must stay visible"
        )
    finally:
        context.close()


@pytest.mark.parametrize("path", [EN_POST_PATH, VI_POST_PATH])
def test_print_emulation_keeps_blocks_whole(built_site_url, browser, path):
    """Images (and code where present) refuse breaks inside under print."""
    context, page = _print_context(browser)
    try:
        _open(page, built_site_url, path)
        images = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.post-content img')).map("
            "(el) => getComputedStyle(el).breakInside)"
        )
        assert images, f"{path} (print): expected article images"
        for value in images:
            assert value == "avoid", (
                f"{path} (print): article images must avoid breaks inside, "
                f"got {value!r}"
            )
    finally:
        context.close()


@pytest.mark.parametrize("path", [EN_LINK_POST_PATH, VI_LINK_POST_PATH])
def test_print_emulation_shows_outbound_link_urls(
    built_site_url, browser, path
):
    """Outbound link targets print after the link text in both languages."""
    context, page = _print_context(browser)
    try:
        _open(page, built_site_url, path)
        hrefs = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.post-content a[href^=\"http\"]')).map("
            "(el) => el.getAttribute('href'))"
        )
        assert hrefs, f"{path} (print): expected an outbound article link"
        content = page.evaluate(
            """() => {
              const el = document.querySelector('.post-content a[href^="http"]');
              return getComputedStyle(el, '::after').content;
            }"""
        )
        assert hrefs[0] in content, (
            f"{path} (print): the outbound link must expose its URL through "
            f"`::after`, got {content!r}"
        )
    finally:
        context.close()
