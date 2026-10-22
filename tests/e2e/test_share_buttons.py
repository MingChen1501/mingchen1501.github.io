"""Guards for #222: tracker-free share buttons on post pages.

Post pages had no sharing affordance, so `_layouts/post.html` now renders a
small share row (via `_includes/share.html`) at the end of the post column:
a copy-link button, a Web Share button revealed only where `navigator.share`
exists, and three plain share-intent links (X, Facebook, LinkedIn) with no
third-party SDK or tracker. Labels are localized (`Share` / `Chia sẻ`,
`Copy link` / `Sao chép liên kết`) with a localized confirmation
(`Copied` / `Đã sao chép`).

Guarded here:

- the include exists and is wired into the post layout only, below the
  content (static);
- the labels are localized per page language with stable accessible names
  (static + built);
- the copy button carries the canonical post URL and copies it through the
  Clipboard API with a textarea + ``execCommand`` fallback, announcing the
  confirmation in a ``role="status"`` line (static + browser clipboard
  read-back);
- the intent links encode the post URL/title, open in a new tab with
  ``noopener``, and work with JS disabled; no external script tag is added
  anywhere (static + built + browser);
- the native-share row stays hidden without ``navigator.share`` and shares
  through it where present (browser, stubbed);
- the copy-link item ships hidden and is revealed by the script, with a
  ``noscript`` fallback showing the canonical post URL as a plain visible
  link, so no-JS pages have zero dead controls (#244)
  (static + built + browser);
- the script is a tiny dependency-free first-party asset linked through the
  ``?v=`` build token like every other fixed-URL asset (#61)
  (static + rendered);
- every control keeps a 44px minimum touch target and a visible keyboard
  focus, the confirmation reserves its space (no layout shift), and the row
  adds no horizontal overflow at 375px (static + browser).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARE_INCLUDE = REPO_ROOT / "_includes" / "share.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
SCRIPT = REPO_ROOT / "assets" / "js" / "share.js"
HELPER = REPO_ROOT / "assets" / "js" / "site-utils.js"

SCRIPT_PATH = "/assets/js/share.js"

# The script is plain DOM code with a Clipboard fallback and an optional
# Web Share path; keep it that way.
MAX_SCRIPT_BYTES = 4096
MAX_SCRIPT_CODE_LINES = 100

HEADING_EN = "Share"
HEADING_VI = "Chia sẻ"
COPY_EN = "Copy link"
COPY_VI = "Sao chép liên kết"
DONE_EN = "Copied"
DONE_VI = "Đã sao chép"
POST_LINK_EN = "Post link"
POST_LINK_VI = "Liên kết bài viết"
NATIVE_EN = "Share…"
NATIVE_VI = "Chia sẻ…"
X_EN = "Share on X"
X_VI = "Chia sẻ lên X"

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _share_section(html):
    match = re.search(r'<section class="share".*?</section>', html, re.S)
    assert match, "expected a share row (`section.share`) in the page"
    return match.group(0)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_share_include_is_wired_into_the_post_layout_only():
    """The row renders on post pages, below the content, nowhere else."""
    assert SHARE_INCLUDE.is_file(), (
        f"{SHARE_INCLUDE.relative_to(REPO_ROOT)} is missing"
    )
    layout = _read(POST_LAYOUT)
    assert "include share.html" in layout, (
        "the post layout must render the share row"
    )
    content_pos = layout.find("{{ content }}")
    include_pos = layout.find("include share.html")
    assert 0 <= content_pos < include_pos, (
        "the share row must sit below the post content"
    )
    for template in sorted((REPO_ROOT / "_layouts").glob("*.html")):
        if template.name == "post.html":
            continue
        assert "share.html" not in _read(template), (
            f"{template.relative_to(REPO_ROOT)} must not render the share row: "
            "post pages only (#222)"
        )


@pytest.mark.static
def test_the_share_labels_are_localized():
    """Heading, buttons and confirmation follow the page language."""
    text = _read(SHARE_INCLUDE)
    for label in (
        HEADING_EN, HEADING_VI, COPY_EN, COPY_VI, DONE_EN, DONE_VI,
        POST_LINK_EN, POST_LINK_VI,
        NATIVE_EN, NATIVE_VI, X_EN, X_VI,
    ):
        assert label in text, f"the include never renders the label {label!r}"
    assert "page.lang | default: site.lang" in text, (
        "the labels must be derived from the page language, like `post_lang`"
    )


@pytest.mark.static
def test_the_copy_button_carries_the_canonical_url():
    """The button ships the absolute post URL for the script to copy."""
    text = _read(SHARE_INCLUDE)
    assert "absolute_url" in text, (
        "the copy button must carry the canonical post URL (`absolute_url`)"
    )
    assert "data-share-url" in text and "data-copied-label" in text, (
        "the copy button must expose the URL and the confirmation label "
        "as data attributes for the script"
    )
    assert 'role="status"' in text, (
        "the confirmation must be announced through a `role=status` line"
    )


@pytest.mark.static
def test_the_intent_links_are_plain_tracker_free_anchors():
    """Three provider share URLs, encoded, opening safely in a new tab."""
    text = _read(SHARE_INCLUDE)
    for host in (
        "twitter.com/intent/tweet",
        "www.facebook.com/sharer/sharer.php",
        "www.linkedin.com/sharing/share-offsite/",
    ):
        assert host in text, f"the include must link the {host} share intent"
    assert "uri_escape" in text, (
        "the post URL/title must be encoded into the intent links"
    )
    assert 'target="_blank"' in text and 'rel="noopener noreferrer"' in text, (
        "intent links must open in a new tab without an opener reference"
    )


@pytest.mark.static
def test_no_external_script_is_added():
    """Tracker-free means no third-party script tag anywhere new."""
    for path in (SHARE_INCLUDE, POST_LAYOUT, SUB_FOOTER):
        assert not re.search(r'<script[^>]+src="https?://', _read(path)), (
            f"{path.relative_to(REPO_ROOT)} must not add an external script"
        )


@pytest.mark.static
def test_the_copy_button_is_enhancement_only_with_a_noscript_fallback():
    """No-JS post pages show no dead copy control (#244)."""
    text = _read(SHARE_INCLUDE)
    assert "data-share-copy-item" in text and "hidden" in text, (
        "the copy-link item must ship hidden (JS reveals it), like the "
        "native-share row"
    )
    script = _read(SCRIPT)
    assert "data-share-copy-item" in script, (
        "the share script must reveal the copy-link item where JS runs"
    )
    assert "<noscript>" in text and "share__fallback" in text, (
        "no-JS readers need a visible fallback (the canonical post URL as "
        "a plain link) instead of the copy button"
    )


@pytest.mark.static
def test_the_share_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the share script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the share script has {len(code)} code lines, expected at most "
        f"{MAX_SCRIPT_CODE_LINES}"
    )
    assert "import " not in text and "require(" not in text, (
        "the share script must not depend on anything"
    )


