"""Guards for #141: every tap target is at least 24x24 CSS px (WCAG 2.2 SC 2.5.8).

A 360px audit measured the tag chips, pager links, social icons, language
pill and the opened mobile menu already at or above the minimum, so they are
pinned here without touching their styles. The sidebar links, TOC entries,
tag back-link, footer email link and desktop nav items fell short and were
lifted with `min-height` in `_sass/minima/custom/_tap-targets.scss` (#174) — CSS-only, no
markup restructuring, font sizes/margins/columns untouched.

Guarded here:

- the stylesheet carries a 24px minimum for each previously-small control,
  the opened mobile panel keeps its own padding, and the already-compliant
  controls keep the sizing that makes them pass (static);
- at 360px every interactive target on `/`, `/vi/`, a post page (with TOC)
  and a tag page (EN + VI) measures >= 24px in both dimensions: chips,
  pager, social icons, lang switcher, opened mobile menu items, sidebar
  titles / tag-post links / "view all" links / heading links, TOC summary +
  entries, tag back-link and footer email (browser);
- at desktop width the nav items measure >= 24px tall (browser).

The browser guards use the session's shared `built_site`/`built_site_url`
fixtures from `conftest.py` (one `bundle exec jekyll build` for the whole
suite, served once over loopback HTTP). Third-party requests are aborted —
the local `style.css` fully defines the layout.
"""

import contextlib
import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_SCSS = REPO_ROOT / "_sass" / "minima" / "_layout.scss"
TAG_PAGES_DIR = REPO_ROOT / "tags"
VI_TAG_PAGES_DIR = REPO_ROOT / "vi" / "tags"

PHONE_WIDTH = 360
DESKTOP_WIDTH = 1280

TAG_PAGE = f"/tags/{sorted(path.stem for path in TAG_PAGES_DIR.glob('*.md'))[0]}/"
VI_TAG_PAGE = f"/vi/tags/{sorted(path.stem for path in VI_TAG_PAGES_DIR.glob('*.md'))[0]}/"

# Controls the #141 audit found below 24px, each lifted with `min-height`.
# (The desktop nav items are the exception: font-dependent inline height, so
# `inline-block` + `min-height` scoped to desktop widths, pinned by
# `test_desktop_nav_items_meet_the_minimum_...` below.)
FIXED_SELECTORS = [
    ".sidebar-post__title",
    ".sidebar-tag__posts a",
    ".sidebar-tag__more",
    ".sidebar__heading-link",
    ".post-toc__summary",
    ".post-toc__item a",
    ".tag-page__back a",
    ".contact-list .u-email",
    # The minimum is pinned on the link itself, independent of the glyph
    # inside (inline SVG since #254, icon font before it).
    ".social-media-list a",
]

# The inline boxes among them also need `inline-block`, or the height cannot
# apply (and `min-width`, so a short label cannot shrink the other axis).
INLINE_FIXED_SELECTORS = [
    ".sidebar-tag__posts a",
    ".sidebar__heading-link",
    ".post-toc__item a",
    ".tag-page__back a",
    ".contact-list .u-email",
]

# Already at or above 24px in both dimensions before #141: pinned, untouched.
ALREADY_COMPLIANT = {
    "the pager keeps its 45px minimum": (
        LAYOUT_SCSS,
        r"\.pagination\s*\{[^}]*li\s*\{[^}]*min-width:\s*45px;[^}]*min-height:\s*45px;",
    ),
    "the social icons keep their 45px minimum": (
        LAYOUT_SCSS,
        r"\.social-media-list\s*\{[^}]*li\s*\{[^}]*min-width:\s*45px;[^}]*min-height:\s*45px;",
    ),
    "the language pill keeps its 44px minimum": (
        conftest.custom_styles_text(),
        r"\.lang-switcher\s*\{[^}]*min-width:\s*44px;[^}]*min-height:\s*44px;",
    ),
    "the mobile toggle keeps its 36px box": (
        LAYOUT_SCSS,
        r"\.nav-toggle\s*\{[^}]*width:\s*36px;[^}]*height:\s*36px;",
    ),
    "the chips keep the padding and line-height that clear 24px": (
        conftest.custom_styles_text(),
        r"\.tag-chip\s*\{[^}]*padding:\s*2px 10px;[^}]*line-height:\s*1\.6;",
    ),
}


