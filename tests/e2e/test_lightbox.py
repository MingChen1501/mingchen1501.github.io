"""Guards for #223: accessible image lightbox for post content images.

Long-form posts carry many content images with no way to view one
full-size. ``assets/js/lightbox.js`` progressively enhances every
informative ``.post-content`` image (the image itself becomes the trigger,
so enhancement adds no box and cannot shift layout) into a keyboard-operable
viewer: click or Enter/Space opens the full-resolution source in an overlay
with its alt/caption, arrows move prev/next within the post, Esc closes and
returns focus to the invoking image. Decorative repeats (``aria-hidden``,
#147) and linked images stay out of the set; the dialog is built at runtime,
so without JS the page ships no overlay markup at all.

Guarded here:

- the script exists, stays vanilla (no dependency, no build step) and
  localized (EN default, VI), with dialog semantics (``role="dialog"``,
  ``aria-modal``, focus trap + restore, Escape/arrows, swipe) and source
  reuse (``currentSrc`` — no new image variants);
- only informative images become triggers (non-empty ``alt``, no
  ``aria-hidden``, never inside a link);
- the template links it with the ``?v=`` build token (#61);
- the styles scope every new box under ``.lightbox`` (``hidden`` hides),
  keep 44px controls, a visible trigger focus and ``prefers-reduced-motion``
  handling, and change no trigger geometry;
- built EN/VI post pages ship no dialog markup and no trigger attributes
  (progressive enhancement);
- browser (needs Ruby + a browser): open via click and via keyboard, caption
  shown, arrows move with a live counter, Esc closes and restores focus, the
  focus trap cycles, single-image sets hide prev/next, external
  attachment-URL images (#195) open the same way, axe is clean with the
  overlay open, and with JS disabled the images stay plain.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "lightbox.js"
HELPER = REPO_ROOT / "assets" / "js" / "site-utils.js"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
PARTIAL = REPO_ROOT / "_sass" / "minima" / "custom" / "_lightbox.scss"
STYLES_INDEX = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
AXE_JS = REPO_ROOT / "tests" / "e2e" / "axe-core" / "axe.min.js"

SCRIPT_PATH = "/assets/js/lightbox.js"

# The dialog (trap, restore, swipe, i18n) is unavoidably bigger than the
# copy-code one-liner, but it ships on post pages only (#318): keep it small.
MAX_SCRIPT_BYTES = 12 * 1024
MAX_SCRIPT_CODE_LINES = 260

VIEWER_EN = "Image viewer"
VIEWER_VI = "Trình xem ảnh"
CLOSE_EN = "Close"
CLOSE_VI = "Đóng"
PREV_EN = "Previous image"
PREV_VI = "Ảnh trước"
NEXT_EN = "Next image"
NEXT_VI = "Ảnh tiếp theo"
TRIGGER_EN = "View full-size image"
TRIGGER_VI = "Xem ảnh đầy đủ"

# The EN/VI coffee pair shares `ref: cach-pha-ca-phe` (same article in both
# languages); the EN post holds six informative images, the VI twin five
# (its blockquote lead repeat is `aria-hidden`, #147).
EN_POST = "/2022/10/27/brewing-vietnamese-coffee.html"
VI_POST = "/vi/2022/10/27/cach-pha-ca-phe.html"


def _read(path):
    return path.read_text(encoding="utf-8")


def _code_lines(text):
    return [
        line
        for line in text.splitlines()
        if line.strip()
        and not line.strip().startswith(("/*", "*", "//"))
    ]


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_lightbox_script_exists_and_stays_vanilla():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the lightbox script ships on every page: keep it under "
        f"{MAX_SCRIPT_BYTES} bytes"
    )
    assert len(_code_lines(text)) <= MAX_SCRIPT_CODE_LINES, (
        "the lightbox script grows past its budget"
    )
    assert "import " not in text and "require(" not in text, (
        "the lightbox script must not depend on anything"
    )


@pytest.mark.static
def test_the_lightbox_labels_are_localized():
    """Every control name ships in EN and VI, chosen from `<html lang>`."""
    text = _read(SCRIPT)
    for label in (
        VIEWER_EN,
        VIEWER_VI,
        CLOSE_EN,
        CLOSE_VI,
        PREV_EN,
        PREV_VI,
        NEXT_EN,
        NEXT_VI,
        TRIGGER_EN,
        TRIGGER_VI,
    ):
        assert label in text, f"the script never renders the label {label!r}"
    assert "aria-label" in text, (
        "the dialog and its controls must expose accessible names"
    )
    # The page language comes from the shared helper (#246); the labels
    # themselves still live here.
    assert "SiteUtils" in text and "isVietnamese" in text, (
        "the labels must follow the page language via the shared "
        "SiteUtils helper (#246)"
    )


@pytest.mark.static
def test_only_informative_images_become_triggers():
    """Decorative repeats and linked images never join the viewer set."""
    text = _read(SCRIPT)
    assert ".post-content img" in text, (
        "the script must scope itself to `.post-content` images"
    )
    assert "aria-hidden" in text, (
        "decorative repeats (`aria-hidden`, #147) must stay out of the set"
    )
    assert "closest('a')" in text or 'closest("a")' in text, (
        "images already wrapped in a link must keep navigating, not open "
        "the viewer"
    )
    assert re.search(r"getAttribute\(['\"]alt['\"]\)", text), (
        "an image without usable alt text must never become a trigger"
    )


@pytest.mark.static
def test_the_dialog_semantics_live_in_the_script():
    """role/aria-modal, focus trap + restore, Escape/arrows, swipe, reuse."""
    text = _read(SCRIPT)
    assert 'role' in text and '"dialog"' in text, (
        "the overlay must carry `role=\"dialog\"`"
    )
    assert "aria-modal" in text, "the dialog must be modal"
    assert "aria-describedby" in text, (
        "the dialog must describe itself with the visible caption"
    )
    for key in ("Escape", "ArrowLeft", "ArrowRight", "Tab"):
        assert f'"{key}"' in text or f"'{key}'" in text, (
            f"the dialog must handle the {key} key"
        )
    assert "shiftKey" in text, "the focus trap must wrap in both directions"
    assert ".focus()" in text, (
        "focus must move into the dialog and back to the invoking image"
    )
    assert "touchstart" in text and "touchend" in text, (
        "a horizontal swipe must move prev/next on touch screens"
    )
    assert "currentSrc" in text, (
        "the viewer must reuse the already-loaded source (`currentSrc`), "
        "never generate a new variant"
    )
    assert "prefers-reduced-motion" in text or "reduced" in text.lower(), (
        "the script must document its no-animation stance for "
        "`prefers-reduced-motion` readers"
    )


@pytest.mark.static
def test_the_lightbox_script_is_linked_with_the_cache_version_token():
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
def test_the_lightbox_partial_joins_the_cascade():
    assert PARTIAL.is_file(), f"{PARTIAL.relative_to(REPO_ROOT)} is missing"
    index = _read(STYLES_INDEX)
    assert "minima/custom/lightbox" in index, (
        "the lightbox partial must be imported from custom-styles.scss "
        "(#174 cascade index)"
    )
    assert index.index("minima/custom/lightbox") < index.index(
        "minima/custom/legibility"
    ), (
        "the lightbox partial must stay before the legibility partial: "
        "the #148 guard scans everything past its own marker and the "
        "dialog image needs `max-height` to fit the viewport"
    )


@pytest.mark.static
def test_the_lightbox_styles_shift_no_layout():
    """The overlay is fixed; the trigger keeps its exact built box."""
    scss = _read(PARTIAL)
    assert ".lightbox[hidden]" in scss and "display: none" in scss, (
        "the closed overlay must render nothing (`display: flex` would "
        "override the `hidden` attribute otherwise)"
    )
    assert ".lightbox__prev[hidden]" in scss, (
        "the `hidden` attribute must win over the `inline-flex` control "
        "rule, so single-image sets really hide prev/next"
    )
    assert "position: fixed" in scss, (
        "the overlay must float above the page, never in its flow"
    )
    assert "prefers-reduced-motion" in scss, (
        "the overlay must pin its no-animation promise for "
        "`prefers-reduced-motion` readers"
    )
    assert "min-width: 44px" in scss and "min-height: 44px" in scss, (
        "the dialog controls must keep a 44px minimum touch target"
    )
    assert "img.lightbox-trigger:focus-visible" in scss, (
        "the image trigger needs its own visible keyboard focus (the "
        "global rule only covers links and buttons)"
    )
    assert "cursor: zoom-in" in scss, (
        "the trigger must advertise the viewer affordance"
    )
    trigger_block = scss[
        scss.index("img.lightbox-trigger {"):
        scss.index("}", scss.index("img.lightbox-trigger {"))
    ]
    for prop in ("margin", "padding", "border", "width", "height", "display"):
        assert prop not in trigger_block, (
            f"the trigger rule must not set `{prop}`: enhancement adds no "
            "box, so the built aspect-ratio box never shifts"
        )


# --- built-HTML guards (need the real `jekyll build`, no browser) ---------


def _post_html(built_site, path):
    page = built_site / path.lstrip("/")
    assert page.is_file(), f"expected a built page at {page}"
    return _read(page)


def test_no_overlay_markup_is_shipped_without_js(built_site):
    """Progressive enhancement: the build carries no dialog, no triggers."""
    for path in (EN_POST, VI_POST):
        html = _post_html(built_site, path)
        assert "lightbox__dialog" not in html, (
            f"{path} ships dialog markup: the overlay must be built by JS "
            "only, so the page is unchanged with JS disabled"
        )
        assert "lightbox-trigger" not in html, (
            f"{path} ships trigger attributes: images become triggers at "
            "runtime, never in the markup"
        )
        assert 'role="button"' not in html, (
            f"{path} ships button roles on images without JS"
        )


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    html = _post_html(built_site, EN_POST)
    match = re.search(r'<script src="(/assets/js/lightbox\.js\?v=([^"]+))"', html)
    assert match, "the post page does not link the lightbox script (#318)"
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


def _triggers(page):
    return page.locator(".post-content img.lightbox-trigger")


def _dialog(page):
    return page.locator(".lightbox__dialog")


def _open_first(page, built_site_url, path):
    page.goto(built_site_url.rstrip("/") + path, wait_until="load")
    page.wait_for_selector(
        ".post-content img.lightbox-trigger", state="attached", timeout=10_000
    )
    _triggers(page).first.click()
    page.wait_for_selector(".lightbox:not([hidden])", timeout=10_000)


def test_unopened_overlay_adds_no_pending_image(built_site_url, page):
    """The viewer `<img>` is created on first open: before any interaction
    every image in the document must carry a source and decode, so settle
    checks (e.g. the visual-baseline `_SETTLE_JS`, #208) see exactly the
    content images and never stall on a src-less placeholder."""
    page.goto(built_site_url.rstrip("/") + EN_POST, wait_until="load")
    page.wait_for_selector(
        ".post-content img.lightbox-trigger", state="attached", timeout=10_000
    )
    # Walk the page so lazy-loaded images decode, mirroring the settle.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(400)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_function(
        "() => Array.from(document.images).every("
        "(img) => img.complete && img.naturalWidth > 0)",
        timeout=15_000,
    )
    srcs = page.evaluate(
        "() => Array.from(document.images).map((img) => img.getAttribute('src'))"
    )
    assert srcs, "the post page must contain content images to judge"
    assert all(srcs), (
        "the unopened overlay must not leave a src-less `<img>` in the DOM"
    )


def _run_axe(page):
    page.add_script_tag(path=str(AXE_JS))
    page.wait_for_function("() => !!window.axe", timeout=15_000)
    return page.evaluate(
        "() => window.axe.run(document, {resultTypes: ['violations']})"
        ".then((results) => results.violations.map((v) => ({"
        "  id: v.id,"
        "  impact: v.impact,"
        "  nodes: v.nodes.map((n) => ({"
        "    target: n.target.join(' '),"
        "    html: (n.html || '').slice(0, 200),"
        "  })),"
        "})))"
    )


def test_click_opens_the_overlay_with_alt_and_escape_restores_focus(
    built_site_url, page
):
    """Click opens the full-size source; Esc closes onto the same image."""
    _open_first(page, built_site_url, EN_POST)
    dialog = _dialog(page)
    assert dialog.get_attribute("role") == "dialog"
    assert dialog.get_attribute("aria-modal") == "true"
    assert dialog.get_attribute("aria-label") == VIEWER_EN
    first_src = page.evaluate(
        "() => document.querySelector("
        "'.post-content img.lightbox-trigger').currentSrc"
    )
    assert page.locator(".lightbox__image").get_attribute("src") == first_src
    assert (
        page.locator(".lightbox__image").get_attribute("alt")
        == _triggers(page).first.get_attribute("alt")
    )
    # First trigger is the blockquote lead repeat (#309 gave it a
    # descriptive alt instead of `aria-hidden`, so it joins the set).
    assert "Stainless steel phin filter" in page.locator(
        ".lightbox__caption"
    ).inner_text()
    assert page.locator(".lightbox__counter").inner_text() == "1 / 6"
    assert page.get_by_role("button", name=CLOSE_EN).count() == 1

    invoking = _triggers(page).first
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)
    assert invoking.evaluate("el => document.activeElement === el"), (
        "Esc must return focus to the invoking image"
    )


def test_keyboard_flow_opens_moves_and_closes(built_site_url, page):
    """Tab-focus, Enter, arrows with a live counter, Esc (EN post)."""
    page.goto(built_site_url.rstrip("/") + EN_POST, wait_until="load")
    page.wait_for_selector(
        ".post-content img.lightbox-trigger", state="attached", timeout=10_000
    )
    first = _triggers(page).first
    first.focus()
    page.keyboard.press("Enter")
    page.wait_for_selector(".lightbox:not([hidden])", timeout=10_000)
    assert page.locator(".lightbox__counter").inner_text() == "1 / 6"

    page.keyboard.press("ArrowRight")
    assert page.locator(".lightbox__counter").inner_text() == "2 / 6"
    assert (
        page.locator(".lightbox__image").get_attribute("alt")
        == _triggers(page).nth(1).get_attribute("alt")
    )
    page.keyboard.press("ArrowLeft")
    assert page.locator(".lightbox__counter").inner_text() == "1 / 6"

    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)
    assert page.evaluate(
        "() => document.activeElement && "
        "document.activeElement.className.indexOf('lightbox-trigger') !== -1"
    ), "Esc must return focus to the invoking image"


def test_space_opens_and_buttons_navigate(built_site_url, page):
    """Space is a second open key; prev/next buttons move the set."""
    page.goto(built_site_url.rstrip("/") + EN_POST, wait_until="load")
    page.wait_for_selector(
        ".post-content img.lightbox-trigger", state="attached", timeout=10_000
    )
    _triggers(page).first.focus()
    page.keyboard.press("Space")
    page.wait_for_selector(".lightbox:not([hidden])", timeout=10_000)

    page.get_by_role("button", name=NEXT_EN).click()
    assert page.locator(".lightbox__counter").inner_text() == "2 / 6"
    page.get_by_role("button", name=PREV_EN).click()
    assert page.locator(".lightbox__counter").inner_text() == "1 / 6"
    # Wrapping: prev from the first image lands on the last one.
    page.get_by_role("button", name=PREV_EN).click()
    assert page.locator(".lightbox__counter").inner_text() == "6 / 6"
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)


def test_focus_stays_trapped_inside_the_open_dialog(built_site_url, page):
    _open_first(page, built_site_url, EN_POST)
    dialog = _dialog(page)
    for _ in range(5):
        page.keyboard.press("Tab")
        assert page.evaluate(
            "() => document.querySelector('.lightbox__dialog').contains("
            "document.activeElement)"
        ), "Tab must cycle inside the open dialog"
    for _ in range(5):
        page.keyboard.press("Shift+Tab")
        assert page.evaluate(
            "() => document.querySelector('.lightbox__dialog').contains("
            "document.activeElement)"
        ), "Shift+Tab must cycle inside the open dialog"
    assert dialog.is_visible()
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)


def test_vietnamese_post_uses_vietnamese_labels(built_site_url, page):
    """Same flow on the VI twin, at phone width: localized names."""
    page.set_viewport_size({"width": 375, "height": 800})
    _open_first(page, built_site_url, VI_POST)
    dialog = _dialog(page)
    assert dialog.get_attribute("aria-label") == VIEWER_VI
    assert page.get_by_role("button", name=CLOSE_VI).count() == 1
    assert page.get_by_role("button", name=PREV_VI).count() == 1
    assert page.get_by_role("button", name=NEXT_VI).count() == 1
    assert page.locator(".lightbox__counter").inner_text() == "1 / 5"
    trigger_label = _triggers(page).first.get_attribute("aria-label") or ""
    assert trigger_label.startswith(TRIGGER_VI), (
        f"the VI trigger label must start with {TRIGGER_VI!r}, got "
        f"{trigger_label!r}"
    )
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)


def test_decorative_repeats_never_become_triggers(built_site_url, page):
    """The VI lead repeat is `aria-hidden` (#147): present, not a trigger."""
    page.goto(built_site_url.rstrip("/") + VI_POST, wait_until="load")
    page.wait_for_selector(".post-content img", state="attached", timeout=10_000)
    assert page.locator(".post-content img").count() == 6
    assert _triggers(page).count() == 5, (
        "the `aria-hidden` lead repeat must stay a plain image"
    )
    assert page.locator('.post-content img[aria-hidden="true"]').count() == 1


def test_single_image_set_hides_prev_next(built_site_url, page):
    """One informative image: viewer works, navigation hides."""
    page.goto(built_site_url.rstrip("/") + "/", wait_until="load")
    page.evaluate(
        """() => {
          document.body.insertAdjacentHTML('beforeend',
            '<div class="post-content" id="lb-single">'
            + '<img src="/assets/img/placeholder.svg" alt="Lone image"'
            + ' width="120" height="90"></div>');
        }"""
    )
    # The viewer reads DOM-ready/lang from the shared helper (#246).
    page.add_script_tag(path=str(HELPER))
    page.add_script_tag(path=str(SCRIPT))
    page.wait_for_selector(
        "#lb-single img.lightbox-trigger", state="attached", timeout=10_000
    )
    page.locator("#lb-single img.lightbox-trigger").click()
    page.wait_for_selector(".lightbox:not([hidden])", timeout=10_000)
    assert page.locator(".lightbox__counter").inner_text() == "1 / 1"
    assert not page.locator(".lightbox__prev").is_visible()
    assert not page.locator(".lightbox__next").is_visible()
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)


def test_external_attachment_url_opens_like_a_local_image(
    built_site_url, page
):
    """External #195 attachment URLs join the set with their own src/alt."""
    external = "https://github.com/user-attachments/assets/3f4a5b6c-lightbox"
    page.goto(built_site_url.rstrip("/") + "/", wait_until="load")
    page.evaluate(
        """(src) => {
          document.body.insertAdjacentHTML('beforeend',
            '<div class="post-content" id="lb-external">'
            + '<img src="' + src + '" alt="External diagram"'
            + ' width="1200" height="800"></div>');
        }""",
        external,
    )
    # The viewer reads DOM-ready/lang from the shared helper (#246).
    page.add_script_tag(path=str(HELPER))
    page.add_script_tag(path=str(SCRIPT))
    page.wait_for_selector(
        "#lb-external img.lightbox-trigger", state="attached", timeout=10_000
    )
    page.locator("#lb-external img.lightbox-trigger").click()
    page.wait_for_selector(".lightbox:not([hidden])", timeout=10_000)
    assert page.locator(".lightbox__image").get_attribute("src") == external
    assert page.locator(".lightbox__image").get_attribute("alt") == (
        "External diagram"
    )
    assert "External diagram" in page.locator(
        ".lightbox__caption"
    ).inner_text()
    page.keyboard.press("Escape")
    page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)


