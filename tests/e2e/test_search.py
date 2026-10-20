"""Guards for #221: offline client-side search (EN + VI, no plugins).

The search page filters a build-time JSON index entirely in the reader's
browser: no Jekyll plugin (GitHub Pages builds with `--safe`), no external
service, no SDK. `_includes/search.html` renders the accessible shell (label,
input, guidance, `aria-live` status, results list, no-results state) in the
page language on `/search/` (`search.md`) and `/vi/tim-kiem/`
(`vi/search.md`); `assets/js/search.js` lazy-loads `search.json` only there
and ranks title hits above description/tag hits, same-language first.

Guarded here:

- static (no Ruby, no browser): the index template emits exactly the six
  metadata fields per post (never the body), over both post collections with
  drafts excluded and the `site.vi_posts` nil-guard the upstream theme-dev
  build needs; both pages carry lang/ref/permalink and include the shell;
  the shell wires label/input/status/results plus the `?v=` build token on
  the script and the index URL (#61); the script stays vanilla, tiny and
  offline; nothing outside the search shell loads the script or the index;
  both navs link the page;
- build (needs Ruby): `search.json` parses, covers every published post per
  language with all six fields, and every URL resolves to a built file; both
  pages render with a numeric version token and switch to each other;
- browser (needs Ruby + a browser): a fixture query returns the expected
  post as the top result on both language paths (including a diacritics-free
  Vietnamese query); empty query shows guidance; a nonsense query shows the
  localized no-results state with the count announced via the live region;
  the control is keyboard-operable (desktop-only autofocus, Enter, Escape
  (#243)); neither page scrolls sideways at 375px or 1280px; typing mirrors
  `?q=` into the URL and reopening it reproduces the results (#243).

The browser guards use the session's shared `built_site`/`built_site_url`
fixtures from `conftest.py` (one `bundle exec jekyll build` for the whole
suite, served once over loopback HTTP), exactly like the #47/#58 guards.
Third-party requests are aborted — the local `style.css` fully defines the
layout.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_TEMPLATE = REPO_ROOT / "search.json"
SEARCH_INCLUDE = REPO_ROOT / "_includes" / "search.html"
SEARCH_SCRIPT = REPO_ROOT / "assets" / "js" / "search.js"
SEARCH_SCSS = REPO_ROOT / "_sass" / "minima" / "custom" / "_search.scss"
SCSS_INDEX = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
SUB_FOOTER_INCLUDE = REPO_ROOT / "_includes" / "sub-footer.html"
HEADER_INCLUDE = REPO_ROOT / "_includes" / "header.html"
CONFIG = REPO_ROOT / "_config.yml"
EN_PAGE = REPO_ROOT / "search.md"
VI_PAGE = REPO_ROOT / "vi" / "search.md"

EN_PATH = "/search/"
VI_PATH = "/vi/tim-kiem/"

# The script ships on every search page view; keep it dependency-free and
# small (the nav-toggle guard pins 2KB/40 lines for a smaller script; search
# owns ranking + rendering, so it gets headroom, not a blank cheque).
MAX_SCRIPT_BYTES = 8192

# Fixture queries (must stay distinctive as the archive grows): "fedora"
# matches the EN/VI Fedora pair on both paths, so the top result proves the
# same-language ranking; "bai bien" is the VI beach-post title stripped of
# diacritics, proving the fold; "beach" is EN-only.
EN_FEDORA_POST = "/2026/01/01/switching-from-windows-11-to-fedora.html"
VI_FEDORA_POST = "/vi/2026/01/01/migrate-windows-11-to-fedora.html"
EN_BEACH_POST = "/2026/10/17/real-world-agent-orchestration-with-free-opencode.html"
VI_BEACH_POST = "/vi/2026/10/17/agent-orchestration-opencode-free.html"
NONSENSE_QUERY = "zzzqqqxk"

REQUIRED_FIELDS = ("title", "description", "url", "lang", "tags", "date")


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    text = _read(path)
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert match, f"{path.relative_to(REPO_ROOT)} has no front matter"
    return yaml.safe_load(match.group(1))


def _published_posts(posts_dir):
    """Published posts of one source directory (mirrors the index query)."""
    posts = []
    for path in sorted(posts_dir.glob("*.md")):
        front_matter = _front_matter(path)
        if front_matter.get("published") is False:
            continue
        if front_matter.get("draft") is True:
            continue
        posts.append((path, front_matter))
    return posts


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_search_index_template_emits_post_metadata_only():
    text = _read(INDEX_TEMPLATE)
    front_matter = _front_matter(INDEX_TEMPLATE)
    assert front_matter.get("layout") in (None, "null", "nil"), (
        "the index must render raw JSON, not wrapped in a layout"
    )
    assert front_matter.get("permalink") == "/search.json"
    assert front_matter.get("sitemap") is False, (
        "search.json is data, not a page: keep it out of sitemap.xml"
    )
    # Both post collections feed the index; drafts are filtered like
    # `vi/feed.xml` does.
    assert "for post in search_en" in text or "for post in site.posts" in text
    assert "site.posts" in text
    assert "site.vi_posts" in text
    assert 'where_exp' in text and 'draft != true' in text
    # The upstream theme-dev build leaves `site.vi_posts` undefined
    # (`script/cibuild`); the template must degrade instead of crashing.
    assert re.search(r"assign \w+ = site\.vi_posts", text), (
        "site.vi_posts must be read through a nil-guarded variable"
    )
    assert "== nil" in text
    # Exactly the six metadata fields, JSON-escaped; bodies must never leak
    # into the index (it has to stay small, #221).
    for field in REQUIRED_FIELDS:
        assert f'"{field}":' in text, f"the index must emit {field!r} per post"
    assert "jsonify" in text
    assert "post.content" not in text, "the index must not embed post bodies"
    assert "post.excerpt" not in text, "the index must not embed excerpts"


@pytest.mark.static
def test_search_pages_exist_in_both_languages_with_shared_ref():
    for path, lang, permalink in (
        (EN_PAGE, "en", "/search/"),
        (VI_PAGE, "vi", "/vi/tim-kiem/"),
    ):
        assert path.is_file(), f"{path.relative_to(REPO_ROOT)} is missing"
        front_matter = _front_matter(path)
        assert front_matter.get("layout") == "page"
        assert front_matter.get("lang") == lang
        assert front_matter.get("ref") == "search", (
            "both search pages must share `ref: search` so the switcher, "
            "hreflang and sitemap alternates link them as counterparts"
        )
        assert front_matter.get("permalink") == permalink
        assert front_matter.get("title"), "the search page needs a nav title"
        assert front_matter.get("description"), (
            "the search page needs a description for jekyll-seo-tag"
        )
    assert "include search.html" in _read(EN_PAGE)
    assert "include search.html" in _read(VI_PAGE)


@pytest.mark.static
def test_search_shell_is_accessible_and_versioned():
    html = _read(SEARCH_INCLUDE)
    # Label + input association, search landmark, live status region,
    # results list and a hidden no-results paragraph for the script.
    assert re.search(r'<label[^>]*for="site-search-input"', html)
    assert re.search(r'<input[^>]*id="site-search-input"[^>]*>', html)
    assert 'name="q"' in html, "the input keeps `?q=` for no-JS submits"
    assert 'role="search"' in html
    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
    assert 'id="site-search-results"' in html
    assert 'id="site-search-empty"' in html
    assert "hidden" in html
    # Language-aware shell: every dynamic string travels as a data
    # attribute so the script stays language-agnostic.
    for attr in (
        "data-index-url",
        "data-lang",
        "data-found-one",
        "data-found-many",
        "data-no-results",
        "data-load-error",
    ):
        assert attr in html, f"the shell must expose {attr} to the script"
    # Cache versioning (#61): the script and the lazily fetched index carry
    # the build token, and no external origin is ever touched.
    assert "/assets/js/search.js?v=" in html
    assert "/search.json" in html and "?v=" in html
    assert re.search(r"site\.time", html)
    assert "http://" not in html and "https://" not in html, (
        "the search shell must not reference any external origin"
    )


@pytest.mark.static
def test_search_script_stays_vanilla_tiny_and_offline():
    assert SEARCH_SCRIPT.is_file(), "assets/js/search.js is missing"
    text = _read(SEARCH_SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the search script ships on the search page: keep it small"
    )
    assert "import " not in text and "require(" not in text, (
        "the search script must not depend on anything"
    )
    assert "http://" not in text and "https://" not in text, (
        "the search script must never contact an external service"
    )
    # The behaviours the browser guards pin: diacritics folding (including
    # `đ`), AND matching with title-first scoring, same-language ranking,
    # `?q=` deep-links, no-JS-submit interception and Escape-to-clear.
    assert "normalize(" in text and "đ" in text
    assert "preventDefault" in text
    assert "URLSearchParams" in text
    assert "Escape" in text
    assert "fetch(" in text
    assert "data-loaded" in text, (
        "the script must flag the index load so tests can wait on it"
    )


@pytest.mark.static
def test_search_243_shareable_url_and_conditional_focus():
    """#243: typed queries mirror into ?q=; focus stays desktop-only."""
    text = _read(SEARCH_SCRIPT)
    # Shareable filtered views without history spam: replaceState on every
    # keystroke/submit, cleared on empty; the language path never changes.
    assert "replaceState" in text, (
        "typing must mirror the query into the URL with history.replaceState"
    )
    assert "pushState" not in text, (
        "the query mirror must not grow the session history"
    )
    assert "searchParams" in text
    assert re.search(r"searchParams\.set\(\s*['\"]q['\"]", text), (
        "the script must write the live query into ?q="
    )
    assert re.search(r"searchParams\.delete\(\s*['\"]q['\"]", text), (
        "clearing the query must drop ?q= so no stale deep link remains"
    )
    # No mobile keyboard-pop: coarse pointers and narrow screens skip the
    # initial focus; the Escape refocus (explicit user intent) stays.
    assert "(pointer: coarse)" in text
    assert "max-width" in text
    assert re.search(
        r"if\s*\(.*[Aa]utofocus.*\)\s*input\.focus\(\)", text
    ), "the initial focus must be conditional, not unconditional"


