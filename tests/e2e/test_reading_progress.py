"""Guards for #224: reading progress bar + back-to-top button on post pages.

Long posts (16-18 ``<h2>`` sections) had no reading cue and no way back to
the top (UX audit #112, remainder after the #134 TOC). ``_layouts/post.html``
now ships a thin fixed progress bar (0-100% width + ``aria-valuenow``)
and a back-to-top pill past ~600px of scroll, both ``hidden`` in the markup
so readers without JS render neither; ``assets/js/reading-progress.js``
reveals the bar and drives both at runtime. Labels follow the page language
(``Reading progress`` / ``Tiến độ đọc``, ``Back to top`` / ``Về đầu trang``);
``prefers-reduced-motion`` jumps instantly instead of smooth-scrolling.

Guarded here:

- the markup lives in the post layout only, ``hidden`` up front, localized
  per page language (static + built);
- the script stays a tiny dependency-free first-party asset that tracks
  scroll 0-100% (full/complete on short pages, no divide-by-zero), shows
  the button past ~600px, scrolls smooth unless reduced motion says
  otherwise, and no-ops off post pages (static);
- the script is linked through the ``?v=`` build token like every other
  fixed-URL asset (#61) (static + rendered);
- the styles float both controls above the page (no in-flow box, reserved
  nothing, transparent track so the at-rest bar paints zero pixels), keep
  44px targets with visible keyboard focus and ``prefers-reduced-motion``
  handling (static);
- browser (needs Ruby + a browser): scroll a long EN post, assert progress
  advances and the button appears, activate it, assert top reached; the
  same flow localized on a long VI post at phone width; smooth vs instant
  scrolling under normal vs reduced motion; keyboard focusability with a
  visible focus; short pages complete without errors; with JS disabled
  neither control renders.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
SCRIPT = REPO_ROOT / "assets" / "js" / "reading-progress.js"
PARTIAL = REPO_ROOT / "_sass" / "minima" / "custom" / "_reading-progress.scss"
STYLES_INDEX = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"

SCRIPT_PATH = "/assets/js/reading-progress.js"

# Same budget as the share script: a tiny first-party asset fetched with
# every page load.
MAX_SCRIPT_BYTES = 4096
MAX_SCRIPT_CODE_LINES = 100

# The button must appear only after real scrolling.
SHOW_AFTER_PX = 600

PROGRESS_EN = "Reading progress"
PROGRESS_VI = "Tiến độ đọc"
TOP_EN = "Back to top"
TOP_VI = "Về đầu trang"

# Long EN/VI twins (16 `<h2>` sections each): scrollable at every viewport.
EN_LONG_POST = "/2022/12/25/explaining-the-internet.html"
VI_LONG_POST = "/vi/2022/12/25/gioi-thieu-ve-internet.html"
# A shorter EN/VI pair for the no-JS/at-rest built guards.
EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _code_lines(text):
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_controls_live_in_the_post_layout_only():
    """Progress + button render on post pages, nowhere else, hidden upfront."""
    layout = _read(POST_LAYOUT)
    assert "reading-progress" in layout and "back-to-top" in layout, (
        "the post layout must render the progress bar and the button"
    )
    for needle in (
        'class="reading-progress" hidden',
        'class="reading-progress__bar"',
        'class="back-to-top" hidden',
    ):
        assert needle in layout, (
            f"the post layout must ship `{needle}`: without JS neither "
            "control may render (#224)"
        )
    for template in sorted((REPO_ROOT / "_layouts").glob("*.html")):
        if template.name == "post.html":
            continue
        text = _read(template)
        assert "reading-progress" not in text and "back-to-top" not in text, (
            f"{template.relative_to(REPO_ROOT)} must not render the "
            "controls: post pages only (#224)"
        )


@pytest.mark.static
def test_the_control_labels_are_localized():
    """Bar name and button text follow the page language."""
    layout = _read(POST_LAYOUT)
    for label in (PROGRESS_EN, PROGRESS_VI, TOP_EN, TOP_VI):
        assert label in layout, f"the layout never renders the label {label!r}"
    assert "page.lang | default: site.lang" in layout, (
        "the labels must be derived from the page language, like `post_lang`"
    )
    assert 'role="progressbar"' in layout, (
        "the bar must expose progressbar semantics"
    )
    for attr in ("aria-valuemin", "aria-valuemax", "aria-valuenow", "aria-label"):
        assert attr in layout, (
            f"the progressbar must carry {attr} (named 0-100 range)"
        )


@pytest.mark.static
def test_the_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the script ships on every page load: keep it under "
        f"{MAX_SCRIPT_BYTES} bytes"
    )
    assert len(_code_lines(text)) <= MAX_SCRIPT_CODE_LINES, (
        "the script grows past its budget"
    )
    assert "import " not in text and "require(" not in text, (
        "the script must not depend on anything"
    )


@pytest.mark.static
def test_the_script_tracks_scroll_and_threshold():
    """0-100% with a short-page complete state; ~600px button threshold."""
    text = _read(SCRIPT)
    assert "scrollHeight" in text and "innerHeight" in text, (
        "progress must be computed from the scrollable range"
    )
    assert "aria-valuenow" in text and "style.width" in text, (
        "the script must publish progress as bar width + `aria-valuenow`"
    )
    assert str(SHOW_AFTER_PX) in text, (
        f"the button must appear only past ~{SHOW_AFTER_PX}px of scroll"
    )
    assert re.search(r"max\s*>\s*0", text), (
        "pages shorter than the viewport must report complete (100%) "
        "instead of dividing by zero"
    )
    assert ".reading-progress" in text and ".back-to-top" in text, (
        "the script must scope itself to the post controls"
    )
    assert "if (!track" in text or "if(!track" in text, (
        "off post pages (no controls) the script must no-op"
    )


@pytest.mark.static
def test_the_script_respects_reduced_motion():
    """Smooth scroll normally, instant jump under reduced motion."""
    text = _read(SCRIPT)
    assert "prefers-reduced-motion" in text, (
        "the script must read the reduced-motion preference"
    )
    assert "smooth" in text and "'auto'" in text, (
        "activation must smooth-scroll normally and jump instantly when "
        "the reader asked for reduced motion"
    )
    assert "scrollTo" in text, "activation must return to the top"


@pytest.mark.static
def test_the_script_is_linked_with_the_cache_version_token():
    """A fixed-URL asset must carry the build token (#61)."""
    html = _read(SUB_FOOTER)
    assert f"{SCRIPT_PATH}?v=" in html, (
        f"{SUB_FOOTER.relative_to(REPO_ROOT)} must link {SCRIPT_PATH} with "
        "the `?v=` build token, like every other fixed-URL asset (#61)"
    )
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER)), (
        "the version token must be derived from the build"
    )


