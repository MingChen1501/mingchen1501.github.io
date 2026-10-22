"""Guards for #114: the mobile nav is an operable disclosure and no `<summary>`
nests interactive content.

Findings (reader audit at 375px): the mobile menu used a CSS-only
checkbox + `<label>` hack with no accessible name, so keyboard and
screen-reader users could not open it; and the sidebar tag rows nested tag-chip
`<a>` elements inside `<summary>`, which is invalid and breaks keyboard/AT
behaviour.

Guarded here:

- the header renders a real `<button class="nav-toggle">` with an accessible
  name plus `aria-expanded`/`aria-controls` wired to the menu panel (static);
- the old checkbox/label pattern is gone from the markup and the styles
  (static);
- `assets/js/nav-toggle.js` exists, stays tiny and dependency-free, opens the
  panel only on reader action, closes it on Escape while returning focus,
  and re-syncs `aria-expanded` across breakpoint crossings (static);
- the `no-js`/`js` progressive-enhancement hook flips before first paint and
  CSS hides the phone panel only under `html.js` (static + browser);
- the header markup ships the panel collapsed (`aria-expanded="false"` +
  `hidden`) so a JS first paint never flashes it open, while no-JS readers
  keep the full menu with working links (static + browser);
- the script is linked with the `?v=` build token like every other fixed-URL
  asset (#61) (static + rendered);
- no `<summary>` in the built pages contains a link (browser, EN + VI, home
  and tag pages);
- at 375px the toggle opens with keyboard (Enter/Space), Tab reaches the menu
  links, and Escape closes the menu and returns focus (browser);
- on desktop the toggle stays hidden and the menu is simply shown (browser).

The browser guards use the session's shared `built_site`/`built_site_url`
fixtures from `conftest.py` (one `bundle exec jekyll build` for the whole
suite, served once over loopback HTTP), exactly like the #47/#58 guards.
Third-party requests are aborted — the local `style.css` fully defines the
layout.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_INCLUDE = REPO_ROOT / "_includes" / "header.html"
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
BASE_LAYOUT = REPO_ROOT / "_layouts" / "base.html"
NAV_ITEMS_INCLUDE = REPO_ROOT / "_includes" / "nav-items.html"
SUB_FOOTER_INCLUDE = REPO_ROOT / "_includes" / "sub-footer.html"
NAV_SCRIPT = REPO_ROOT / "assets" / "js" / "nav-toggle.js"
NAV_LAYOUT = REPO_ROOT / "_sass" / "minima" / "_layout.scss"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
TAG_PAGES_DIR = REPO_ROOT / "tags"
VI_TAG_PAGES_DIR = REPO_ROOT / "vi" / "tags"

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280

TAG_PAGE = f"/tags/{sorted(path.stem for path in TAG_PAGES_DIR.glob('*.md'))[0]}/"
VI_TAG_PAGE = f"/vi/tags/{sorted(path.stem for path in VI_TAG_PAGES_DIR.glob('*.md'))[0]}/"

# The script is a few dozen lines of plain DOM code; keep it that way.
MAX_SCRIPT_BYTES = 2048
MAX_SCRIPT_CODE_LINES = 40


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------

EXPECTED_PANEL_ID = "nav-menu"


@pytest.mark.static
def test_mobile_nav_uses_a_button_disclosure_with_an_accessible_name():
    html = _read(HEADER_INCLUDE)
    assert 'class="site-nav"' in html
    assert 'aria-label=' in html
    match = re.search(r'<button[^>]*class="nav-toggle"[^>]*>', html)
    assert match, "the mobile menu trigger must be a real <button>"
    attrs = match.group(0)
    assert 'class="nav-toggle"' in attrs
    assert 'type="button"' in attrs
    assert 'aria-expanded=' in attrs
    assert f'aria-controls="{EXPECTED_PANEL_ID}"' in attrs
    # Icon-only button: the accessible name comes from the label.
    assert 'aria-label="Menu"' in attrs
    assert 'aria-hidden="true"' in html
    # The unreachable checkbox + label hack is gone (#114 root cause).
    markup = re.sub(r"\{%-?\s*comment.*?endcomment\s*-?%\}", "", html, flags=re.S)
    assert "nav-trigger" not in markup
    assert 'type="checkbox"' not in markup
    assert "<label" not in markup


@pytest.mark.static
def test_nav_panel_id_matches_the_toggle():
    html = _read(NAV_ITEMS_INCLUDE)
    assert f'id="{EXPECTED_PANEL_ID}"' in html
    header = _read(HEADER_INCLUDE)
    assert f'aria-controls="{EXPECTED_PANEL_ID}"' in header


@pytest.mark.static
def test_nav_styles_toggle_the_panel_without_the_checkbox_hack():
    scss = _read(NAV_LAYOUT)
    assert ".nav-toggle" in scss
    assert "[hidden]" in scss
    assert "aria-expanded" in scss
    assert "#nav-trigger" not in scss
    assert 'label[for="nav-trigger"]' not in scss
    assert 'label[for=nav-trigger]' not in scss


@pytest.mark.static
def test_no_summary_in_the_header_and_no_links_in_any_summary():
    assert "<summary" not in _read(HEADER_INCLUDE)
    sidebar = _read(SIDEBAR_INCLUDE)
    summaries = re.findall(r"<summary.*?</summary>", sidebar, re.S)
    assert summaries, "the sidebar tag rows must keep their summary elements"
    for summary in summaries:
        assert "<a " not in summary


@pytest.mark.static
def test_the_nav_toggle_script_exists_and_stays_tiny():
    assert NAV_SCRIPT.is_file(), f"{NAV_SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(NAV_SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the nav toggle script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the nav toggle script has {len(code)} code lines, expected at most "
        f"{MAX_SCRIPT_CODE_LINES}"
    )
    assert "import " not in text and "require(" not in text, (
        "the nav toggle script must not depend on anything"
    )
    # The four behaviours the browser guards pin: shipped-collapsed state,
    # click toggling, Escape-to-close with focus back on the trigger, and
    # breakpoint-crossing re-sync.
    assert "aria-expanded" in text
    assert "hidden" in text
    assert "Escape" in text
    assert ".focus()" in text
    assert "resize" in text


@pytest.mark.static
def test_the_nav_script_is_linked_with_the_cache_version_token():
    """A fixed-URL asset must carry the build token (#61)."""
    html = _read(SUB_FOOTER_INCLUDE)
    assert "/assets/js/nav-toggle.js?v=" in html, (
        "sub-footer.html must link nav-toggle.js with the `?v=` build token, "
        "like every other fixed-URL asset (#61)"
    )
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER_INCLUDE)), (
        "the version token must be derived from the build"
    )