@pytest.mark.static
def test_search_assets_load_only_on_the_search_page():
    """The index is lazy: no other template may pull the script or the JSON."""
    sub_footer = _read(SUB_FOOTER_INCLUDE)
    assert "search.js" not in sub_footer, (
        "search.js must not load site-wide — only _includes/search.html "
        "links it, so the index is fetched solely on the search page (#221)"
    )
    offenders = []
    for directory in ("_includes", "_layouts"):
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if not path.is_file() or path == SEARCH_INCLUDE:
                continue
            text = _read(path)
            if "search.js" in text or "search.json" in text:
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert not offenders, (
        "only _includes/search.html may reference the search assets: "
        + ", ".join(offenders)
    )


@pytest.mark.static
def test_search_page_is_in_both_navs():
    config = yaml.safe_load(_read(CONFIG))
    assert "search.md" in (config.get("minima", {}).get("nav_pages") or []), (
        "the English nav must link the search page"
    )
    assert "vi/search.md" in _read(HEADER_INCLUDE), (
        "the Vietnamese nav must stay inside /vi/ and link the search page"
    )


@pytest.mark.static
def test_search_styles_exist_and_join_the_cascade():
    assert SEARCH_SCSS.is_file(), "the search SCSS partial is missing"
    scss = _read(SEARCH_SCSS)
    for selector in (".search__input", ".search__results", ".search__empty"):
        assert selector in scss
    assert "minima/custom/search" in _read(SCSS_INDEX), (
        "custom-styles.scss must import the search partial"
    )


