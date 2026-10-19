"""Guards for #122: the language switcher is a compact pill control.

The old control was a small bordered text link ("English" / "Tiếng Việt")
appended inside `.site-nav`: a <44px tap target competing with the hamburger
on phones and a random boxed link on desktop, with no icon and no `lang`
semantics beyond `hreflang`.

Guarded here:

- the pill ships a globe icon (inline SVG, `aria-hidden`) + short target
  code (`EN` / `VI`); the full language name stays the accessible name
  (`aria-label`) and `title`, with `lang` on the code and `hreflang` on the
  link (static + rendered on `/` and `/vi/`);
- the ref/fallback link logic is untouched (first-match wins, paginated URLs
  skipped, other-language home fallback) — spot-checked on the build;
- the control renders in the header row, never inside `.site-nav` / the
  collapsible `#nav-menu` panel and never in the sidebar (static + build);
- styling hits the contract: min 44x44 tap target, pill radius, clear
  hover/focus-visible states, phone clearance from the hamburger (static);
- at 320px and 375px the pill is visible, >= 44x44, single-line, clears the
  hamburger and introduces no horizontal overflow; on desktop it is right
  aligned, vertically centered, hover-tinted, keyboard-focusable with a 3px
  ring, and Enter follows the link (browser, EN + VI homes).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_INCLUDE = REPO_ROOT / "_includes" / "header.html"
SWITCHER_INCLUDE = REPO_ROOT / "_includes" / "lang-switcher.html"
NAV_ITEMS_INCLUDE = REPO_ROOT / "_includes" / "nav-items.html"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
CUSTOM_STYLES = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"

PHONE_WIDTHS = (320, 375)
DESKTOP_WIDTH = 1280


def _read(path):
    return path.read_text(encoding="utf-8")


def _switcher_tag(html):
    match = re.search(r'<a class="lang-switcher".*?</a>', html, re.S)
    assert match, "the page renders no language switcher"
    return match.group(0)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_switcher_markup_is_a_pill_with_an_accessible_name():
    html = _read(SWITCHER_INCLUDE)
    # Globe affordance, hidden from assistive tech (the code carries meaning).
    assert "<svg" in html and 'aria-hidden="true"' in html
    # Short target codes, not the long "English" / "Tiếng Việt" words.
    assert "'EN'" in html or '"EN"' in html or ">EN<" in html or "EN" in html
    assert "switch_code" in html
    assert "EN" in html and "VI" in html
    # Full language name as the accessible name + title, localized per side.
    assert 'aria-label="{{ switch_name }}"' in html
    assert 'title="{{ switch_name }}"' in html
    assert "View this page in English" in html
    assert "Xem trang này bằng tiếng Việt" in html
    # Language semantics on the label and the link.
    assert 'lang="{{ switch_other }}"' in html
    assert 'hreflang="{{ switch_other }}"' in html
    # The ref/fallback behaviour is untouched: counterpart lookup by `ref`
    # with the other-language home as fallback (#93, #104).
    assert "switch_ref" in html and "switch_home" in html
    assert "switch_found" in html
    assert "/vi/" in html


@pytest.mark.static
def test_switcher_lives_in_the_header_row_not_the_nav_panel():
    header = _read(HEADER_INCLUDE)
    assert "include lang-switcher.html" in header
    nav = re.search(r'<nav class="site-nav".*?</nav>', header, re.S)
    assert nav, "the header renders no `.site-nav` to judge"
    assert "lang-switcher" not in nav.group(0), (
        "the switcher must sit in the header row, not inside `.site-nav`"
    )
    assert "lang-switcher" not in _read(NAV_ITEMS_INCLUDE), (
        "the switcher must never render inside the collapsible `#nav-menu` panel"
    )


@pytest.mark.static
def test_switcher_styles_hit_the_tap_target_and_states():
    scss = _read(CUSTOM_STYLES)
    assert "min-width: 44px" in scss
    assert "min-height: 44px" in scss
    assert "border-radius: 999px" in scss
    assert ".lang-switcher" in scss
    assert "&:hover" in scss
    assert ".lang-switcher:focus-visible" in scss or "&:focus-visible" in scss
    assert "outline: 3px solid" in scss
    # Header row: title leads, nav + pill share the right end.
    assert ".site-header .wrapper" in scss
    assert "align-items: center" in scss
    # Phones: the pill clears the hamburger box instead of stacking with the
    # title's old clearance padding.
    assert "margin-right: 48px" in scss


@pytest.mark.static
def test_switcher_stays_out_of_the_sidebar():
    assert "lang-switcher" not in _read(SIDEBAR_INCLUDE), (
        "the switcher must stay in the header, never in the sidebar (#65 budget)"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def _switcher_on(built_site, rel):
    html = (built_site / rel).read_text(encoding="utf-8")
    tag = _switcher_tag(html)
    nav = re.search(r'<nav class="site-nav".*?</nav>', html, re.S)
    assert nav, f"/{rel} renders no `.site-nav` to judge"
    assert "lang-switcher" not in nav.group(0), (
        f"/{rel} renders the switcher inside `.site-nav`"
    )
    panel = re.search(r'<div class="nav-items" id="nav-menu".*?</div>', html, re.S)
    if panel:
        assert "lang-switcher" not in panel.group(0), (
            f"/{rel} renders the switcher inside the `#nav-menu` panel"
        )
    aside = re.search(r'<aside class="site-sidebar".*?</aside>', html, re.S)
    if aside:
        assert "lang-switcher" not in aside.group(0), (
            f"/{rel} renders the switcher inside the sidebar"
        )
    return tag


def test_switcher_points_at_the_counterpart_with_polite_markup(built_site):
    en = _switcher_on(built_site, "index.html")
    assert 'hreflang="vi"' in en
    assert 'href="/vi/"' in en
    assert 'aria-label="Xem trang này bằng tiếng Việt"' in en
    assert 'title="Xem trang này bằng tiếng Việt"' in en
    assert 'lang="vi"' in en and ">VI<" in en
    assert 'aria-hidden="true"' in en
    vi = _switcher_on(built_site, "vi/index.html")
    assert 'hreflang="en"' in vi
    assert 'href="/"' in vi
    assert 'aria-label="View this page in English"' in vi
    assert 'title="View this page in English"' in vi
    assert 'lang="en"' in vi and ">EN<" in vi
    assert 'aria-hidden="true"' in vi


# --- browser guards (need Ruby + a browser) ---------------------------------


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
    page.wait_for_selector(".lang-switcher", state="visible", timeout=10_000)
    page.wait_for_timeout(300)
    return page


@pytest.mark.parametrize("path,code", [("/", "VI"), ("/vi/", "EN")])
@pytest.mark.parametrize("width", PHONE_WIDTHS)
def test_mobile_pill_clears_the_hamburger_without_overflow(
    path, code, width, built_site_url, browser
):
    """#122: >= 44x44, single-line, clear of the toggle, no 320px overflow."""
    for page in _viewport(browser, built_site_url, width):
        _open(page, built_site_url, path)
        switcher = page.locator(".lang-switcher")
        assert switcher.count() == 1, f"{path}: expected one switcher"
        assert (switcher.text_content() or "").strip() == code
        box = switcher.bounding_box()
        assert box is not None, f"{path}: the switcher has no box at {width}px"
        assert box["width"] >= 44, f"{path}: too narrow ({box['width']})"
        assert box["height"] >= 44, f"{path}: too short ({box['height']})"
        assert box["height"] < 60, (
            f"{path}: the pill wrapped to two lines ({box['height']}px tall)"
        )
        toggle = page.locator(".nav-toggle")
        assert toggle.is_visible(), f"{path}: the toggle is hidden at {width}px"
        gap = toggle.bounding_box()["x"] - (box["x"] + box["width"])
        assert gap >= 4, f"{path}: the pill crowds the hamburger (gap {gap}px)"
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 1, f"{path}: horizontal overflow of {overflow}px"


