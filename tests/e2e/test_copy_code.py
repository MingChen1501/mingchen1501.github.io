"""Guards for #126: fenced code blocks get an accessible copy button.

Vanilla ``assets/js/copy-code.js`` progressively enhances every ``pre > code``
with a localized copy button (``Copy code`` / ``Sao chép mã``); without JS the
markup is unchanged. Copies via the Clipboard API with a textarea fallback.

Guarded here:

- the script exists, stays tiny and has no dependency (static);
- it enhances only ``pre > code`` — never a bare ``pre`` or inline ``code``
  (static + browser);
- the labels are localized from ``<html lang>``, including the copied
  feedback (static + browser, EN and VI);
- it copies via the Clipboard API with a textarea + ``execCommand`` fallback
  (static + browser clipboard read-back);
- the template links it through the ``?v=`` build token, like every other
  fixed-URL asset (#61) (static + rendered);
- the button keeps a 44px minimum touch target and a visible keyboard focus,
  and never adds horizontal overflow at 375px (static + browser);
- without JS no button is rendered at all (built markup).
- success feedback is announced through a per-block polite live region in
  EN and VI, cleared on revert, exactly once per copy (#257) (static +
  browser);
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "copy-code.js"
HELPER = REPO_ROOT / "assets" / "js" / "site-utils.js"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"

SCRIPT_PATH = "/assets/js/copy-code.js"

# The script is plain DOM code with a Clipboard fallback and localized
# feedback; keep it that way.
MAX_SCRIPT_BYTES = 2048
MAX_SCRIPT_CODE_LINES = 55

COPY_EN = "Copy code"
COPY_VI = "Sao chép mã"
DONE_EN = "Copied"
DONE_VI = "Đã sao chép"


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_copy_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the copy-code script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the copy-code script has {len(code)} code lines, expected at most "
        f"{MAX_SCRIPT_CODE_LINES}"
    )
    # No dependency, no build step: the file runs as it is served.
    assert "import " not in text and "require(" not in text, (
        "the copy-code script must not depend on anything"
    )


@pytest.mark.static
def test_the_script_enhances_only_pre_code():
    """Only fenced blocks get a button: no bare `pre`, no inline `code`."""
    text = _read(SCRIPT)
    assert "pre > code" in text, (
        "the script must target `pre > code` (fenced blocks only)"
    )
    assert "querySelectorAll('pre')" not in text and 'querySelectorAll("pre")' not in text, (
        "the script must not decorate bare `pre` elements"
    )


@pytest.mark.static
def test_the_copy_label_is_localized():
    """The accessible name follows `<html lang>` (EN default, VI)."""
    text = _read(SCRIPT)
    for label in (COPY_EN, COPY_VI, DONE_EN, DONE_VI):
        assert label in text, f"the script never renders the label {label!r}"
    assert "SiteUtils" in text and "isVietnamese" in text, (
        "the label must be derived from the page language via the shared "
        "SiteUtils helper (#246)"
    )
    assert "document.documentElement" in _read(HELPER) and "lang" in _read(HELPER), (
        "the shared helper must read the page language from `<html lang>`"
    )
    assert "aria-label" in text, (
        "the button must expose its label as an accessible name"
    )


@pytest.mark.static
def test_the_copied_confirmation_is_announced_via_a_polite_live_region():
    """#257: success feedback must reach screen readers, not just sighted users."""
    text = _read(SCRIPT)
    assert "copy-code__status" in text, (
        "each enhanced block needs its own status node for the announcement"
    )
    assert "visually-hidden" in text, (
        "the status node must stay visually hidden so there is no visual change"
    )
    assert "'status'" in text or '"status"' in text, (
        "the status node must carry role=status, like the share row (#257)"
    )
    assert "aria-live" in text and "polite" in text, (
        "the announcement must go through a polite live region"
    )
    assert "status.textContent = DONE" in text, (
        "the live region must announce the localized DONE strings"
    )
    assert "status.textContent = ''" in text or 'status.textContent = ""' in text, (
        "the live region must clear on revert so a repeat copy announces again"
    )


@pytest.mark.static
def test_one_copy_announces_exactly_once():
    """#257: a single copy must produce a single announcement."""
    text = _read(SCRIPT)
    assert text.count("aria-live") == 1, (
        "exactly one polite live region per block: the button's own 2s label "
        "flip stays visual-only so screen readers hear the confirmation once"
    )
    assert "status.setAttribute('aria-live', 'polite')" in text or (
        'status.setAttribute("aria-live", "polite")' in text
    ), "only the status node may be a live region, never the button"


@pytest.mark.static
def test_the_script_copies_with_a_fallback():
    """Clipboard API first, textarea + execCommand where it is missing."""
    text = _read(SCRIPT)
    helper = _read(HELPER)
    assert "SiteUtils" in text and "copyText" in text, (
        "the script must copy through the shared SiteUtils helper (#246)"
    )
    assert "navigator.clipboard" in helper and "writeText" in helper, (
        "the shared helper must copy through the Clipboard API"
    )
    assert "textarea" in helper and "execCommand" in helper, (
        "the shared helper must fall back to a textarea + execCommand copy"
    )