# --- build guards (need Ruby; no browser) ----------------------------------


def _built_json(built_site):
    path = built_site / "search.json"
    assert path.is_file(), "the build emits no /search.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"/search.json does not parse: {error}")


def test_search_index_completeness_per_language(built_site):
    entries = _built_json(built_site)
    assert isinstance(entries, list) and entries, "the index must be a non-empty array"
    for entry in entries:
        assert tuple(sorted(entry.keys())) == tuple(sorted(REQUIRED_FIELDS)), (
            f"index entry {entry.get('url')} must carry exactly {REQUIRED_FIELDS}"
        )
        assert entry["title"] and entry["description"] and entry["url"]
        assert entry["lang"] in ("en", "vi")
        assert isinstance(entry["tags"], list) and entry["tags"], (
            f"{entry['url']} must list at least one pillar tag"
        )
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]), (
            f"{entry['url']} carries a malformed date {entry['date']!r}"
        )
    by_lang = {"en": [], "vi": []}
    for entry in entries:
        by_lang[entry["lang"]].append(entry)
    for lang, posts_dir in (("en", REPO_ROOT / "_posts"), ("vi", REPO_ROOT / "_vi_posts")):
        expected = _published_posts(posts_dir)
        got = {entry["url"] for entry in by_lang[lang]}
        assert len(by_lang[lang]) == len(expected), (
            f"the index holds {len(by_lang[lang])} {lang} entries but "
            f"{posts_dir.relative_to(REPO_ROOT)} publishes {len(expected)} posts"
        )
        for _, front_matter in expected:
            assert front_matter["title"] in {entry["title"] for entry in by_lang[lang]}, (
                f"{front_matter['title']!r} is missing from the {lang} index"
            )