@pytest.mark.static
def test_the_partial_joins_the_cascade_before_legibility():
    assert PARTIAL.is_file(), f"{PARTIAL.relative_to(REPO_ROOT)} is missing"
    index = _read(STYLES_INDEX)
    assert "minima/custom/reading-progress" in index, (
        "the partial must be imported from custom-styles.scss "
        "(#174 cascade index)"
    )
    assert index.index("minima/custom/reading-progress") < index.index(
        "minima/custom/legibility"
    ), (
        "the partial must stay before the legibility partial, like the "
        "other post enhancement (#223 lightbox)"
    )


@pytest.mark.static
def test_the_styles_float_shift_nothing_and_stay_usable():
    """Fixed, transparent at rest, 44px targets, reduced-motion aware."""
    scss = _read(PARTIAL)
    assert ".reading-progress[hidden]" in scss, (
        "the `hidden` attribute must win so no-JS readers see no bar"
    )
    assert ".back-to-top[hidden]" in scss, (
        "the `hidden` attribute must win so pre-threshold and no-JS "
        "readers are never offered a dead control"
    )
    assert scss.count("position: fixed") >= 2, (
        "both controls must float above the page, never in its flow "
        "(no layout shift)"
    )
    assert "background: transparent" in scss, (
        "the bar track must be transparent: at 0% width it paints zero "
        "pixels, so the #208 post baselines stay byte-identical"
    )
    assert "pointer-events: none" in scss, (
        "the bar must never intercept taps aimed at the page"
    )
    assert "min-width: 44px" in scss and "min-height: 44px" in scss, (
        "the back-to-top button must keep a 44px minimum touch target"
    )
    assert "prefers-reduced-motion" in scss, (
        "the styles must pin no-transition behavior for reduced-motion "
        "readers"
    )
    assert "button:focus-visible" in conftest.custom_styles_text(), (
        "the button keeps its visible keyboard focus through the global "
        "#87 rule — no local override may drop it"
    )


# --- built-HTML guards (need the real `jekyll build`, no browser) ---------


def _post_html(built_site, rel):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {page}"
    return _read(page)


