"""ToC scroll-spy with auto-expanded mounts (#345).

`_includes/post-toc.html` renders the list expanded (`<details open>`,
plain anchors, both mounts), so the ToC works with JS disabled; the
post-only `assets/js/toc-spy.js` progressively enhances it by marking the
row for the section being read (`aria-current="location"` on both copies,
styled in `custom/_toc.scss` with the theme-aware link colour plus an
inset bar — never colour-only).

Guarded here:

- static (no Ruby, no browser): the script stays vanilla, small, and
  dependency-free; it observes headings with `IntersectionObserver`,
  falls back to a passive scroll listener, marks exactly one row per
  mount with `aria-current="location"`, adds no smooth scrolling (so
  `prefers-reduced-motion` needs no handling), and never touches tab
  order or the `details[open]` state; the tag lives in the post-only
  gate after the helper with its build token; the active style keys off
  the attribute with a theme-safe colour plus a non-colour indicator,
  and indentation stays CSS-driven per level class;
- built (needs Ruby, no browser): both mounts render expanded with the
  localized label, EN and VI;
- browser (needs Ruby + a browser): both copies load expanded; scrolling
  a 16-section post marks exactly the row under the viewport top on both
  copies (first row at the very top, last row at the end, no flicker
  between sections); clicking a row marks it immediately; keyboard users
  can tab through the rows; the active style passes contrast in light
  and dark; level indentation holds with no horizontal overflow down to
  small phones; with JS disabled the list stays expanded and usable.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect

import test_post_only_js

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "toc-spy.js"
TOC_SCSS = REPO_ROOT / "_sass" / "minima" / "custom" / "_toc.scss"
SUB_FOOTER = test_post_only_js.SUB_FOOTER

SCRIPT_PATH = "/assets/js/toc-spy.js"
# The scroll-spy ships on post pages only (#345): keep it small.
MAX_SCRIPT_BYTES = 6 * 1024

EN_LONG_POST = "/2022/12/25/explaining-the-internet.html"
VI_LONG_POST = "/vi/2022/12/25/gioi-thieu-ve-internet.html"


def _read(path):
    return Path(path).read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_spy_script_exists_and_stays_vanilla():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the ToC scroll-spy ships on post pages only: keep it under "
        f"{MAX_SCRIPT_BYTES} bytes (#345)"
    )
    assert "import " not in text and "require(" not in text, (
        "the scroll-spy must not depend on anything (#345)"
    )
    assert "SiteUtils.onReady" in text, (
        "the scroll-spy must run through the shared DOM-ready helper "
        "after site-utils.js (#246, #345)"
    )


@pytest.mark.static
def test_the_spy_observes_headings_with_a_passive_scroll_fallback():
    text = _read(SCRIPT)
    assert "IntersectionObserver" in text, (
        "the scroll-spy must observe headings instead of polling (#345)"
    )
    assert re.search(
        r"addEventListener\(\s*['\"]scroll['\"].*passive", text, re.S
    ), "the scroll fallback must stay passive (#345)"
    assert "requestAnimationFrame" in text, (
        "scroll handling must be rAF-throttled (#345)"
    )


@pytest.mark.static
def test_the_spy_marks_one_row_per_mount_with_aria_current():
    text = _read(SCRIPT)
    assert 'aria-current", "location"' in text or (
        "'aria-current', 'location'" in text
    ), 'the active row must use aria-current="location" (#345)'
    assert "removeAttribute('aria-current')" in text or (
        'removeAttribute("aria-current")' in text
    ), "a newly active row must unmark the previous one (#345)"
    assert ".post-toc__nav" in text, (
        "both mounts must be marked together (#345)"
    )


@pytest.mark.static
def test_the_spy_adds_no_motion_and_steals_no_keyboard_or_toggle():
    text = _read(SCRIPT)
    # Strip the header comment: the assertions below pin runtime behaviour,
    # while the comment is allowed to explain the reduced-motion story.
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    # The default anchor jump is instant; nothing smooth is ever added, so
    # prefers-reduced-motion needs no handling (#345).
    assert "smooth" not in code, (
        "the scroll-spy must not smooth-scroll (reduced motion, #345)"
    )
    assert "scrollIntoView" not in code and "scrollTo" not in code, (
        "the scroll-spy must never move the viewport itself (#345)"
    )
    assert "tabindex" not in code.lower() and "tabIndex" not in code, (
        "the scroll-spy must leave the ToC tab order alone (#345)"
    )
    assert ".open" not in code and "removeAttribute('open'" not in code, (
        "the scroll-spy must never close the expanded ToC (#345)"
    )


@pytest.mark.static
def test_the_spy_script_is_gated_to_post_pages():
    """The tag lives in the post-layout conditional with its token (#345)."""
    html = _read(SUB_FOOTER)
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", html)
    assert gate, "the post-layout gate in sub-footer.html is gone (#345)"
    gated = html[gate.end():html.index("endif", gate.end())]
    assert f"{SCRIPT_PATH}?v=" in gated, (
        "the toc-spy script tag must live inside the post-layout "
        "conditional (#345)"
    )
    assert gated.index("/assets/js/reading-progress.js?v=") < gated.index(
        f"{SCRIPT_PATH}?v="
    ), "toc-spy must load after reading-progress in document order (#345)"
    assert html.index("/assets/js/site-utils.js?v=") < html.index(
        f"{SCRIPT_PATH}?v="
    ), "toc-spy must load after the shared helper (#246, #345)"


@pytest.mark.static
def test_the_active_style_is_visible_in_both_themes_without_colour_only():
    scss = _read(TOC_SCSS)
    rule = re.search(
        r'\.post-toc__item a\[aria-current="location"\]\s*\{(.*?)\}',
        scss,
        re.S,
    )
    assert rule, (
        "the active style must key off the aria-current attribute (#345)"
    )
    body = rule.group(1)
    # `$link-base-color` compiles to `var(--minima-link-base-color)`, which
    # the skin swaps per theme: ~5.1:1 on the light background, ~5.4:1 on
    # the dark one (both over the 4.5:1 bar, measured 2026-10-21).
    assert "color: $link-base-color" in body, (
        "the active row must use the theme-aware link colour (#345)"
    )
    assert "border-left-color: $link-base-color" in body, (
        "the active row needs a non-colour indicator next to the colour "
        "(#345)"
    )


@pytest.mark.static
def test_the_level_indentation_is_css_driven_per_level_class():
    scss = _read(TOC_SCSS)
    h3 = re.search(r"\.post-toc__item--h3\s*\{(.*?)\}", scss, re.S)
    assert h3 and "padding-left" in h3.group(1), (
        "h3 rows must indent one step via their level class (#345)"
    )
    assert "--h4" not in scss, (
        "no h4 level exists: no published post uses h4 headings (#345)"
    )
    assert "overflow-wrap" in scss, (
        "long ToC titles must wrap instead of overflowing small phones "
        "(#345)"
    )


# --- emitted site (needs Ruby, no browser) ---------------------------------


@pytest.mark.parametrize(
    ("rel", "label"),
    [
        ("2022/12/25/explaining-the-internet.html", "On this page"),
        ("vi/2022/12/25/gioi-thieu-ve-internet.html", "Trong bài này"),
    ],
)
def test_long_posts_render_both_mounts_expanded(built_site, rel, label):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {rel}"
    html = page.read_text(encoding="utf-8")
    assert html.count('<details class="post-toc" open>') == 2, (
        f"{rel}: both ToC mounts must render expanded on load (#345)"
    )
    assert "<details class=\"post-toc\">" not in html.replace(
        '<details class="post-toc" open>', ""
    ), f"{rel}: no collapsed ToC copy may remain (#345)"


# --- browser behaviour (needs Ruby + a browser) ------------------------------


@pytest.fixture()
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    browser_page = context.new_page()
    # Only the site's own files are fetched: third-party requests are aborted
    # so the run stays offline-safe.
    browser_page.route(
        "**/*",
        lambda route: (
            route.continue_()
            if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost")
            else route.abort()
        ),
    )
    try:
        yield browser_page
    finally:
        context.close()


def _visible_mount(page):
    displays = page.evaluate(
        """() => ({
          inline: getComputedStyle(document.querySelector('.post-toc-mount--inline')).display,
          sidebar: getComputedStyle(document.querySelector('.post-toc-mount--sidebar')).display,
        })"""
    )
    return ".post-toc-mount--sidebar" if displays["sidebar"] != "none" else (
        ".post-toc-mount--inline"
    )


def _heading_ids(page):
    return page.evaluate(
        """() => Array.from(
          document.querySelectorAll('.post-content h2[id], .post-content h3[id]')
        ).map(h => h.id)"""
    )


def _scroll_to_heading(page, heading_id, offset_px=10):
    """Put a heading just below the viewport top, instantly.

    The spy counts a heading as current once its top reaches the
    viewport top (plus a small `EDGE_PX` slack), so the target must land
    within that band — not 100px down the viewport.
    """
    page.evaluate(
        "const h = document.getElementById("
        f"{heading_id!r});"
        " window.scrollTo(0, h.getBoundingClientRect().top"
        " + window.scrollY - " + str(offset_px) + ");"
    )


def _settle_layout(page):
    """Wait out late image boxes before measuring heading positions.

    Aborted or slow images resize their boxes after load; any scroll
    measured before that goes stale when the headings move. Waiting for
    every image to finish keeps the scroll targets fresh.
    """
    page.wait_for_function(
        "() => Array.from(document.images).every(i => i.complete)",
        timeout=15_000,
    )


def _expect_active(page, mount, heading_id):
    page.wait_for_function(
        f"""() => {{
          const marked = Array.from(document.querySelectorAll(
            '{mount} a[aria-current="location"]'
          )).map(a => a.getAttribute('href'));
          return marked.length === 1 && marked[0] === '#{heading_id}';
        }}""",
        timeout=10_000,
    )


def test_both_copies_load_expanded_and_mark_one_row_each(
    built_site_url, page
):
    """Expanded on load; scrolling marks exactly the row being read (#345)."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    assert page.locator('details.post-toc[open]').count() == 2
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    assert len(ids) >= 16, f"expected a long post, got {len(ids)} headings"
    for index in (0, 5):
        _scroll_to_heading(page, ids[index])
        _expect_active(page, mount, ids[index])
    # The last heading cannot scroll fully to the viewport top when the
    # article tail is short: reaching the page end must still mark it.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    _expect_active(page, mount, ids[-1])
    # Both copies mark the same row.
    marked = page.locator(
        ".post-toc__nav a[aria-current='location']"
    ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
    assert marked == [f"#{ids[-1]}", f"#{ids[-1]}"], (
        f"both ToC copies must mark the same row, got {marked} (#345)"
    )


def test_the_last_heading_stays_active_at_the_end(built_site_url, page):
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    _expect_active(page, mount, ids[-1])


def test_clicking_a_row_marks_it_immediately(built_site_url, page):
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    page.locator(f"{mount} a[href='#{ids[7]}']").click()
    # The default anchor jump fires after the click handler: poll until the
    # scroll settles on the clicked section instead of asserting mid-flight.
    expect(page.locator(f"{mount} a[href='#{ids[7]}']")).to_have_attribute(
        "aria-current", "location", timeout=10_000
    )
    assert page.url.split("#")[-1] == ids[7], (
        "the ToC link must still jump to its section (#345)"
    )


def test_keyboard_users_can_reach_every_row(built_site_url, page):
    """Rows stay plain anchors in tab order inside the expanded list."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    mount = _visible_mount(page)
    links = page.locator(f"{mount} .post-toc__list a")
    assert links.count() >= 16
    assert page.evaluate(
        f"""() => Array.from(
          document.querySelectorAll('{mount} .post-toc__list a')
        ).every(a => a.tabIndex >= 0 && a.getAttribute('tabindex') === null)"""
    ), "every ToC row must stay keyboard-reachable (#345)"
    links.first.focus()
    assert page.evaluate(
        "document.activeElement.classList.contains('post-toc__list')"
        " || document.activeElement.tagName === 'A'"
    ), "a ToC row must be focusable (#345)"


def _active_contrast(page):
    return page.evaluate(
        """() => {
          const lum = (s) => {
            const c = s.match(/[\\d.]+/g).map(Number).slice(0, 3)
              .map(v => v / 255).map(v => v <= 0.03928 ? v / 12.92
                : Math.pow((v + 0.055) / 1.055, 2.4));
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
          };
          const link = document.querySelector(
            ".post-toc__nav a[aria-current='location']"
          );
          const fg = lum(getComputedStyle(link).color);
          const bg = lum(getComputedStyle(document.body).backgroundColor);
          const hi = Math.max(fg, bg), lo = Math.min(fg, bg);
          return (hi + 0.05) / (lo + 0.05);
        }"""
    )


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_active_row_passes_contrast_in_both_themes(
    built_site_url, browser, scheme
):
    """The active style is a theme-aware link colour: >= 4.5:1 either way."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 900}, color_scheme=scheme
    )
    try:
        themed = context.new_page()
        themed.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
        _settle_layout(themed)
        ids = themed.evaluate(
            """() => Array.from(
              document.querySelectorAll('.post-content h2[id]')
            ).map(h => h.id)"""
        )
        _scroll_to_heading(themed, ids[3])
        themed.wait_for_function(
            "() => document.querySelector"
            "(\"a[aria-current='location']\") !== null",
            timeout=10_000,
        )
        ratio = _active_contrast(themed)
        assert ratio >= 4.5, (
            f"the active ToC row is {ratio:.2f}:1 in {scheme} mode, "
            "below the 4.5:1 bar (#345)"
        )
    finally:
        context.close()


def test_level_indentation_holds_without_overflow_on_small_phones(
    built_site_url, browser
):
    context = browser.new_context(viewport={"width": 320, "height": 700})
    try:
        narrow = context.new_page()
        narrow.goto(
            built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load"
        )
        assert narrow.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "the expanded ToC must not overflow a 320px viewport (#345)"
        lefts = narrow.evaluate(
            """() => Array.from(document.querySelectorAll(
              '.post-toc-mount--inline .post-toc__item a'
            )).map(a => a.getBoundingClientRect().left)"""
        )
        assert lefts, "expected ToC rows in the inline mount (#345)"
        assert max(lefts) - min(lefts) == 0, (
            "h2 rows must share one column (level-accurate indentation, #345)"
        )
    finally:
        context.close()


def test_no_js_readers_get_the_expanded_list_with_working_anchors(
    built_site_url, browser
):
    """No-JS: expanded ToC, plain anchors, no dead states (#345)."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        plain.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
        assert plain.locator('details.post-toc[open]').count() == 2
        assert plain.locator(
            ".post-toc__nav a[aria-current]"
        ).count() == 0
        ids = plain.evaluate(
            """() => Array.from(
              document.querySelectorAll('.post-content h2[id]')
            ).map(h => h.id)"""
        )
        inline_visible = plain.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--inline')).display !== 'none'"
        )
        mount = (
            ".post-toc-mount--inline" if inline_visible
            else ".post-toc-mount--sidebar"
        )
        plain.locator(f"{mount} .post-toc__nav a[href='#{ids[4]}']").click()
        plain.wait_for_function(
            f"() => window.location.hash === '#{ids[4]}'", timeout=10_000
        )
    finally:
        context.close()