def test_search_index_urls_resolve_and_exclude_unpublished(built_site):
    """Every indexed URL is a built file; unpublished posts stay out."""
    entries = _built_json(built_site)
    for entry in entries:
        path = built_site / entry["url"].lstrip("/")
        assert path.is_file(), f"indexed URL {entry['url']} is not in the build"
    indexed_titles = {entry["title"] for entry in entries}
    for posts_dir in (REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"):
        for path, front_matter in _published_posts(posts_dir):
            assert front_matter["title"] in indexed_titles
        for path in sorted(posts_dir.glob("*.md")):
            front_matter = _front_matter(path)
            if front_matter.get("published") is False or front_matter.get("draft") is True:
                assert front_matter.get("title") not in indexed_titles, (
                    f"unpublished {path.name} must not be indexed"
                )


def test_search_pages_render_with_versioned_assets(built_site):
    """Both pages render the shell with a numeric build token (#61)."""
    for rel, lang, counterpart in (
        ("search/index.html", "en", "/vi/tim-kiem/"),
        ("vi/tim-kiem/index.html", "vi", "/search/"),
    ):
        html = _read(built_site / rel)
        assert f'<html lang="{lang}"' in html
        for element in (
            'id="site-search-form"',
            'for="site-search-input"',
            'id="site-search-input"',
            'id="site-search-guidance"',
            'aria-live="polite"',
            'id="site-search-results"',
            'id="site-search-empty"',
        ):
            assert element in html, f"{rel} misses {element}"
        script = re.search(r'<script src="(/assets/js/search\.js\?v=([^"]+))"', html)
        assert script, f"{rel} does not link the search script"
        assert re.fullmatch(r"\d+", script.group(2)), (
            f"{rel} carries a non-numeric version token {script.group(2)!r}"
        )
        index = re.search(r'data-index-url="(/search\.json\?v=([^"]+))"', html)
        assert index, f"{rel} does not version the index URL"
        assert re.fullmatch(r"\d+", index.group(2))
        assert f'href="{counterpart}"' in html, (
            f"{rel} must switch to its {counterpart} counterpart"
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
    page.wait_for_selector("#site-search-input", state="attached", timeout=10_000)
    # The index fetch resolves before any assertion runs.
    page.wait_for_selector("#site-search[data-loaded]", timeout=10_000)
    return page


def _search(page, query):
    page.locator("#site-search-input").fill(query)
    page.wait_for_function(
        "() => document.getElementById('site-search-status').textContent.trim().length > 0"
        " || !document.getElementById('site-search-empty').hidden",
        timeout=10_000,
    )


def _top_href(page):
    return page.evaluate(
        "() => { const first = document.querySelector('#site-search-results .search__item a');"
        " return first ? first.getAttribute('href') : null; }"
    )


@pytest.mark.parametrize(
    "path,query,expected",
    [
        (EN_PATH, "fedora", EN_FEDORA_POST),
        (VI_PATH, "fedora", VI_FEDORA_POST),
        (EN_PATH, "beach", EN_BEACH_POST),
        (VI_PATH, "bai bien", VI_BEACH_POST),
    ],
)
def test_fixture_query_returns_the_expected_post_first(
    path, query, expected, built_site_url, browser
):
    """#221 acceptance: a known title ranks its post top, per language —
    including the diacritics-free Vietnamese query."""
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, path)
        _search(page, query)
        assert _top_href(page) == expected, (
            f"{path} query {query!r}: top result is {_top_href(page)!r}, "
            f"expected {expected!r}"
        )


@pytest.mark.parametrize(
    "path,guidance,no_results",
    [
        (EN_PATH, "Type above to search", "No posts match"),
        (VI_PATH, "Nhập từ khóa ở trên", "Không có bài nào khớp"),
    ],
)
def test_empty_query_shows_guidance_and_nonsense_shows_no_results(
    path, guidance, no_results, built_site_url, browser
):
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, path)
        assert page.locator("#site-search-guidance").is_visible()
        assert guidance in page.locator("#site-search-guidance").inner_text()
        _search(page, NONSENSE_QUERY)
        empty = page.locator("#site-search-empty")
        assert empty.is_visible(), f"{path}: the no-results state never showed"
        assert no_results in empty.inner_text()
        # The same text is announced through the live region.
        status = page.locator("#site-search-status").inner_text().strip()
        assert status, f"{path}: the live region announced nothing"
        assert no_results in status