@pytest.mark.static
def test_focus_stays_visible_on_the_toggle():
    """#87's focus rule covers buttons, so the disclosure never goes dark."""
    assert "button:focus-visible" in conftest.custom_styles_text()


@pytest.mark.static
def test_nav_markup_ships_collapsed():
    """#384: the toggle ships `aria-expanded="false"` and the panel `hidden`,
    so a JS first paint never flashes the menu open (no closing snap needed)."""
    header = _read(HEADER_INCLUDE)
    match = re.search(r'<button[^>]*class="nav-toggle"[^>]*>', header)
    assert match, "the mobile menu trigger must be a real <button>"
    assert 'aria-expanded="false"' in match.group(0)
    assert 'id="nav-menu" hidden' in _read(NAV_ITEMS_INCLUDE)


@pytest.mark.static
def test_no_js_hook_flips_to_js_before_first_paint():
    """#384: `<html class="no-js">` plus a tiny blocking flip ahead of the
    stylesheet, so CSS can gate the phone panel on `html.js` from paint one."""
    base = _read(BASE_LAYOUT)
    assert re.search(r'<html[^>]*class="no-js"', base), (
        "base.html must ship `<html class=\"no-js\">` for the #384 hook"
    )
    head = _read(HEAD_INCLUDE)
    tags = re.findall(r"<script[^>]*>.*?</script>", head, re.S)
    flips = [tag for tag in tags if "no-js" in tag and "src=" not in tag.split(">", 1)[0]]
    assert len(flips) == 1, "head.html must flip `no-js` to `js` exactly once"
    tag = flips[0]
    assert "documentElement" in tag and '"js"' in tag
    inner = tag.split(">", 1)[1].rsplit("<", 1)[0]
    assert len(inner.encode("utf-8")) < 200, "the flip must stay tiny and blocking"
    opener = tag.split(">", 1)[0]
    assert "defer" not in opener and "async" not in opener, (
        "the flip must run before first paint, never deferred"
    )
    assert head.index(tag) < head.index('id="main-stylesheet"'), (
        "the flip must run before the stylesheet paints"
    )