def test_the_built_posts_render_localized_hidden_controls(built_site):
    en = _post_html(built_site, EN_POST_REL)
    assert f'aria-label="{PROGRESS_EN}"' in en
    assert f">{TOP_EN}<" in en and TOP_VI not in en

    vi = _post_html(built_site, VI_POST_REL)
    assert f'aria-label="{PROGRESS_VI}"' in vi
    assert f">{TOP_VI}<" in vi and f">{TOP_EN}<" not in vi

    for html in (en, vi):
        assert 'class="reading-progress" hidden' in html
        assert 'class="back-to-top" hidden' in html
        assert 'role="progressbar"' in html


def test_no_controls_leave_the_post_pages(built_site):
    """Home, tag and static pages stay control-free."""
    pages = ["index.html", "vi/index.html", "tags/index.html"]
    pages.extend(
        path.relative_to(built_site).as_posix()
        for path in sorted(built_site.glob("tags/*/index.html"))[:1]
    )
    pages.extend(["about/index.html", "portfolio/index.html"])
    for page in pages:
        assert (built_site / page).is_file(), f"{page} is missing"
        html = _read(built_site / page)
        assert 'class="reading-progress"' not in html, (
            f"{page} renders the progress bar: post pages only (#224)"
        )
        assert 'class="back-to-top"' not in html, (
            f"{page} renders the back-to-top button: post pages only (#224)"
        )


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    text = _post_html(built_site, EN_POST_REL)
    match = re.search(
        r'<script src="(/assets/js/reading-progress\.js\?v=([^"]+))"', text
    )
    assert match, "the post page does not link the reading-progress script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


# --- browser guards (need Ruby + a browser) ---------------------------------


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


def _bar_width(page):
    return page.locator(".reading-progress__bar").evaluate(
        "el => el.style.width"
    )


def _bar_value(page):
    return page.locator(".reading-progress__bar").get_attribute(
        "aria-valuenow"
    )


def test_scroll_advances_progress_and_reveals_the_button(built_site_url, page):
    """Long EN post: progress grows, the button appears past ~600px."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.wait_for_selector(".reading-progress:not([hidden])", timeout=10_000)
    assert _bar_width(page) == "0%"
    assert _bar_value(page) == "0"
    assert page.get_by_role("button", name=TOP_EN).count() == 0, (
        "the button must stay out of reach before the scroll threshold"
    )

    page.evaluate(f"window.scrollTo(0, {SHOW_AFTER_PX + 200})")
    page.wait_for_function(
        "() => !document.querySelector('.back-to-top').hidden",
        timeout=10_000,
    )
    mid_width = _bar_width(page)
    assert mid_width not in ("", "0%"), (
        "scrolling down must advance the progress bar"
    )
    assert page.get_by_role("button", name=TOP_EN).count() == 1

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function(
        "() => document.querySelector("
        "'.reading-progress__bar').getAttribute('aria-valuenow') === '100'",
        timeout=10_000,
    )
    assert _bar_width(page) == "100%"


def test_activating_the_button_returns_to_the_top(built_site_url, page):
    """Click scrolls back to 0 and the button hides again."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_selector(".back-to-top:not([hidden])", timeout=10_000)

    page.get_by_role("button", name=TOP_EN).click()
    page.wait_for_function("() => window.scrollY === 0", timeout=10_000)
    assert _bar_width(page) == "0%"
    assert page.locator(".back-to-top").is_hidden(), (
        "back at the top, the button must hide again"
    )


def test_vietnamese_post_at_phone_width(built_site_url, browser):
    """Same flow localized on the VI twin: labels, targets, no overflow."""
    context = browser.new_context(viewport={"width": 375, "height": 800})
    try:
        origin = urlparse(built_site_url).netloc
        narrow = context.new_page()
        narrow.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        narrow.goto(
            built_site_url.rstrip("/") + VI_LONG_POST, wait_until="load"
        )
        narrow.wait_for_selector(
            ".reading-progress:not([hidden])", timeout=10_000
        )
        assert narrow.get_by_role("button", name=TOP_VI).count() == 0
        assert narrow.get_by_role("button", name=TOP_EN).count() == 0

        narrow.evaluate(
            f"window.scrollTo(0, {SHOW_AFTER_PX + 200})"
        )
        narrow.wait_for_function(
            "() => !document.querySelector('.back-to-top').hidden",
            timeout=10_000,
        )
        button = narrow.get_by_role("button", name=TOP_VI)
        assert button.count() == 1
        box = button.first.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, (
            "the button must keep a 44px minimum touch target, got "
            f"{box['width']:.0f}x{box['height']:.0f}"
        )
        button.first.focus()
        outline = narrow.evaluate(
            "() => { const s = getComputedStyle("
            "document.querySelector('.back-to-top')); "
            "return {style: s.outlineStyle, width: s.outlineWidth}; }"
        )
        assert outline["style"] != "none" and outline["width"] != "0px", (
            f"keyboard focus on the button must stay visible, got {outline}"
        )

        button.first.click()
        narrow.wait_for_function("() => window.scrollY === 0", timeout=10_000)
        overflow = narrow.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 0, (
            f"the controls must not add horizontal overflow at 375px "
            f"(+{overflow}px)"
        )
    finally:
        context.close()