def test_search_is_keyboard_operable(built_site_url, browser):
    """Autofocus on load, Enter submits without navigating, Escape clears."""
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, EN_PATH)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.id === 'site-search-input'",
            timeout=10_000,
        )
        page.keyboard.type("fedora")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => (document.querySelectorAll('#site-search-results .search__item').length || 0) > 0",
            timeout=10_000,
        )
        assert urlparse(page.url).path == EN_PATH, (
            "Enter must filter in place, not navigate away"
        )
        assert _top_href(page) == EN_FEDORA_POST
        # Tab reaches the first result link from the input.
        page.locator("#site-search-input").focus()
        page.keyboard.press("Tab")
        focused = page.evaluate(
            "() => ({tag: document.activeElement.tagName, "
            "cls: document.activeElement.className})"
        )
        assert focused["tag"] == "A" and "search__link" in focused["cls"], (
            f"Tab from the input must reach a result link, got {focused}"
        )
        # Escape clears back to the guidance state.
        page.locator("#site-search-input").focus()
        page.keyboard.press("Escape")
        assert page.locator("#site-search-input").input_value() == ""
        assert page.locator("#site-search-guidance").is_visible()


@pytest.mark.parametrize("path", [EN_PATH, VI_PATH])
@pytest.mark.parametrize("width", [375, 1280])
def test_search_page_never_scrolls_sideways(path, width, built_site_url, browser):
    for page in _viewport(browser, built_site_url, width):
        _open(page, built_site_url, path)
        _search(page, "orchestration")
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth"
        ), f"{path} scrolls sideways at {width}px"


# --- #243 guards: shareable ?q= + desktop-only focus ------------------------


def _touch_viewport(browser, built_site_url, width=375, height=800):
    """A narrow touch context (phone-like): coarse pointer, small screen."""
    context = browser.new_context(
        viewport={"width": width, "height": height},
        has_touch=True,
        is_mobile=True,
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
        yield page
    finally:
        context.close()


def _active_element_id(page):
    return page.evaluate(
        "() => (document.activeElement && document.activeElement.id) || ''"
    )


@pytest.mark.parametrize(
    "path,expected",
    [(EN_PATH, EN_FEDORA_POST), (VI_PATH, VI_FEDORA_POST)],
)
def test_typing_mirrors_query_and_deep_link_reproduces_results(
    path, expected, built_site_url, browser
):
    """#243: typing writes ?q= (same language path); reopening replays it."""
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, path)
        _search(page, "fedora")
        page.wait_for_function(
            "() => window.location.search.indexOf('q=fedora') !== -1",
            timeout=10_000,
        )
        assert urlparse(page.url).path == path.rstrip("/") + "/", (
            f"{path}: the ?q= mirror must keep the language path"
        )
        assert _top_href(page) == expected
        # The live region keeps announcing through the mirror.
        assert page.locator("#site-search-status").inner_text().strip()
        # A shared link reproduces the same filtered view (incl. no-JS
        # shape: the query arrives as ?q= and prefills the input).
        shared_url = page.url
        reloaded = page.goto(shared_url, wait_until="load")
        assert reloaded is not None and reloaded.status == 200
        page.wait_for_selector("#site-search[data-loaded]", timeout=10_000)
        page.wait_for_function(
            "() => (document.querySelectorAll('#site-search-results .search__item').length || 0) > 0",
            timeout=10_000,
        )
        assert page.locator("#site-search-input").input_value() == "fedora"
        assert _top_href(page) == expected


def test_escape_clears_query_guidance_and_url(built_site_url, browser):
    """#243: Escape restores guidance and removes ?q= (no stale link)."""
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, EN_PATH)
        _search(page, "fedora")
        page.wait_for_function(
            "() => window.location.search.indexOf('q=fedora') !== -1",
            timeout=10_000,
        )
        page.locator("#site-search-input").focus()
        page.keyboard.press("Escape")
        assert page.locator("#site-search-input").input_value() == ""
        assert page.locator("#site-search-guidance").is_visible()
        assert "q=" not in urlparse(page.url).query, (
            "Escape must remove ?q= from the address bar"
        )
        # Clearing the field by hand drops ?q= the same way.
        _search(page, "fedora")
        page.wait_for_function(
            "() => window.location.search.indexOf('q=fedora') !== -1",
            timeout=10_000,
        )
        page.locator("#site-search-input").fill("")
        page.wait_for_function(
            "() => window.location.search.indexOf('q=') === -1",
            timeout=10_000,
        )
        assert page.locator("#site-search-guidance").is_visible()


def test_initial_focus_is_desktop_only(built_site_url, browser):
    """#243: desktop focuses the field; a narrow touch screen does not."""
    for page in _viewport(browser, built_site_url, 1280):
        _open(page, built_site_url, EN_PATH)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.id === 'site-search-input'",
            timeout=10_000,
        )
    for page in _touch_viewport(browser, built_site_url):
        _open(page, built_site_url, EN_PATH)
        page.wait_for_selector("#site-search[data-loaded]", timeout=10_000)
        assert _active_element_id(page) != "site-search-input", (
            "a phone-sized touch screen must not steal focus on load"
        )