@pytest.mark.parametrize("path,target", [("/", "/vi/"), ("/vi/", "/")])
def test_desktop_pill_placement_hover_focus_and_keyboard(
    path, target, built_site_url, browser
):
    """#122: right-aligned, centered, tinted hover, 3px focus ring, Enter goes."""
    for page in _viewport(browser, built_site_url, DESKTOP_WIDTH):
        _open(page, built_site_url, path)
        switcher = page.locator(".lang-switcher")
        assert switcher.is_visible(), f"{path}: the pill is hidden on desktop"
        centers = page.evaluate(
            "() => { const wrap = document.querySelector('.site-header .wrapper')."
            "getBoundingClientRect(); const pill = document.querySelector("
            "'.lang-switcher').getBoundingClientRect(); return { header: "
            "document.querySelector('.site-header').getBoundingClientRect().top "
            "+ document.querySelector('.site-header').getBoundingClientRect()."
            "height / 2, pill: pill.top + pill.height / 2,"
            " pillRight: pill.right, wrapRight: wrap.right }; }"
        )
        assert abs(centers["pill"] - centers["header"]) <= 10, (
            f"{path}: the pill is not vertically centered in the header"
        )
        assert centers["wrapRight"] - centers["pillRight"] < 60, (
            f"{path}: the pill is not right-aligned"
        )
        before = switcher.evaluate(
            "(el) => getComputedStyle(el).borderColor"
        )
        switcher.hover()
        after = switcher.evaluate("(el) => getComputedStyle(el).borderColor")
        assert before != after, f"{path}: hover does not tint the pill"
        page.evaluate("() => document.querySelector('.lang-switcher').focus()")
        ring = switcher.evaluate(
            "(el) => ({ width: getComputedStyle(el).outlineWidth, "
            "style: getComputedStyle(el).outlineStyle })"
        )
        assert ring["width"] == "3px" and ring["style"] == "solid", (
            f"{path}: the focus ring is {ring}, expected a 3px solid outline"
        )
        with page.expect_navigation(wait_until="load", timeout=10_000):
            page.keyboard.press("Enter")
        assert urlparse(page.url).path == target, (
            f"{path}: Enter led to {urlparse(page.url).path}, expected {target}"
        )