def test_axe_clean_with_the_overlay_open(built_site_url, browser):
    """The vendored scanner reports no serious/critical on an open overlay."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        scan = context.new_page()
        origin = urlparse(built_site_url).netloc
        scan.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        _open_first(scan, built_site_url, EN_POST)
        violations = _run_axe(scan)
    finally:
        context.close()
    blocking = [
        v for v in violations if v["impact"] in ("serious", "critical")
    ]
    assert not blocking, (
        "axe serious/critical violations with the lightbox open:\n"
        + "\n".join(
            f"[{v['impact']}] {v['id']} "
            + ", ".join(
                f"target={n['target']} html={n['html']}" for n in v["nodes"]
            )
            for v in blocking
        )
    )


def test_without_js_images_stay_plain(built_site_url, browser):
    """No-JS readers get the unchanged page: plain images, no overlay."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        plain.goto(
            built_site_url.rstrip("/") + EN_POST, wait_until="load"
        )
        assert plain.locator(".post-content img").count() > 0
        assert plain.locator(".lightbox-trigger").count() == 0
        assert plain.locator(".lightbox").count() == 0
    finally:
        context.close()


def test_opening_adds_no_page_overflow(built_site_url, page):
    """The overlay floats: no horizontal scroll at phone or desktop width."""
    for width in (375, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        _open_first(page, built_site_url, EN_POST)
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth"
        ), f"the open overlay overflows the viewport at {width}px"
        page.keyboard.press("Escape")
        page.wait_for_selector(".lightbox[hidden]", state="attached", timeout=10_000)