def _capture_scroll_behavior(page):
    page.evaluate(
        """() => {
          window.__scrollBehavior = 'unset';
          const orig = window.scrollTo.bind(window);
          window.scrollTo = function (a, b) {
            window.__scrollBehavior =
              (a && typeof a === 'object' && a.behavior) || 'unset';
            return orig(a, b);
          };
        }"""
    )


def test_activation_smooth_scrolls_by_default(built_site_url, page):
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_selector(".back-to-top:not([hidden])", timeout=10_000)
    _capture_scroll_behavior(page)
    page.evaluate("window.__scrollBehavior = 'unset'")
    page.get_by_role("button", name=TOP_EN).click()
    page.wait_for_function(
        "() => window.__scrollBehavior !== 'unset'", timeout=10_000
    )
    assert page.evaluate("() => window.__scrollBehavior") == "smooth"
    page.wait_for_function("() => window.scrollY === 0", timeout=10_000)


def test_activation_jumps_instantly_with_reduced_motion(
    built_site_url, page
):
    page.emulate_media(reduced_motion="reduce")
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_selector(".back-to-top:not([hidden])", timeout=10_000)
    _capture_scroll_behavior(page)
    page.evaluate("window.__scrollBehavior = 'unset'")
    page.get_by_role("button", name=TOP_EN).click()
    page.wait_for_function(
        "() => window.__scrollBehavior !== 'unset'", timeout=10_000
    )
    assert page.evaluate("() => window.__scrollBehavior") == "auto"
    page.wait_for_function("() => window.scrollY === 0", timeout=10_000)


def test_keyboard_activation_returns_to_the_top(built_site_url, page):
    """Tab-reached button + Enter is a one-keypress way back up."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_selector(".back-to-top:not([hidden])", timeout=10_000)
    button = page.get_by_role("button", name=TOP_EN)
    button.first.focus()
    assert page.evaluate(
        "() => document.activeElement === "
        "document.querySelector('.back-to-top')"
    ), "the revealed button must be keyboard-focusable"
    page.keyboard.press("Enter")
    page.wait_for_function("() => window.scrollY === 0", timeout=10_000)


def test_short_pages_report_complete_without_errors(built_site_url, page):
    """No scroll range: the bar completes instead of dividing by zero."""
    page.goto(
        built_site_url.rstrip("/") + "/" + EN_POST_REL.as_posix(),
        wait_until="load",
    )
    page.wait_for_selector(".reading-progress:not([hidden])", timeout=10_000)
    # Shrink the article below the viewport so the page has no scroll range,
    # then nudge the script the way a real resize would. The sidebar is
    # hidden too: since #386 it holds Tags plus Related and Latest, which
    # alone can exceed the viewport and keep a scroll range on their own.
    page.evaluate(
        """() => {
          document.querySelector('.post-content').innerHTML = '<p>Short.</p>';
          const aside = document.querySelector('.post-sidebar');
          if (aside) { aside.style.display = 'none'; }
          window.dispatchEvent(new Event('resize'));
        }"""
    )
    page.wait_for_function(
        "() => document.querySelector("
        "'.reading-progress__bar').getAttribute('aria-valuenow') === '100'",
        timeout=10_000,
    )
    assert _bar_width(page) == "100%"
    assert page.locator(".back-to-top").is_hidden(), (
        "a page with no scroll range must never offer the button"
    )


def test_without_js_neither_control_renders(built_site_url, browser):
    """No-JS readers get the unchanged page: both controls stay hidden."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        plain.goto(
            built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load"
        )
        assert plain.locator(".reading-progress").count() == 1
        assert plain.locator(".reading-progress").is_hidden()
        assert plain.locator(".back-to-top").count() == 1
        assert plain.locator(".back-to-top").is_hidden()
        assert plain.get_by_role("button", name=TOP_EN).count() == 0, (
            "without JS the button must stay out of the tab order"
        )
        assert plain.locator(
            ".reading-progress__bar"
        ).evaluate("el => el.style.width") in ("", "0px"), (
            "without JS the bar must never show partial progress"
        )
    finally:
        context.close()