def _read(path):
    return path.read_text(encoding="utf-8")


def _blocks(scss, selector):
    """All declaration blocks for `selector` (flat rules, no nesting).

    The #141 minima live together in the tap-targets partial (#174),
    while some selectors keep an earlier base rule — every block counts, since
    the cascade merges them.
    """
    matches = re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", scss)
    found = [match.group(1) for match in matches]
    assert found, f"{selector} has no rule in the custom styles"
    return found


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
@pytest.mark.parametrize("selector", FIXED_SELECTORS, ids=lambda s: s)
def test_small_controls_carry_a_24px_minimum(selector):
    blocks = _blocks(conftest.custom_styles_text(), selector)
    assert any("min-height: $tap-target-minimum;" in block for block in blocks), (
        f"{selector} must keep `min-height: $tap-target-minimum` (24px, #141)"
    )
    if selector in INLINE_FIXED_SELECTORS:
        assert any("display: inline-block;" in block for block in blocks), (
            f"{selector} is an inline box: it needs `inline-block` for the "
            "minimum height to apply (#141)"
        )
        assert any("min-width: $tap-target-minimum;" in block for block in blocks), (
            f"{selector} must also keep `min-width: $tap-target-minimum` so a short label "
            "cannot shrink the other axis (#141)"
        )


@pytest.mark.static
def test_desktop_nav_items_meet_the_minimum_without_touching_the_mobile_panel():
    """Inline nav height follows the available fonts (22px with local fonts,
    19px on CI runners), so neither padding nor inheritance can guarantee the
    minimum — and plain `inline-block` would take the 54px header strut.
    Desktop items pin a 24px line box of their own plus `min-height`, scoped
    above the mobile breakpoint so the panel keeps its block rows and
    `5px 10px` padding.
    """
    scss = conftest.custom_styles_text()
    match = re.search(
        r"@media screen and \(min-width:[^)]*\)\s*\{\s*"
        r"\.site-nav \.nav-item\s*\{([^}]*)\}",
        scss,
    )
    assert match, (
        "desktop nav items must carry the minimum inside a min-width query"
    )
    block = match.group(1)
    assert "display: inline-block;" in block
    assert "line-height: $tap-target-minimum;" in block
    assert "min-width: $tap-target-minimum;" in block
    assert "min-height: $tap-target-minimum;" in block
    # Above the mobile breakpoint: the collapsible panel (max-width) can
    # never meet this rule, so its block rows are untouched.
    assert "$on-medium + 1px" in scss
    # The opened mobile panel keeps its roomy rows.
    assert "padding: 5px 10px;" in _read(LAYOUT_SCSS)


@pytest.mark.static
@pytest.mark.parametrize("note", sorted(ALREADY_COMPLIANT), ids=lambda s: s)
def test_already_compliant_controls_keep_their_sizing(note):
    source, pattern = ALREADY_COMPLIANT[note]
    # Entries are either a file to read or the concatenated custom styles (#174).
    text = _read(source) if isinstance(source, Path) else source
    label = source.name if isinstance(source, Path) else "custom styles"
    assert re.search(pattern, text, re.S), (
        f"{note} ({label})"
    )


# --- browser guards (need Ruby + a browser) ---------------------------------


