"""Guards for #246: one shared JS helper instead of three copy-pasted blocks.

Seven deferred scripts re-implemented the same primitives inline: a
clipboard textarea + ``execCommand`` fallback (``copy-code.js``,
``share.js``), a ``document.readyState === 'loading'`` guard (all seven),
and a ``documentElement.lang`` Vietnamese sniff (``copy-code.js``,
``lightbox.js``). They now share ``assets/js/site-utils.js``
(``window.SiteUtils`` with ``copyText`` / ``onReady`` / ``isVietnamese``),
loaded first with the same ``?v=`` build token as every other fixed-URL
asset (#61).

Guarded here:

- the helper exists, stays tiny and dependency-free (static);
- it exposes exactly the three shared primitives on ``window.SiteUtils``
  (static);
- the duplicated blocks are gone: the guard, the fallback and the sniff
  live only in the helper, and every call site uses it (static);
- the helper loads before its users with the ``?v=`` build token, both
  site-wide (``sub-footer.html``) and on the search pages (``search.html``,
  whose script tag runs before the sub-footer ones) (static + built);
- total ``assets/js`` bytes do not grow (static).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "assets" / "js" / "site-utils.js"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
SEARCH_INCLUDE = REPO_ROOT / "_includes" / "search.html"
JS_DIR = REPO_ROOT / "assets" / "js"

HELPER_PATH = "/assets/js/site-utils.js"

# The helper is fetched on every page load: it must stay smaller than the
# ~1.2KB of duplication it removes, so total JS bytes shrink.
MAX_HELPER_BYTES = 1536
MAX_HELPER_CODE_LINES = 45

# Total JS payload after the dedupe (10 files, `wc -c`): it grows only by
# deliberate feature additions. #258 adds `giscus-theme.js` (~3KB), which
# loads solely on Giscus comment pages — non-comment pages fetch nothing new.
MAX_TOTAL_JS_BYTES = 38482

READY_CONSUMERS = (
    "copy-code.js",
    "lang-switch.js",
    "lazy-load.js",
    "lightbox.js",
    "reading-progress.js",
    "search.js",
    "share.js",
)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _code_lines(text):
    return [
        line
        for line in text.splitlines()
        if line.strip()
        and not line.strip().startswith(("/*", "*", "//"))
    ]


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_helper_exists_and_stays_tiny():
    assert HELPER.is_file(), f"{HELPER.relative_to(REPO_ROOT)} is missing"
    text = _read(HELPER)
    assert len(text.encode("utf-8")) <= MAX_HELPER_BYTES, (
        "the shared helper must stay smaller than the duplication it removes"
    )
    assert len(_code_lines(text)) <= MAX_HELPER_CODE_LINES, (
        "the shared helper grows past its budget"
    )
    assert "import " not in text and "require(" not in text, (
        "the shared helper must not depend on anything"
    )


@pytest.mark.static
def test_the_helper_exposes_the_three_primitives():
    """`window.SiteUtils` carries copy, ready and lang-sniff, nothing more."""
    text = _read(HELPER)
    assert "window.SiteUtils" in text, (
        "the helper must publish its API as `window.SiteUtils`"
    )
    for name in ("onReady", "isVietnamese", "copyText"):
        assert name in text, f"the helper must expose `{name}`"


@pytest.mark.static
def test_the_helper_implements_each_primitive():
    """Same shapes the inline copies had: no behaviour change."""
    text = _read(HELPER)
    assert "document.readyState" in text and "DOMContentLoaded" in text, (
        "the helper must defer while the document is still loading"
    )
    assert "document.documentElement" in text and "lang" in text, (
        "the helper must sniff the page language from `<html lang>`"
    )
    assert "navigator.clipboard" in text and "writeText" in text, (
        "the helper must copy through the Clipboard API first"
    )
    assert "textarea" in text and "execCommand" in text, (
        "the helper must fall back to a textarea + execCommand copy"
    )


def _code_text(text):
    """Strip block/line comments so prose never trips the dedupe pins."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(
        line.split("//", 1)[0]
        for line in text.splitlines()
        if "://" not in line
    )