@pytest.mark.static
def test_the_script_copies_with_a_fallback_and_gates_native_share():
    """Clipboard API first with a textarea fallback; Web Share only."""
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
    assert "navigator.share" in text, (
        "the script must offer the Web Share API where the browser has it"
    )
    assert "data-share-native-item" in text and "hidden" in text, (
        "the native-share row must stay hidden without `navigator.share`"
    )


@pytest.mark.static
def test_the_share_script_is_linked_with_the_cache_version_token():
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
def test_the_share_style_keeps_targets_focus_and_no_shift():
    """44px minimum targets, reserved confirmation space, hidden wins."""
    import conftest

    scss = conftest.custom_styles_text()
    assert ".share__status" in scss, (
        "the share row needs its own style block in the custom styles"
    )
    for selector in (".share__button", ".share__link"):
        blocks = re.findall(re.escape(selector) + r"[^{]*\{([^}]*)\}", scss)
        assert blocks, f"{selector} has no rule in the custom styles"
        merged = " ".join(blocks)
        assert "min-width: 44px" in merged and "min-height: 44px" in merged, (
            f"{selector} must keep a 44px minimum touch target"
        )
    assert "min-height" in scss.split(".share__status", 1)[1].split("}", 1)[0], (
        "the confirmation line must reserve its height so the feedback "
        "never shifts the layout"
    )
    assert ".share__item[hidden]" in scss, (
        "the stylesheet must keep `hidden` winning over the control layout, "
        "or unsupported browsers would show a dead native-share button"
    )
    assert "button:focus-visible" in scss, (
        "#87's focus rule covers buttons, so the share buttons never go dark"
    )