@pytest.mark.static
def test_the_copy_script_is_linked_with_the_cache_version_token():
    """A fixed-URL asset must carry the build token (#61)."""
    html = _read(SUB_FOOTER)
    assert f"{SCRIPT_PATH}?v=" in html, (
        f"{SUB_FOOTER.relative_to(REPO_ROOT)} must link {SCRIPT_PATH} with the "
        "`?v=` build token, like every other fixed-URL asset (#61)"
    )
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER)), (
        "the version token must be derived from the build"
    )


@pytest.mark.static
def test_the_button_style_meets_the_touch_target_and_focus():
    """44px minimum target, floating over the block, focus stays visible."""
    scss = conftest.custom_styles_text()
    assert ".copy-code__button" in scss, (
        "the copy button needs its own style block in the custom styles"
    )
    assert "min-width: 44px" in scss and "min-height: 44px" in scss, (
        "the copy button must keep a 44px minimum touch target"
    )
    assert "position: absolute" in scss, (
        "the button must float over the block instead of shifting the code"
    )
    assert "button:focus-visible" in scss, (
        "#87's focus rule covers buttons, so the copy button never goes dark"
    )


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    text = _read(built_site / "index.html")
    match = re.search(r'<script src="(/assets/js/copy-code\.js\?v=([^"]+))"', text)
    assert match, "the home page does not link the copy-code script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


def test_no_button_is_rendered_without_js(built_site):
    """Graceful degradation: the build ships no button markup at all."""
    pages = [built_site / "index.html", built_site / "vi" / "index.html"]
    for page in pages:
        assert page.is_file(), f"expected a built page at {page}"
        text = _read(page)
        assert "copy-code__button" not in text, (
            f"{page.relative_to(built_site)} ships button markup: the button "
            "must be added by JS only"
        )
        assert 'class="copy-code"' not in text, (
            f"{page.relative_to(built_site)} ships the wrapper: enhancement "
            "must happen at runtime"
        )


# --- browser guards (need Ruby + a browser) ---------------------------------


@pytest.fixture()
def page(browser, browser_name):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    if browser_name == "chromium":
        # Chromium needs explicit clipboard grants for the read-back below.
        # Firefox allows clipboard over loopback HTTP with no grant (and
        # rejects the grant call); WebKit grants neither clipboard-read nor
        # clipboard-write, and headless WebKit denies navigator.clipboard
        # outright, so the two click-to-copy tests skip there (#209).
        context.grant_permissions(["clipboard-read", "clipboard-write"])
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


_FIXTURE_HTML = """
<div class="post-content" id="copy-fixture">
  <div class="highlight"><pre class="highlight"><code>puts 'hello'</code></pre></div>
  <pre>plain pre, no code child</pre>
  <p>inline <code>code</code> stays button-free</p>
</div>
"""

_INJECT_JS = (
    "(html) => { document.body.insertAdjacentHTML('beforeend', html); }"
)


def _enhance(page, built_site_url, path):
    """Load a real page, inject code samples, run the real script file."""
    page.goto(built_site_url.rstrip("/") + path, wait_until="load")
    page.evaluate(_INJECT_JS, _FIXTURE_HTML)
    # The script reads its clipboard/DOM-ready helpers from `site-utils.js`
    # (#246), loaded first like the deferred tags in `sub-footer.html`.
    page.add_script_tag(path=str(HELPER))
    page.add_script_tag(path=str(SCRIPT))
    page.wait_for_selector(".copy-code__button", state="attached", timeout=10_000)


def test_only_fenced_blocks_get_a_button_and_clicking_copies(
    built_site_url, page, browser_name
):
    if browser_name == "webkit":
        pytest.skip(
            "headless WebKit denies navigator.clipboard (NotAllowedError) and "
            "Playwright grants no clipboard permission on WebKit, so the "
            "clipboard read-back cannot run there (#209); the button, its "
            "localization and the copied feedback still run on "
            "Chromium/Firefox"
        )
    _enhance(page, built_site_url, "/")

    buttons = page.get_by_role("button", name=COPY_EN)
    assert buttons.count() == 1, (
        f"expected one {COPY_EN!r} button (one `pre > code`), got "
        f"{buttons.count()}"
    )
    # The bare `pre` and the inline `code` stay button-free.
    assert page.locator("#copy-fixture .copy-code").count() == 1

    buttons.first.click()
    page.wait_for_function(
        "() => document.querySelector('.copy-code__button')"
        f".textContent === {DONE_EN!r}",
        timeout=10_000,
    )
    assert page.evaluate("() => navigator.clipboard.readText()") == "puts 'hello'"
    button = page.locator(".copy-code__button").first
    assert button.get_attribute("aria-label") == DONE_EN