@pytest.mark.static
def test_the_duplicated_blocks_live_only_in_the_helper():
    """Every former call site uses the helper; no inline copy remains."""
    for name in sorted(p.name for p in JS_DIR.glob("*.js")):
        text = _code_text(_read(JS_DIR / name))
        if name == "site-utils.js":
            continue
        assert "document.readyState" not in text, (
            f"{name} still carries its own DOM-ready guard: "
            "use `SiteUtils.onReady` instead (#246)"
        )
        assert "execCommand" not in text, (
            f"{name} still carries its own clipboard fallback: "
            "use `SiteUtils.copyText` instead (#246)"
        )
        assert "documentElement.lang" not in text, (
            f"{name} still carries its own language sniff: "
            "use `SiteUtils.isVietnamese` instead (#246)"
        )
    for name in READY_CONSUMERS:
        text = _read(JS_DIR / name)
        assert "SiteUtils" in text and "onReady" in text, (
            f"{name} must enter through `SiteUtils.onReady` (#246)"
        )
    copy_code = _read(JS_DIR / "copy-code.js")
    share = _read(JS_DIR / "share.js")
    lightbox = _read(JS_DIR / "lightbox.js")
    for text, name in ((copy_code, "copy-code.js"), (share, "share.js")):
        assert "SiteUtils" in text and "copyText" in text, (
            f"{name} must copy through `SiteUtils.copyText` (#246)"
        )
    for text, name in ((copy_code, "copy-code.js"), (lightbox, "lightbox.js")):
        assert "SiteUtils" in text and "isVietnamese" in text, (
            f"{name} must sniff the language via `SiteUtils.isVietnamese` "
            "(#246)"
        )


@pytest.mark.static
def test_the_helper_is_linked_first_with_the_cache_version_token():
    """A fixed-URL asset must carry the build token and load first (#61)."""
    html = _read(SUB_FOOTER)
    assert f"{HELPER_PATH}?v=" in html, (
        f"{SUB_FOOTER.relative_to(REPO_ROOT)} must link {HELPER_PATH} with "
        "the `?v=` build token, like every other fixed-URL asset (#61)"
    )
    assert re.search(r"site\.time", html), (
        "the version token must be derived from the build"
    )
    first = html.index(f"{HELPER_PATH}?v=")
    for name in READY_CONSUMERS:
        if name == "search.js":
            continue
        tag = f"/assets/js/{name}?v="
        assert tag in html, f"sub-footer must still link {tag}"
        assert first < html.index(tag), (
            f"the helper must load before {name} (deferred scripts run in "
            "document order, #246)"
        )
    search_html = _read(SEARCH_INCLUDE)
    assert f"{HELPER_PATH}?v=" in search_html, (
        "search pages run `search.js` before the sub-footer scripts, so "
        f"{SEARCH_INCLUDE.relative_to(REPO_ROOT)} must link the helper "
        "ahead of `search.js` (#246)"
    )
    assert search_html.index(f"{HELPER_PATH}?v=") < search_html.index(
        "/assets/js/search.js?v="
    ), "the helper must load before `search.js` on the search pages"


@pytest.mark.static
def test_total_js_bytes_do_not_increase():
    total = sum(p.stat().st_size for p in JS_DIR.glob("*.js"))
    assert total <= MAX_TOTAL_JS_BYTES, (
        f"assets/js totals {total} bytes, expected at most "
        f"{MAX_TOTAL_JS_BYTES}: dedupe must not grow the payload (#246)"
    )


# --- build guards (need Ruby; no browser) ----------------------------------


def test_the_rendered_helper_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, on pages and search."""
    home = _read(built_site / "index.html")
    match = re.search(r'<script src="(/assets/js/site-utils\.js\?v=([^"]+))"', home)
    assert match, "the home page does not link the shared helper"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )
    assert home.index(match.group(1)) < home.index("copy-code.js?v="), (
        "the rendered helper tag must precede its users"
    )
    search = _read(built_site / "search" / "index.html")
    helper_pos = search.find("/assets/js/site-utils.js?v=")
    script_pos = search.find("/assets/js/search.js?v=")
    assert helper_pos != -1 and script_pos != -1, (
        "the rendered search page must link the helper and the script"
    )
    assert helper_pos < script_pos, (
        "the rendered helper tag must precede `search.js`"
    )