# --- build guards (need Ruby; no browser) ----------------------------------


def _canonical_url(path):
    config = _read(REPO_ROOT / "_config.yml")
    site_url = re.search(r'^url:\s*"([^"]+)"', config, re.M).group(1)
    prefix = "vi/" if path.parts[0] == "vi" else ""
    rest = "/".join(path.parts[1:] if prefix else path.parts)
    return f"{site_url}/{prefix}{rest}"


def test_the_row_renders_in_both_languages(built_site):
    en = _share_section(_read(built_site / EN_POST_REL))
    assert f">{HEADING_EN}<" in en and f">{COPY_EN}<" in en
    assert HEADING_VI not in en and COPY_VI not in en

    vi = _share_section(_read(built_site / VI_POST_REL))
    assert f">{HEADING_VI}<" in vi and f">{COPY_VI}<" in vi
    assert f">{COPY_EN}<" not in vi


def test_the_built_row_links_the_canonical_url(built_site):
    for rel in (EN_POST_REL, VI_POST_REL):
        section = _share_section(_read(built_site / rel))
        canonical = _canonical_url(rel)
        assert f'data-share-url="{canonical}"' in section, (
            f"{rel}: the copy button must carry the canonical URL {canonical}"
        )
        assert canonical in section, (
            f"{rel}: the intent links must carry the canonical post URL"
        )
        assert "twitter.com/intent/tweet?url=" in section
        assert "facebook.com/sharer/sharer.php?u=" in section
        assert "linkedin.com/sharing/share-offsite/?url=" in section


def test_no_share_row_leaves_the_post_pages(built_site):
    """Home, tag and static pages stay share-free."""
    pages = ["index.html", "vi/index.html", "tags/index.html"]
    pages.extend(
        path.relative_to(built_site).as_posix()
        for path in sorted(built_site.glob("tags/*/index.html"))[:1]
    )
    pages.extend(["about/index.html", "resume/index.html"])
    for page in pages:
        assert (built_site / page).is_file(), f"{page} is missing"
        assert 'class="share"' not in _read(built_site / page), (
            f"{page} renders a share row: post pages only (#222)"
        )


def test_no_external_script_is_shipped(built_site):
    for rel in (EN_POST_REL, VI_POST_REL):
        html = _read(built_site / rel)
        assert not re.search(r'<script[^>]+src="https?://', html), (
            f"{rel} loads a third-party script: sharing must stay "
            "tracker-free (#222)"
        )


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    text = _read(built_site / EN_POST_REL)
    match = re.search(r'<script src="(/assets/js/share\.js\?v=([^"]+))"', text)
    assert match, "the post page does not link the share script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


def test_the_intent_links_work_without_js(built_site):
    """Progressive enhancement: the links are in the built markup."""
    for rel in (EN_POST_REL, VI_POST_REL):
        section = _share_section(_read(built_site / rel))
        assert section.count('class="share__link"') == 3
        assert 'data-share-native-item hidden' in section, (
            "the native-share row must ship hidden (JS reveals it)"
        )
        assert 'data-share-copy-item hidden' in section, (
            "the copy-link item must ship hidden (JS reveals it, #244)"
        )


