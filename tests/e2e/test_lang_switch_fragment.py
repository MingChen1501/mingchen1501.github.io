"""Guards for #145: the language switch keeps the reading position.

EN/VI heading anchor ids differ (kramdown auto-ids from different-language
headings), so `assets/js/lang-switch.js` progressively enhances
`.lang-switcher` on posts: the href carries the section index
(`?section=N`, plus the real `#fragment`) and the counterpart scrolls to
its Nth section when the fragment has no match there. Without JS the
switcher keeps today's behaviour (counterpart top).

Guarded here:

- the script exists, stays tiny and has no dependency (static);
- it enhances `.lang-switcher` from `.post-content` section headings only,
  carries `?section=N` + the fragment, falls back to the plain counterpart
  URL, never redirects, and drops the query after landing (static);
- the template links it through the `?v=` build token like every other
  fixed-URL asset (#61), without touching the switcher markup, hreflang
  alternates, or canonicals (static + rendered);
- the built post pages ship a fragment/query-free switcher href (no-JS
  degradation is today's top landing) with hreflang/canonical intact
  (build);
- switching mid-article EN->VI and VI->EN lands on the same section index
  with a clean URL, while a bogus index or fragment degrades to the top
  with no page errors (browser, on the long Internet post pair).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "lang-switch.js"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
SWITCHER_INCLUDE = REPO_ROOT / "_includes" / "lang-switcher.html"
ALTERNATES_INCLUDE = REPO_ROOT / "_includes" / "lang-alternates.html"

SCRIPT_PATH = "/assets/js/lang-switch.js"

# Two-sided work (source href + counterpart landing) in one file, still
# fetched deferred on every page: keep it small.
MAX_SCRIPT_BYTES = 4096
MAX_SCRIPT_CODE_LINES = 95

EN_POST_PATH = "2022/12/25/explaining-the-internet.html"
VI_POST_PATH = "vi/2022/12/25/gioi-thieu-ve-internet.html"
SECTION_SELECTOR = ".post-content h2[id], .post-content h3[id]"


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_switch_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the lang-switch script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the lang-switch script has {len(code)} code lines, expected at most "
        f"{MAX_SCRIPT_CODE_LINES}"
    )
    assert "import " not in text and "require(" not in text, (
        "the lang-switch script must not depend on anything"
    )


@pytest.mark.static
def test_the_script_enhances_the_switcher_from_post_sections():
    text = _read(SCRIPT)
    assert ".lang-switcher" in text
    assert ".post-content h2[id]" in text and ".post-content h3[id]" in text
    # getElementById (never a CSS selector): non-ASCII kramdown ids need no
    # escaping.
    assert "getElementById" in text
    assert "querySelector('#'" not in text and 'querySelector("#"' not in text


@pytest.mark.static
def test_the_script_carries_the_section_and_falls_back_to_top():
    text = _read(SCRIPT)
    # The position rides along as `?section=N` plus the real fragment.
    assert "section" in text
    assert "'?'" in text or '"?"' in text
    assert "'#'" in text or '"#"' in text
    # No match / top of page restores the plain counterpart URL.
    assert "getAttribute('href')" in text or 'getAttribute("href")' in text
    # Never a redirect or a history entry: only a silent cleanup.
    assert "location.href =" not in text and "location.assign" not in text
    assert "location.replace" not in text and "window.open" not in text
    assert "replaceState" in text
    # Defer-safe like the other fixed-URL scripts, via the shared helper.
    assert "SiteUtils" in text and "onReady" in text


@pytest.mark.static
def test_the_switch_script_is_linked_with_the_cache_version_token():
    html = _read(SUB_FOOTER)
    assert f"{SCRIPT_PATH}?v=" in html, (
        f"{SUB_FOOTER.relative_to(REPO_ROOT)} must link {SCRIPT_PATH} with "
        "the `?v=` build token, like every other fixed-URL asset (#61)"
    )
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER))


@pytest.mark.static
def test_the_static_switcher_and_alternates_are_untouched():
    # The position is a runtime enhancement: no fragment or query is baked
    # into the markup, and the link semantics stay exactly as #122 left them.
    switcher = _read(SWITCHER_INCLUDE)
    assert "section" not in switcher
    assert 'hreflang="{{ switch_other }}"' in switcher
    assert 'href="{{ switch_url | relative_url }}"' in switcher
    # hreflang alternates + seo-tag canonicals are intact: the script must
    # not touch them (it only scrolls and drops its own query).
    alternates = _read(ALTERNATES_INCLUDE)
    assert 'hreflang="en"' in alternates
    assert 'hreflang="vi"' in alternates
    assert 'hreflang="x-default"' in alternates
    assert "section" not in alternates and "replaceState" not in alternates


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    text = _read(built_site / "index.html")
    match = re.search(r'<script src="(/assets/js/lang-switch\.js\?v=([^"]+))"', text)
    assert match, "the home page does not link the lang-switch script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


def test_built_posts_keep_a_plain_switcher_href_with_intact_seo(built_site):
    for rel in (EN_POST_PATH, VI_POST_PATH):
        page = built_site / rel
        assert page.is_file(), f"expected a built post at {page}"
        text = _read(page)
        match = re.search(r'<a class="lang-switcher".*?</a>', text, re.S)
        assert match, f"/{rel} renders no language switcher"
        tag = match.group(0)
        href = re.search(r'href="([^"]+)"', tag).group(1)
        # No-JS degradation is today's behaviour: a plain counterpart URL
        # with no fragment or query, so the reader lands at the top.
        assert "?" not in href and "#" not in href, (
            f"/{rel} bakes a position into the switcher href {href!r}"
        )
        assert 'hreflang="' in tag
        # hreflang alternates + self canonical survive the change.
        assert 'hreflang="en"' in text and 'hreflang="vi"' in text
        assert 'rel="canonical"' in text


# --- browser guards (need Ruby + a browser) ---------------------------------


def _page(browser, built_site_url):
    """A same-origin-only page that records JS page errors."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    origin = urlparse(built_site_url).netloc
    page.route(
        "**/*",
        lambda route: route.continue_()
        if urlparse(route.request.url).netloc == origin
        else route.abort(),
    )
    errors = []
    page.on("pageerror", lambda err: errors.append(err))
    try:
        yield page, errors
    finally:
        context.close()


