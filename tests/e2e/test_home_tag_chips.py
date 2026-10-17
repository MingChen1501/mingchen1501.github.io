"""Browser guard for #47: tag chips on the home post list.

Acceptance for #47 (epic #44):

- every home list item shows that post's tags as chips linking to
  ``/tags/<tag>/`` (the pages added by #46),
- the chips are the *same* chips the post page shows (shared
  ``_includes/post-tags.html``, same classes and labels), and
- the list does not scroll sideways on a phone (375px, ``scrollWidth <=
  innerWidth``).

The chips are produced by a Liquid include, so this guard needs the real site:
it uses the session-wide `built_site`/`built_site_url` fixtures from
`conftest.py` (one `bundle exec jekyll build` for the whole suite, served over
loopback HTTP). The dev environment is used on purpose (no external giscus
embed) and third-party requests are aborted, keeping the run hermetic - the
local `style.css` fully defines the layout.

Known, separately tracked overflow: this base (#48's branch, so master) still
has the `#50` image regression - `img { max-width: 100%; padding: 20px }` uses
content-box sizing, so a full-width image is `100% + 40px` wide and the
document scrolls ~22px sideways at 375px on any page showing one. That fix
belongs to PR #51 (`_sass/minima/_base.scss`) and is explicitly out of this
change's scope, so the document assertion here allows exactly the *measured*
image overhang and tightens to `scrollWidth <= innerWidth` on its own as soon
as the images stop overhanging. Chip overflow itself is asserted exactly, per
chip, with no allowance.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_PAGES_DIR = REPO_ROOT / "tags"
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"

PHONE_WIDTH = 375
TAG_HREF_RE = re.compile(r"^/tags/([a-z0-9-]+)/$")

# `document.documentElement` must not be wider than the viewport, and every
# chip must sit inside it (a chip that overflows horizontally is the phone
# regression this guard exists for).
_MEASURE_JS = """
() => {
  const vw = window.innerWidth;
  const items = [];
  for (const li of document.querySelectorAll('.post-list > li')) {
    const link = li.querySelector('a.post-link');
    const chips = [];
    for (const el of li.querySelectorAll('a.tag-chip')) {
      const rect = el.getBoundingClientRect();
      const list = el.closest('.tag-chip-list');
      chips.push({
        text: (el.textContent || '').trim(),
        href: el.getAttribute('href'),
        left: rect.left,
        right: rect.right,
        width: rect.width,
        flexWrap: list ? getComputedStyle(list).flexWrap : null,
      });
    }
    items.push({
      title: link ? (link.textContent || '').trim() : null,
      url: link ? link.getAttribute('href') : null,
      chips: chips,
    });
  }
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: vw,
    imageOverhang: Array.from(document.querySelectorAll('img')).reduce(
      (worst, el) => Math.max(worst, el.getBoundingClientRect().right - vw), 0
    ),
    items: items,
  };
}
"""

# Style of the chip itself, to prove the home list reuses the sidebar chip
# instead of a look-alike.
_CHIP_STYLE_JS = """
() => {
  const el = document.querySelector('a.tag-chip');
  if (!el) return null;
  const cs = getComputedStyle(el);
  return {
    fontSize: cs.fontSize,
    padding: cs.paddingTop + ' ' + cs.paddingRight + ' ' + cs.paddingBottom + ' ' + cs.paddingLeft,
    borderRadius: cs.borderRadius,
    borderWidth: cs.borderTopWidth,
    color: cs.color,
  };
}
"""


@pytest.fixture(scope="session")
def home_url(built_site_url):
    """Point at the home list of the session's one served build."""
    return built_site_url.rstrip("/") + "/"


@pytest.fixture()
def page(browser):
    context = browser.new_context(
        viewport={"width": PHONE_WIDTH, "height": 800},
        device_scale_factor=1,
    )
    browser_page = context.new_page()
    # Only the site's own styles decide the layout here; aborting
    # third-party requests keeps the run offline-safe.
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


def _measure(page, home_url):
    page.goto(home_url, wait_until="load")
    page.locator(".post-list").wait_for(state="visible", timeout=10_000)
    return page.evaluate(_MEASURE_JS)