def test_the_built_row_falls_back_to_a_visible_post_link(built_site):
    """No-JS readers get the canonical URL as a plain link (#244)."""
    for rel, label in (
        (EN_POST_REL, POST_LINK_EN),
        (VI_POST_REL, POST_LINK_VI),
    ):
        section = _share_section(_read(built_site / rel))
        canonical = _canonical_url(rel)
        assert "<noscript>" in section, (
            f"{rel}: the share row must ship a noscript fallback"
        )
        assert f">{label}:" in section, (
            f"{rel}: the fallback must carry the localized label {label!r}"
        )
        match = re.search(
            r'<a class="share__fallback-link" href="([^"]+)">([^<]+)</a>',
            section,
        )
        assert match, f"{rel}: the fallback must link the post URL"
        assert match.group(1) == canonical and match.group(2) == canonical, (
            f"{rel}: the fallback link must show the canonical URL "
            f"{canonical}, got href={match.group(1)!r} "
            f"text={match.group(2)!r}"
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
        # outright, so the click-to-copy tests skip there (#209).
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


def _post_path(rel):
    return "/" + "/".join(rel.parts)


def _needs_clipboard(browser_name):
    if browser_name == "webkit":
        pytest.skip(
            "headless WebKit denies navigator.clipboard (NotAllowedError) and "
            "Playwright grants no clipboard permission on WebKit, so the "
            "clipboard read-back cannot run there (#209); the row, its "
            "localization and the copied feedback still run on "
            "Chromium/Firefox"
        )


def test_without_js_no_copy_button_but_intents_and_fallback(
    built_site_url, browser
):
    """JS disabled: no dead copy control, intents + URL fallback work (#244)."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        for rel, copy_label, link_label in (
            (EN_POST_REL, COPY_EN, POST_LINK_EN),
            (VI_POST_REL, COPY_VI, POST_LINK_VI),
        ):
            plain.goto(
                built_site_url.rstrip("/") + _post_path(rel),
                wait_until="load",
            )
            assert plain.locator("[data-share-copy-item]").is_hidden(), (
                f"{rel}: the copy-link item must stay hidden without JS"
            )
            assert plain.get_by_role("button", name=copy_label).count() == 0, (
                f"{rel}: no dead {copy_label!r} button without JS"
            )
            fallback = plain.get_by_role("link", name=_canonical_url(rel))
            assert fallback.count() == 1 and fallback.first.is_visible(), (
                f"{rel}: the canonical URL must stay visible without JS"
            )
            assert (
                link_label in (plain.locator(".share__fallback").text_content() or "")
            ), f"{rel}: the fallback must carry the label {link_label!r}"
            assert plain.locator(".share__link").count() == 3, (
                f"{rel}: the three intent links must work without JS"
            )
    finally:
        context.close()


def test_copy_writes_the_canonical_url_and_confirms(built_site_url, page, browser_name):
    _needs_clipboard(browser_name)
    canonical = _canonical_url(EN_POST_REL)
    page.goto(built_site_url.rstrip("/") + _post_path(EN_POST_REL), wait_until="load")

    copy = page.get_by_role("button", name=COPY_EN)
    assert copy.count() == 1, f"expected one {COPY_EN!r} button, got {copy.count()}"
    copy.first.click()
    page.wait_for_function(
        f"() => document.querySelector('.share__copy').textContent === {DONE_EN!r}",
        timeout=10_000,
    )
    assert page.evaluate("() => navigator.clipboard.readText()") == canonical
    status = page.locator(".share__status")
    assert status.get_attribute("role") == "status"
    assert status.text_content() == DONE_EN


def test_the_vietnamese_row_copies_with_localized_labels(
    built_site_url, page, browser_name
):
    _needs_clipboard(browser_name)
    canonical = _canonical_url(VI_POST_REL)
    page.goto(built_site_url.rstrip("/") + _post_path(VI_POST_REL), wait_until="load")

    copy = page.get_by_role("button", name=COPY_VI)
    assert copy.count() == 1, (
        f"the Vietnamese row must label its button {COPY_VI!r}, got "
        f"{copy.count()}"
    )
    assert page.get_by_role("button", name=COPY_EN).count() == 0
    assert page.get_by_role("heading", name=HEADING_VI).count() == 1

    copy.first.click()
    page.wait_for_function(
        f"() => document.querySelector('.share__copy').textContent === {DONE_VI!r}",
        timeout=10_000,
    )
    assert page.evaluate("() => navigator.clipboard.readText()") == canonical
    assert page.locator(".share__status").text_content() == DONE_VI


def test_intent_links_point_at_the_post(built_site_url, page):
    canonical = _canonical_url(EN_POST_REL)
    page.goto(built_site_url.rstrip("/") + _post_path(EN_POST_REL), wait_until="load")

    for name, host in (
        (X_EN, "twitter.com/intent/tweet"),
        ("Share on Facebook", "facebook.com/sharer/sharer.php"),
        ("Share on LinkedIn", "linkedin.com/sharing/share-offsite"),
    ):
        link = page.get_by_role("link", name=name)
        assert link.count() == 1, f"expected one {name!r} link"
        href = link.first.get_attribute("href")
        assert host in href and canonical in href, (
            f"{name!r} must share the canonical post URL, got {href!r}"
        )
        assert link.first.get_attribute("target") == "_blank"
        assert "noopener" in (link.first.get_attribute("rel") or "")


def test_native_share_stays_hidden_without_the_api(built_site_url, page):
    """No `navigator.share` on desktop: the row ships no dead control."""
    page.goto(built_site_url.rstrip("/") + _post_path(EN_POST_REL), wait_until="load")
    page.wait_for_selector(".share__copy", state="visible", timeout=10_000)
    assert page.locator("[data-share-native-item]").is_hidden(), (
        "the native-share row must stay hidden where `navigator.share` "
        "is missing"
    )


def test_native_share_uses_the_api_where_present(built_site_url, browser):
    """With `navigator.share` stubbed, the button appears and shares."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.add_init_script(
        script="window.__shared = null; "
        "Object.defineProperty(Navigator.prototype, 'share', { "
        "value: function (data) { window.__shared = data; "
        "return Promise.resolve(); }, configurable: true });"
    )
    try:
        stub = context.new_page()
        stub.route(
            "**/*",
            lambda route: (
                route.continue_()
                if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost")
                else route.abort()
            ),
        )
        stub.goto(built_site_url.rstrip("/") + _post_path(EN_POST_REL), wait_until="load")
        native = stub.get_by_role("button", name=NATIVE_EN)
        assert native.count() == 1, "the native-share button must appear"
        assert stub.locator("[data-share-native-item]").is_visible()
        native.first.click()
        stub.wait_for_function("() => window.__shared !== null", timeout=10_000)
        shared = stub.evaluate("() => window.__shared")
        assert shared["url"] == _canonical_url(EN_POST_REL)
    finally:
        context.close()