def _section_ids(page):
    return page.evaluate(
        "() => Array.from(document.querySelectorAll("
        f"{SECTION_SELECTOR!r})).map((h) => h.id)"
    )


def _nearest_section(page):
    """Index of the section the viewport sits in (mirrors the script)."""
    return page.evaluate(
        "() => { const ix = Array.from(document.querySelectorAll("
        f"{SECTION_SELECTOR!r})); const y = window.scrollY; let best = -1; "
        "for (let i = 0; i < ix.length; i++) { "
        "if (ix[i].getBoundingClientRect().top + y <= y + 120) best = i; "
        "else break; } return best; }"
    )


def _scroll_to_section(page, index):
    page.evaluate(
        "(i) => document.querySelectorAll("
        f"{SECTION_SELECTOR!r})[i].scrollIntoView()",
        index,
    )
    page.wait_for_timeout(400)  # let the rAF-throttled href refresh run
    assert _nearest_section(page) == index


def _switch_language(page, built_site_url, path):
    page.goto(f"{built_site_url}/{path}", wait_until="load")
    page.wait_for_selector(".lang-switcher", state="visible", timeout=10_000)
    return page.locator(".lang-switcher")


@pytest.mark.parametrize(
    "source,target,index",
    [(EN_POST_PATH, VI_POST_PATH, 6), (VI_POST_PATH, EN_POST_PATH, 3)],
)
def test_switching_mid_article_keeps_the_section(
    source, target, index, built_site_url, browser
):
    """#145: leaving section N lands on section N with a clean URL."""
    for page, errors in _page(browser, built_site_url):
        _switch_language(page, built_site_url, source)
        assert len(_section_ids(page)) > index
        _scroll_to_section(page, index)
        href = page.get_attribute(".lang-switcher", "href")
        assert f"?section={index}#" in href, (
            f"the switcher href {href!r} carries no section {index}"
        )
        with page.expect_navigation(wait_until="load", timeout=15_000):
            # A DOM click: Playwright's locator click would first scroll the
            # header pill into view (moving the reader to the top and
            # correctly clearing the carried section), which is not what a
            # real mid-article click does.
            page.evaluate("() => document.querySelector('.lang-switcher').click()")
        assert urlparse(page.url).path == f"/{target}", (
            f"the switch led to {page.url}, expected /{target}"
        )
        # Same section index, adopted as the real counterpart anchor, and
        # the transport query is gone (canonicals stay clean).
        assert urlparse(page.url).query == ""
        target_ids = _section_ids(page)
        landed = page.evaluate(
            "() => decodeURIComponent(location.hash.slice(1))"
        )
        assert landed == target_ids[index]
        assert _nearest_section(page) == index
        assert not errors, f"JS page errors after the switch: {errors}"


@pytest.mark.parametrize(
    "query,index",
    [("?section=99", -1), ("?section=2#no-such-anchor", 2)],
)
def test_unusable_positions_degrade_to_today(built_site_url, browser, query, index):
    """#145: a bogus index lands at top; a bogus fragment still finds N."""
    for page, errors in _page(browser, built_site_url):
        _switch_language(page, built_site_url, EN_POST_PATH + query)
        page.wait_for_timeout(400)
        assert urlparse(page.url).query == "", (
            f"the transport query survived in {page.url}"
        )
        if index == -1:
            assert page.evaluate("() => window.scrollY") < 120
            assert page.evaluate("() => location.hash") == ""
        else:
            target_ids = _section_ids(page)
            landed = page.evaluate(
                "() => decodeURIComponent(location.hash.slice(1))"
            )
            assert landed == target_ids[index]
            assert _nearest_section(page) == index
        assert not errors, f"JS page errors on a degraded landing: {errors}"