def test_the_button_label_follows_the_vietnamese_page(
    built_site_url, page, browser_name
):
    if browser_name == "webkit":
        pytest.skip(
            "headless WebKit denies navigator.clipboard (NotAllowedError) and "
            "Playwright grants no clipboard permission on WebKit, so the "
            "clipboard read-back cannot run there (#209)"
        )
    _enhance(page, built_site_url, "/vi/")

    buttons = page.get_by_role("button", name=COPY_VI)
    assert buttons.count() == 1, (
        f"the Vietnamese page must label its button {COPY_VI!r}, got "
        f"{buttons.count()}"
    )
    assert page.get_by_role("button", name=COPY_EN).count() == 0

    buttons.first.click()
    page.wait_for_function(
        "() => document.querySelector('.copy-code__button')"
        f".textContent === {DONE_VI!r}",
        timeout=10_000,
    )
    assert page.evaluate("() => navigator.clipboard.readText()") == "puts 'hello'"


def test_copy_success_is_announced_through_a_live_region(
    built_site_url, page, browser_name
):
    """#257: the EN confirmation surfaces through role=status, then clears."""
    if browser_name == "webkit":
        pytest.skip(
            "headless WebKit denies navigator.clipboard (NotAllowedError) and "
            "Playwright grants no clipboard permission on WebKit, so the "
            "clipboard read-back cannot run there (#209)"
        )
    _enhance(page, built_site_url, "/")

    status = page.locator("#copy-fixture .copy-code__status")
    # One status node for the one fenced block: bare `pre` and inline `code`
    # stay announcement-free.
    assert status.count() == 1
    assert status.get_attribute("role") == "status"
    assert status.get_attribute("aria-live") == "polite"
    assert status.text_content() == ""

    page.get_by_role("button", name=COPY_EN).first.click()
    page.wait_for_function(
        "() => document.querySelector('#copy-fixture .copy-code__status')"
        f".textContent === {DONE_EN!r}",
        timeout=10_000,
    )
    # The visual button feedback is unchanged alongside the announcement.
    assert page.locator(".copy-code__button").first.get_attribute("aria-label") == DONE_EN

    # The revert clears both the label and the region, so a repeat copy
    # announces the confirmation again instead of going silent.
    page.wait_for_function(
        "() => document.querySelector('.copy-code__button')"
        f".textContent === {COPY_EN!r}",
        timeout=10_000,
    )
    assert status.text_content() == ""


def test_copy_success_is_announced_in_vietnamese(
    built_site_url, page, browser_name
):
    """#257: the VI confirmation surfaces through the same live region."""
    if browser_name == "webkit":
        pytest.skip(
            "headless WebKit denies navigator.clipboard (NotAllowedError) and "
            "Playwright grants no clipboard permission on WebKit, so the "
            "clipboard read-back cannot run there (#209)"
        )
    _enhance(page, built_site_url, "/vi/")

    status = page.locator("#copy-fixture .copy-code__status")
    assert status.count() == 1
    assert status.get_attribute("role") == "status"
    assert status.get_attribute("aria-live") == "polite"

    page.get_by_role("button", name=COPY_VI).first.click()
    page.wait_for_function(
        "() => document.querySelector('#copy-fixture .copy-code__status')"
        f".textContent === {DONE_VI!r}",
        timeout=10_000,
    )


def test_the_button_keeps_its_target_focus_and_layout(
    built_site_url, browser, browser_name
):
    """44px touch target at 375px, visible focus, no horizontal overflow."""
    context = browser.new_context(viewport={"width": 375, "height": 800})
    if browser_name == "chromium":
        # See the `page` fixture above: only Chromium needs (and accepts)
        # the clipboard grants; this guard never touches the clipboard.
        context.grant_permissions(["clipboard-read", "clipboard-write"])
    narrow = context.new_page()
    try:
        origin = urlparse(built_site_url).netloc
        narrow.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        _enhance(narrow, built_site_url, "/")
        button = narrow.locator(".copy-code__button").first
        box = button.bounding_box()
        assert box is not None, "the copy button has no rendered box"
        assert box["width"] >= 44 and box["height"] >= 44, (
            "the copy button must keep a 44px minimum touch target, got "
            f"{box['width']:.0f}x{box['height']:.0f}"
        )
        button.focus()
        outline = narrow.evaluate(
            "() => { const s = getComputedStyle("
            "document.querySelector('.copy-code__button')); "
            "return {style: s.outlineStyle, width: s.outlineWidth}; }"
        )
        assert outline["style"] != "none" and outline["width"] != "0px", (
            f"keyboard focus on the button must stay visible, got {outline}"
        )
        overflow = narrow.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 0, (
            f"the button must not add horizontal overflow at 375px (+{overflow}px)"
        )
    finally:
        context.close()