@pytest.mark.static
def test_panel_hides_only_under_html_js_on_phones():
    """#384: CSS hides the phone panel only when JS ran (`html.js`); no-JS
    readers match `html.no-js` and keep the full menu with no script."""
    scss = _read(NAV_LAYOUT)
    assert re.search(r"html\.js\s+&\[hidden\]\s*\{\s*display:\s*none", scss), (
        "the phone panel must hide under `html.js` only"
    )
    assert re.search(r"html\.no-js\s+&\[hidden\]", scss), (
        "the phone panel must re-show under `html.no-js`"
    )
    assert len(re.findall(r"&\[hidden\]", scss)) == 2, (
        "no unscoped `[hidden]` hide may leak into the phone panel styles"
    )


def test_the_rendered_nav_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    text = _read(built_site / "index.html")
    match = re.search(r'<script src="(/assets/js/nav-toggle\.js\?v=([^"]+))"', text)
    assert match, "the home page does not link the nav toggle script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


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
    page.wait_for_selector(".site-nav", state="attached", timeout=10_000)
    return page


@pytest.mark.parametrize("path", ["/", "/vi/", TAG_PAGE, VI_TAG_PAGE])
def test_no_summary_contains_links_in_the_build(path, built_site_url, browser):
    """#114: no nested interactive content inside any `<summary>`."""
    for page in _viewport(browser, built_site_url, PHONE_WIDTH):
        _open(page, built_site_url, path)
        summaries = page.evaluate(
            "() => Array.from(document.querySelectorAll('summary')).map("
            "(el) => ({links: el.querySelectorAll('a').length, "
            "text: (el.textContent || '').trim().slice(0, 60)}))"
        )
        assert summaries, f"{path}: no <summary> rendered to judge"
        for summary in summaries:
            assert summary["links"] == 0, (
                f"{path}: <summary {summary['text']!r}...> nests "
                f"{summary['links']} link(s)"
            )


@pytest.mark.parametrize("path", ["/", "/vi/", TAG_PAGE, VI_TAG_PAGE])
def test_mobile_menu_is_keyboard_operable(path, built_site_url, browser):
    """#114: Tab to the trigger, Enter/Space opens, Tab reaches links,
    Escape closes and focus returns to the trigger."""
    for page in _viewport(browser, built_site_url, PHONE_WIDTH):
        _open(page, built_site_url, path)
        toggle = page.get_by_role("button", name="Menu")
        assert toggle.count() == 1, (
            f"{path}: the mobile trigger must expose the accessible name "
            "'Menu' (it has none)"
        )
        assert toggle.is_visible(), f"{path}: the trigger is not visible at 375px"
        # Collapsed by default once the disclosure script runs.
        page.wait_for_function(
            "() => document.querySelector('.nav-toggle')"
            ".getAttribute('aria-expanded') === 'false'",
            timeout=10_000,
        )
        panel = page.locator(f"#{EXPECTED_PANEL_ID}")
        assert panel.is_hidden(), f"{path}: the menu panel must start collapsed"

        # Keyboard: focus the trigger, Enter opens.
        toggle.focus()
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-expanded") == "true"
        assert panel.is_visible(), f"{path}: Enter did not open the menu"
        links = panel.locator(".nav-item")
        assert links.count() > 0, f"{path}: the menu holds no links"
        assert links.first.is_visible()

        # Tab moves from the trigger into the first menu link.
        page.keyboard.press("Tab")
        focused = page.evaluate(
            "() => ({tag: document.activeElement.tagName, "
            "href: document.activeElement.getAttribute('href')})"
        )
        assert focused["tag"] == "A", (
            f"{path}: Tab from the trigger did not reach a menu link: {focused}"
        )

        # Escape closes and returns focus to the trigger.
        page.keyboard.press("Escape")
        assert toggle.get_attribute("aria-expanded") == "false"
        assert panel.is_hidden(), f"{path}: Escape did not close the menu"
        assert page.evaluate("() => document.activeElement === "
                             "document.querySelector('.nav-toggle')"), (
            f"{path}: Escape did not return focus to the trigger"
        )

        # Space opens too (native button behaviour through the same wiring).
        page.keyboard.press(" ")
        assert toggle.get_attribute("aria-expanded") == "true"
        assert panel.is_visible(), f"{path}: Space did not open the menu"