def test_the_row_keeps_targets_focus_and_layout(built_site_url, browser, browser_name):
    """44px targets at 375px, visible focus, reserved status, no overflow."""
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
        narrow.goto(
            built_site_url.rstrip("/") + _post_path(EN_POST_REL), wait_until="load"
        )
        narrow.wait_for_selector(".share__copy", state="visible", timeout=10_000)
        for selector in (".share__copy", ".share__link"):
            for box in narrow.locator(selector).evaluate_all(
                "els => els.map(e => { const r = e.getBoundingClientRect(); "
                "return {w: r.width, h: r.height}; })"
            ):
                assert box["w"] >= 44 and box["h"] >= 44, (
                    f"{selector} must keep a 44px minimum touch target, got "
                    f"{box['w']:.0f}x{box['h']:.0f}"
                )
        copy = narrow.locator(".share__copy").first
        copy.focus()
        outline = narrow.evaluate(
            "() => { const s = getComputedStyle("
            "document.querySelector('.share__copy')); "
            "return {style: s.outlineStyle, width: s.outlineWidth}; }"
        )
        assert outline["style"] != "none" and outline["width"] != "0px", (
            f"keyboard focus on the copy button must stay visible, got {outline}"
        )
        status_height = narrow.locator(".share__status").evaluate(
            "el => getComputedStyle(el).minHeight"
        )
        assert status_height != "0px", (
            "the confirmation line must reserve its space (no layout shift)"
        )
        overflow = narrow.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 0, (
            f"the share row must not add horizontal overflow at 375px (+{overflow}px)"
        )
    finally:
        context.close()
