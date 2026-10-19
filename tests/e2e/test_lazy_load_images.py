"""Guard for #86: content images are lazy-loaded, the first one is not.

The site has no plugin (GitHub Pages builds with ``--safe``), so the
``loading`` attribute cannot be injected into the kramdown output at build
time. ``assets/js/lazy-load.js`` does it at runtime instead, with one rule:

    inside every content block (``.post-content`` / ``.page-content`` /
    ``article.post``) the FIRST image keeps ``loading="eager"`` - it sits at
    the top of the article and can be the LCP element - and every following
    image becomes ``loading="lazy"``.

An image that already declares a loading mode (the sidebar thumbnails do, see
``_includes/site-sidebar.html``) is never touched, so the script can not undo
a deliberate server-side decision.

Guarded here:

- the script exists, stays tiny and has no dependency (static);
- the template links it through the ``?v=`` build token, like every other
  fixed-URL asset (#61) (static);
- the head preconnects the only third-party origin the templates load, the
  Font Awesome stylesheet on ``cdn.jsdelivr.net`` (static);
- on a real post page the first content image is eager and the others are
  lazy (browser);
- the sidebar thumbnails keep the ``loading="lazy"`` they were rendered with
  (browser).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "lazy-load.js"
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
FOOTER_INCLUDE = REPO_ROOT / "_includes" / "footer.html"

SCRIPT_PATH = "/assets/js/lazy-load.js"
FONT_ORIGIN = "https://cdn.jsdelivr.net"

# The script is a few hundred bytes of plain DOM code; keep it that way.
MAX_SCRIPT_BYTES = 2048
MAX_SCRIPT_CODE_LINES = 25


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_lazy_load_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the lazy-load script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the lazy-load script has {len(code)} code lines, expected at most "
        f"{MAX_SCRIPT_CODE_LINES}"
    )
    # No dependency, no build step: the file runs as it is served.
    assert "import " not in text and "require(" not in text, (
        "the lazy-load script must not depend on anything"
    )


@pytest.mark.static
def test_the_script_is_linked_with_the_cache_version_token():
    """A fixed-URL asset must carry the build token (#61)."""
    html = _read(SUB_FOOTER)
    assert f'{SCRIPT_PATH}?v=' in html, (
        f"{SUB_FOOTER.relative_to(REPO_ROOT)} must link {SCRIPT_PATH} with the "
        "`?v=` build token, like every other fixed-URL asset (#61)"
    )
    token = re.search(rf"{re.escape(SCRIPT_PATH)}\?v=\{{\{{\s*([^}}]+?)\s*\}}\}}", html)
    assert token, "the version token of the script link is missing"
    expression = token.group(1)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
        # `{%- assign <token> = <build expression> -%}` in the same include.
        assign = re.search(
            rf"assign\s+{re.escape(expression)}\s*=\s*(.+?)\s*-?%\}}", html
        )
        assert assign, (
            f"the version {expression!r} is never assigned in "
            f"{SUB_FOOTER.relative_to(REPO_ROOT)}"
        )
        expression = assign.group(1).strip()
    assert re.search(r"\bsite\.time\b|\bsite\.github\.build_revision\b", expression), (
        "the version token must be derived from the build, got "
        f"{{{{ {expression} }}}}"
    )


@pytest.mark.static
def test_head_preconnects_the_only_third_party_origin():
    """The Font Awesome stylesheet is the one external stylesheet."""
    assert FONT_ORIGIN in _read(FOOTER_INCLUDE), (
        "the Font Awesome stylesheet is expected to come from "
        f"{FONT_ORIGIN}; the preconnect guard must follow it"
    )
    head = _read(HEAD_INCLUDE)
    assert re.search(
        rf'<link[^>]*rel="preconnect"[^>]*href="{re.escape(FONT_ORIGIN)}"[^>]*>',
        head,
    ), f"the head must preconnect {FONT_ORIGIN}"
    assert re.search(
        rf'<link[^>]*rel="dns-prefetch"[^>]*href="{re.escape(FONT_ORIGIN)}"[^>]*>',
        head,
    ), f"the head must dns-prefetch {FONT_ORIGIN}"


def test_the_rendered_script_url_carries_a_non_empty_token(built_site):
    """The token must render as a real epoch, not as an empty query."""
    text = _read(built_site / "index.html")
    match = re.search(r'<script src="(/assets/js/lazy-load\.js\?v=([^"]+))"', text)
    assert match, "the home page does not link the lazy-load script"
    assert re.fullmatch(r"\d+", match.group(2)), (
        "the version token must be a non-empty epoch, got "
        f"{match.group(2)!r}"
    )


# --- browser guard (needs the real build) -----------------------------------


@pytest.fixture()
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    browser_page = context.new_page()
    # Only the site's own files are fetched: the third-party stylesheet is
    # aborted so the run stays offline-safe.
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


_LOADING_JS = """
() => Array.from(document.querySelectorAll('.post-content img')).map(
    (img) => img.getAttribute('loading')
)
"""

_THUMBNAIL_JS = """
() => Array.from(document.querySelectorAll('aside.site-sidebar img')).map(
    (img) => img.getAttribute('loading')
)
"""


def _post_with_images(built_site):
    """A built post page whose content holds several images."""
    for path in sorted(built_site.rglob("*.html")):
        text = _read(path)
        match = re.search(
            r'<div class="post-content[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S
        )
        if not match:
            continue
        if len(re.findall(r"<img\b", match.group(1))) >= 3:
            return path
    pytest.fail("no built post page with several content images was found")


def test_the_first_content_image_stays_eager_and_the_others_become_lazy(
    built_site, built_site_url, page
):
    post = _post_with_images(built_site)
    relative = "/" + post.relative_to(built_site).as_posix()

    page.goto(built_site_url.rstrip("/") + relative, wait_until="load")
    # The script is deferred: it has run once the document is parsed.
    page.wait_for_function(
        "() => document.querySelectorAll('.post-content img').length > 0",
        timeout=10_000,
    )
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('.post-content img'))"
        ".every((img) => img.hasAttribute('loading'))",
        timeout=10_000,
    )

    loading = page.evaluate(_LOADING_JS)
    assert len(loading) >= 3, f"{relative} has too few content images to judge"
    assert loading[0] == "eager", (
        "the first image of the article is the one that can be the LCP element; "
        f"it must stay eager, got {loading[0]!r}"
    )
    assert all(value == "lazy" for value in loading[1:]), (
        f"every image after the first one must be lazy, got {loading[1:]}"
    )


def test_the_sidebar_thumbnails_keep_their_own_loading_mode(
    built_site, built_site_url, page
):
    """The script must not override a server-side decision."""
    page.goto(built_site_url.rstrip("/") + "/", wait_until="load")
    page.wait_for_selector("aside.site-sidebar img", state="attached", timeout=10_000)
    page.wait_for_timeout(200)

    thumbnails = page.evaluate(_THUMBNAIL_JS)
    assert thumbnails, "the home page renders no sidebar thumbnail"
    assert all(value == "lazy" for value in thumbnails), (
        "the sidebar thumbnails are rendered with loading=\"lazy\" and must "
        f"keep it, got {thumbnails}"
    )
