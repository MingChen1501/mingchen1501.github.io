"""Guards for #148: secondary UI text is readable on small screens.

A reader-UX audit follow-up (#112, P2): sidebar blocks, tag chips and the
language switcher rendered at 14px (`$small-font-size`), which is hard to read
as grey-on-white text on phones.

Acceptance guarded here (risk-low, SCSS-only, no markup changes):

- at 360px the sidebar base text, the sidebar meta/count rows, the tag chips
  and the language switcher all render at >= 15px effective size (browser);
- at desktop width the hierarchy is unchanged: the sidebar base, the chips
  and the language pill still render at 14px (browser);
- the lift lives in a single `max-width: $on-medium` block in
  `_sass/minima/custom/_legibility.scss` (#174) (static): the desktop base rules still use
  `$small-font-size`, the compact rows keep an adequate line-height, and the
  block introduces no inner scrollbar (`overflow-y`/`max-height`) or height
  budget of its own — on phones both sidebars stack under the content as
  normal in-flow blocks, so the #63 desktop pin budget is untouched.

The browser guards use the session's shared `built_site`/`built_site_url`
fixtures from `conftest.py` (one `bundle exec jekyll build` for the whole
suite, served once over loopback HTTP). Third-party requests are aborted —
the local `style.css` fully defines the sizes.
"""

import contextlib
import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PHONE_WIDTH = 360
DESKTOP_WIDTH = 1280

# Selectors measured on the home list: the sidebar shell, a highlight title
# (inherits the sidebar base), the dimmed highlight date, a collapsed tag-row
# count, a home list chip and the header language pill.
PHONE_SELECTORS = [
    "aside.site-sidebar",
    "a.sidebar-post__title",
    "time.sidebar-post__meta",
    ".sidebar-tag__summary .tag-index__count",
    "a.tag-chip",
    "a.lang-switcher",
]

_MEASURE_JS = """
(selectors) => {
  const out = {};
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (!el) {
      out[selector] = null;
      continue;
    }
    const cs = getComputedStyle(el);
    out[selector] = {fontSize: cs.fontSize, lineHeight: cs.lineHeight};
  }
  return out;
}
"""


def _read(path):
    return path.read_text(encoding="utf-8")


def _split_legibility_block(scss):
    """The `(head, tail)` around the #148 mobile legibility pass."""
    marker = "Small-screen legibility (#148)"
    assert marker in scss, "the #148 legibility block is missing"
    head, tail = scss.split(marker, 1)
    return head, tail


def _px(value):
    assert value.endswith("px"), f"unexpected font size {value!r}"
    return float(value[:-2])


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_desktop_bases_still_use_the_small_font_size():
    """The lift is mobile-only: desktop keeps its 14px hierarchy."""
    head, _ = _split_legibility_block(conftest.custom_styles_text())
    for selector in (".post-sidebar", ".tag-chip", ".lang-switcher"):
        # The first `}` after the opening brace may close a nested `&:hover`
        # block, but the base declarations (including the font size) always
        # come first, so they are inside the captured group either way.
        block = re.search(re.escape(selector) + r"(?![\w-])\s*[^{]*\{([^}]*)\}", head)
        assert block, f"{selector} lost its desktop base rule"
        assert "font-size: $small-font-size;" in block.group(1), (
            f"{selector} must keep `font-size: $small-font-size` on desktop (#148)"
        )


@pytest.mark.static
def test_mobile_block_raises_the_secondary_text():
    """One `max-width` block lifts the sidebar, chips and pill to >= 15px."""
    _, tail = _split_legibility_block(conftest.custom_styles_text())
    assert "@include media-query($on-medium)" in tail, (
        "the #148 lift must be scoped to small screens via "
        "`@include media-query($on-medium)`"
    )
    # Body-like sidebar text goes to the full base size (16px).
    assert re.search(
        r"\.post-sidebar,\s*\.site-sidebar\s*\{[^}]*"
        r"font-size: \$base-font-size;",
        tail,
    ), "the mobile sidebar base must move to `$base-font-size` (16px)"
    # Compact rows stay compact: 15px with an adequate line-height.
    assert re.search(
        r"\.sidebar-post__meta\s*\{[^}]*font-size: 0\.9375em;[^}]*line-height: 1\.5;",
        tail,
    ), "the sidebar meta must render 15px with line-height 1.5 on phones"
    assert re.search(
        r"\.tag-index__count\s*\{[^}]*font-size: 15px;[^}]*line-height: 1\.5;",
        tail,
    ), "the tag counts must render 15px with line-height 1.5 on phones"
    assert re.search(
        r"\.tag-chip\s*\{[^}]*font-size: 15px;[^}]*line-height: 1\.6;",
        tail,
    ), "the tag chips must render 15px with line-height 1.6 on phones"
    assert re.search(
        r"\.lang-switcher\s*\{[^}]*font-size: 15px;",
        tail,
    ), "the language switcher must render 15px on phones"


@pytest.mark.static
def test_mobile_block_adds_no_scroll_or_height_budget():
    """The lift changes sizes only: no inner scrollbar, no layout structure."""
    _, tail = _split_legibility_block(conftest.custom_styles_text())
    for banned in ("overflow-y", "max-height", "100vh", "position: sticky"):
        assert banned not in tail, (
            f"the #148 block must not introduce `{banned}`"
        )


# --- browser guards (need Ruby + a browser) ---------------------------------


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
    page.wait_for_selector("aside.site-sidebar", state="attached", timeout=10_000)
    return page


def test_secondary_text_meets_the_minimum_at_360px(built_site_url, browser):
    with _viewport(browser, built_site_url, PHONE_WIDTH) as page:
        _open(page, built_site_url, "/")
        measured = page.evaluate(_MEASURE_JS, PHONE_SELECTORS)
        for selector in PHONE_SELECTORS:
            entry = measured[selector]
            assert entry is not None, (
                f"/ at {PHONE_WIDTH}px: no element for {selector}"
            )
            assert _px(entry["fontSize"]) >= 15, (
                f"/ at {PHONE_WIDTH}px: {selector} renders at "
                f"{entry['fontSize']}, below the 15px minimum (#148)"
            )


def test_desktop_hierarchy_is_unchanged(built_site_url, browser):
    """Above the mobile breakpoint the secondary text stays 14px."""
    expected = {
        "aside.site-sidebar": 14,
        "a.tag-chip": 14,
        "a.lang-switcher": 14,
    }
    with _viewport(browser, built_site_url, DESKTOP_WIDTH) as page:
        _open(page, built_site_url, "/")
        measured = page.evaluate(_MEASURE_JS, sorted(expected))
        for selector, size in expected.items():
            entry = measured[selector]
            assert entry is not None, (
                f"/ at {DESKTOP_WIDTH}px: no element for {selector}"
            )
            assert _px(entry["fontSize"]) == size, (
                f"/ at {DESKTOP_WIDTH}px: {selector} renders at "
                f"{entry['fontSize']}, expected {size}px (#148 keeps the "
                "desktop hierarchy)"
            )