def _toc_post_url(built_site):
    """URL of a built post page that renders TOC entries (deterministic)."""
    for path in sorted(built_site.rglob("*.html")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "post-toc__item" not in text:
            continue
        relative = path.relative_to(built_site).as_posix()
        if path.name == "index.html":
            return "/" + relative[: -len("index.html")]
        return "/" + relative
    raise AssertionError("no built post page renders TOC entries")


_MEASURE_JS = """
(selectors) => {
  const out = {};
  for (const selector of selectors) {
    out[selector] = Array.from(document.querySelectorAll(selector))
      .map((el) => {
        const box = el.getBoundingClientRect();
        return {w: box.width, h: box.height,
                text: (el.textContent || '').trim().slice(0, 40)};
      })
      .filter((entry) => entry.w > 0 && entry.h > 0);
  }
  return out;
}
"""

# Selectors that must render (non-empty) on each page under test. The pager
# only exists on the paginated English home; the TOC only on long posts; the
# back link only on tag pages; the sidebar only on list pages.
LIST_PAGE_SELECTORS = [
    "a.tag-chip",
    ".social-media-list a",
    "a.lang-switcher",
    ".site-nav .nav-item",
    "a.sidebar-post__title",
    ".sidebar-tag__posts a",
    "a.sidebar-tag__more",
    ".sidebar__heading-link",
    ".contact-list .u-email",
]

POST_PAGE_SELECTORS = [
    "a.tag-chip",
    ".social-media-list a",
    "a.lang-switcher",
    ".site-nav .nav-item",
    ".post-toc__summary",
    ".post-toc__item a",
    ".contact-list .u-email",
]


@contextlib.contextmanager
def _viewport(browser, built_site_url, width, height=800):
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
    page.wait_for_selector(".site-nav", state="attached", timeout=10_000)
    return page


def _open_collapsed_rows(page):
    """Reveal the tag rows' links so their targets can be measured too."""
    page.evaluate(
        "() => document.querySelectorAll('details.sidebar-tag__group')"
        ".forEach((group) => { group.open = true; })"
    )


def _open_mobile_menu(page):
    page.locator(".nav-toggle").click()


def _assert_targets(measured, path, width, extra=()):
    required = set(measured) | set(extra)
    for selector, entries in measured.items():
        if selector in required:
            assert entries, (
                f"{path} at {width}px: no visible target for {selector}"
            )
        for entry in entries:
            assert entry["w"] >= 24 and entry["h"] >= 24, (
                f"{path} at {width}px: {selector} {entry['text']!r} measures "
                f"{entry['w']:.1f}x{entry['h']:.1f}, below the 24px minimum"
            )


@pytest.mark.parametrize(
    "path, selectors, extra",
    [
        ("/", LIST_PAGE_SELECTORS, (".pagination a",)),
        ("/vi/", LIST_PAGE_SELECTORS, ()),
        (TAG_PAGE, [*LIST_PAGE_SELECTORS, ".tag-page__back a"], ()),
        (VI_TAG_PAGE, [*LIST_PAGE_SELECTORS, ".tag-page__back a"], ()),
    ],
)
def test_list_page_targets_meet_the_minimum_at_360px(
    path, selectors, extra, built_site_url, browser,
):
    with _viewport(browser, built_site_url, PHONE_WIDTH) as page:
        _open(page, built_site_url, path)
        _open_collapsed_rows(page)
        _open_mobile_menu(page)
        measured = page.evaluate(_MEASURE_JS, selectors + list(extra))
        _assert_targets(measured, path, PHONE_WIDTH, extra)


def test_post_page_targets_meet_the_minimum_at_360px(
    built_site, built_site_url, browser,
):
    path = _toc_post_url(built_site)
    with _viewport(browser, built_site_url, PHONE_WIDTH) as page:
        _open(page, built_site_url, path)
        _open_mobile_menu(page)
        measured = page.evaluate(_MEASURE_JS, POST_PAGE_SELECTORS)
        _assert_targets(measured, path, PHONE_WIDTH)


def test_desktop_nav_items_meet_the_minimum(built_site_url, browser):
    """Desktop keeps its design; the items just clear 24px tall (#141)."""
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        assert page.locator(".nav-toggle").is_hidden()
        measured = page.evaluate(_MEASURE_JS, [".site-nav .nav-item"])
        _assert_targets(measured, "/", DESKTOP_WIDTH)