@pytest.mark.parametrize("path", ["/", "/vi/"])
def test_mobile_menu_never_paints_open(path, built_site_url, browser):
    """#384: at 375px the panel is shut from paint one — `html.js` is set
    before the stylesheet and the panel ships `hidden`, so no closing snap."""
    for page in _viewport(browser, built_site_url, PHONE_WIDTH):
        _open(page, built_site_url, path)
        assert page.evaluate(
            "document.documentElement.classList.contains('js')"
        ), f"{path}: the `no-js` hook must flip before first paint"
        toggle = page.locator(".nav-toggle")
        assert toggle.get_attribute("aria-expanded") == "false"
        panel = page.locator(f"#{EXPECTED_PANEL_ID}")
        assert panel.is_hidden(), f"{path}: the menu panel must never paint open"
        box = panel.bounding_box()
        assert box is None or box["height"] == 0


@pytest.mark.parametrize("path", ["/", "/vi/"])
def test_resize_keeps_aria_in_sync_with_the_visible_panel(path, built_site_url, browser):
    """#384: crossing the nav breakpoint never leaves `aria-expanded`
    contradicting the visible panel."""
    for page in _viewport(browser, built_site_url, PHONE_WIDTH):
        _open(page, built_site_url, path)
        toggle = page.locator(".nav-toggle")
        panel = page.locator(f"#{EXPECTED_PANEL_ID}")
        assert toggle.get_attribute("aria-expanded") == "false"
        page.set_viewport_size({"width": DESKTOP_WIDTH, "height": 800})
        page.wait_for_function(
            "() => document.querySelector('.nav-toggle')"
            ".getAttribute('aria-expanded') === 'true'",
            timeout=10_000,
        )
        assert panel.is_visible(), f"{path}: the menu must show on desktop"
        page.set_viewport_size({"width": PHONE_WIDTH, "height": 800})
        page.wait_for_timeout(200)
        assert (panel.is_visible()) == (
            toggle.get_attribute("aria-expanded") == "true"
        ), f"{path}: `aria-expanded` contradicts the visible panel after resize"


@pytest.mark.parametrize("path", ["/", "/vi/"])
def test_menu_stays_open_without_js(path, built_site_url, browser):
    """#384: with JS disabled the menu is visible and every link works —
    the `html.no-js` CSS override re-shows the shipped-collapsed panel."""
    context = browser.new_context(
        viewport={"width": PHONE_WIDTH, "height": 800}, java_script_enabled=False
    )
    try:
        page = context.new_page()
        origin = urlparse(built_site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        response = page.goto(f"{built_site_url}{path}", wait_until="load")
        assert response is not None and response.status == 200
        assert page.evaluate(
            "document.documentElement.classList.contains('no-js')"
        ), f"{path}: the `no-js` hook must survive without JS"
        panel = page.locator(f"#{EXPECTED_PANEL_ID}")
        assert panel.is_visible(), f"{path}: the menu must stay open without JS"
        links = panel.locator(".nav-item")
        assert links.count() > 0, f"{path}: the menu holds no links"
        for index in range(links.count()):
            link = links.nth(index)
            assert link.is_visible()
            href = link.get_attribute("href")
            assert href, f"{path}: a menu link has no destination"
            link_response = page.request.get(f"{built_site_url}{href}")
            assert link_response.status == 200, (
                f"{path}: menu link {href} broke without JS "
                f"(status {link_response.status})"
            )
    finally:
        context.close()


@pytest.mark.parametrize("path", ["/", "/vi/", TAG_PAGE, VI_TAG_PAGE])
def test_desktop_menu_needs_no_toggle(path, built_site_url, browser):
    """Desktop keeps its design: no toggle, menu simply shown."""
    for page in _viewport(browser, built_site_url, DESKTOP_WIDTH):
        _open(page, built_site_url, path)
        toggle = page.locator(".nav-toggle")
        assert toggle.is_hidden(), f"{path}: the toggle must stay hidden on desktop"
        panel = page.locator(f"#{EXPECTED_PANEL_ID}")
        assert panel.is_visible(), f"{path}: the menu must show on desktop"
        assert panel.locator(".nav-item").first.is_visible()