def _chips(page, home_url, path):
    page.goto(f"{home_url.rstrip('/')}{path}", wait_until="load")
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('a.tag-chip')).map(
               (el) => (el.textContent || '').trim() + ' ' + el.getAttribute('href')
           )"""
    )


def test_home_list_shows_the_same_chips_as_the_post_page(page, home_url):
    """Every chip on the list is the post's own tag, as the post page shows it."""
    result = _measure(page, home_url)
    assert result["items"], "the home list should not be empty"
    assert any(item["chips"] for item in result["items"]), (
        "no tag chips rendered on the home post list"
    )

    for item in result["items"]:
        chips = [f"{chip['text']} {chip['href']}" for chip in item["chips"]]
        page_chips = _chips(page, home_url, item["url"])
        assert chips == page_chips, (
            f"home list chips for {item['title']!r} ({chips}) do not match the "
            f"post page chips ({page_chips})"
        )


def test_home_chips_link_to_tag_pages_that_exist_in_the_build(page, home_url, built_site):
    result = _measure(page, home_url)
    chips = [chip for item in result["items"] for chip in item["chips"]]
    assert chips, "no chips measured on the home list"

    for chip in chips:
        match = TAG_HREF_RE.match(chip["href"] or "")
        assert match, f"unexpected chip href: {chip['href']}"
        tag = match.group(1)
        # The chip label is the tag itself, as on the post sidebar (#45).
        assert chip["text"] == tag, f"chip label {chip['text']!r} does not match {tag}"

        # The source page (#46) still declares that tag...
        assert (TAG_PAGES_DIR / f"{tag}.md").is_file(), (
            f"chip links to /tags/{tag}/ but tags/{tag}.md does not exist"
        )
        # ...and the built tag page is really there and served.
        assert (built_site / "tags" / tag / "index.html").is_file(), (
            f"/tags/{tag}/ is missing from the build"
        )
        response = page.request.get(f"{home_url}tags/{tag}/")
        assert response.status == 200, f"/tags/{tag}/ returned {response.status}"


def test_home_chips_reuse_the_post_sidebar_chip_style(page, home_url):
    result = _measure(page, home_url)
    first_chip = next(
        (item for item in result["items"] if item["chips"]), None
    )
    assert first_chip, "no chips measured on the home list"

    assert [chip["flexWrap"] for chip in first_chip["chips"]] == ["wrap"] * len(
        first_chip["chips"]
    ), "the chip list must wrap on phones"

    home_style = page.evaluate(_CHIP_STYLE_JS)
    page.goto(f"{home_url.rstrip('/')}{first_chip['url']}", wait_until="load")
    sidebar_style = page.evaluate(_CHIP_STYLE_JS)

    assert home_style is not None and sidebar_style is not None
    assert home_style == sidebar_style, (
        "the home list chip must look exactly like the post sidebar chip: "
        f"{home_style} != {sidebar_style}"
    )


@pytest.mark.parametrize("width", [360, 375])
def test_home_list_does_not_scroll_sideways_at_phone_widths(page, home_url, width):
    page.set_viewport_size({"width": width, "height": 800})
    result = _measure(page, home_url)

    assert result["innerWidth"] == width

    # Chips must never be the reason the page scrolls sideways: bounded
    # exactly, at the pixel, against the viewport.
    for item in result["items"]:
        for chip in item["chips"]:
            assert chip["right"] <= result["innerWidth"] + 0.5, (
                f"chip {chip['text']!r} overhangs the viewport at {width}px: right "
                f"{chip['right']} > innerWidth {result['innerWidth']}"
            )
            assert chip["left"] >= -0.5, f"chip {chip['text']!r} starts off-screen"
            assert chip["flexWrap"] == "wrap", "chips must wrap, not widen the list"

    # Document-level overflow: allowed only up to the pre-existing `#50` image
    # overhang (PR #51 owns the fix). Zero when no image overhangs, which is
    # what the assertion becomes once #51 lands.
    allowed = max(0.0, result["imageOverhang"]) + 0.5
    assert result["scrollWidth"] <= result["innerWidth"] + allowed, (
        f"home list overflows at {width}px: scrollWidth {result['scrollWidth']} > "
        f"innerWidth {result['innerWidth']} (+{allowed} allowed for the tracked "
        f"#50 image overhang of {result['imageOverhang']}px)"
    )


@pytest.mark.static
def test_home_layout_renders_the_chips_from_the_shared_include():
    """Static backstop: no forked chip markup in the home layout."""
    html = HOME_LAYOUT.read_text(encoding="utf-8")
    assert (
        '{%- include post-tags.html tags=post.tags class="tag-chip-list--home" -%}' in html
    )
    assert 'class="tag-chip"' not in html
    assert "'/tags/' | append" not in html
