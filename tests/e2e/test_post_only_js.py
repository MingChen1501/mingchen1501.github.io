"""Guards for #253: post-only JS loads on post pages only.

Every page used to ship every first-party script: ``_includes/sub-footer.html``
loaded eight deferred scripts unconditionally, including ``share.js`` (which
wires the copy-link button rendered by ``_includes/share.html``, itself only
included from ``_layouts/post.html``) and ``reading-progress.js`` (which
drives the progress bar + back-to-top button that ship ``hidden`` in
``_layouts/post.html``). Home, tag, about, portfolio and search pages
rendered neither control yet downloaded both files.

Guarded here:

- the two tags stay in ``sub-footer.html`` with the ``?v=`` build token in
  the same relative order (share, then reading-progress, both after
  ``site-utils.js``), wrapped in a single ``page.layout == 'post'``
  conditional (static);
- the six scripts every page needs stay unconditional (static);
- built non-post pages (home EN/VI, tag index + one tag page, about,
  portfolio, search EN/VI) link neither script and go from 9 to 7
  sub-footer script requests, while built EN/VI post pages still link
  both with a non-empty epoch token (built, needs Ruby).
"""

import re
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"

SHARE_PATH = "/assets/js/share.js"
PROGRESS_PATH = "/assets/js/reading-progress.js"

# Scripts every page needs: helper first, then the site-wide enhancements.
ALWAYS_LOADED = (
    "/assets/js/site-utils.js",
    "/assets/js/lazy-load.js",
    "/assets/js/nav-toggle.js",
    "/assets/js/copy-code.js",
    "/assets/js/lang-switch.js",
    "/assets/js/theme-toggle.js",
    "/assets/js/lightbox.js",
)

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_post_only_scripts_are_gated_on_the_post_layout():
    """Both tags render only where the post markup lives (#253)."""
    html = _read(SUB_FOOTER)
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", html)
    assert gate, (
        "sub-footer must gate the post-only scripts on "
        "`{% if page.layout == 'post' %}` (#253)"
    )
    endif = html.find("endif", gate.end())
    assert endif != -1, "the post-layout conditional must be closed"
    gated = html[gate.end():endif]
    assert f"{SHARE_PATH}?v=" in gated, (
        "the share script tag must live inside the post-layout "
        "conditional (#253)"
    )
    assert f"{PROGRESS_PATH}?v=" in gated, (
        "the reading-progress script tag must live inside the "
        "post-layout conditional (#253)"
    )


@pytest.mark.static
def test_the_gated_scripts_keep_token_and_order():
    """Cache versioning and document order survive the gating (#253)."""
    html = _read(SUB_FOOTER)
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER)), (
        "the version token must still be derived from the build"
    )
    share_pos = html.index(f"{SHARE_PATH}?v=")
    progress_pos = html.index(f"{PROGRESS_PATH}?v=")
    assert share_pos < progress_pos, (
        "share.js must stay before reading-progress.js "
        "(deferred scripts run in document order)"
    )
    helper_pos = html.index("/assets/js/site-utils.js?v=")
    assert helper_pos < share_pos, (
        "the shared helper must still load before its users (#246)"
    )


@pytest.mark.static
def test_the_site_wide_scripts_stay_unconditional():
    """Gating must not swallow a script every page needs (#253)."""
    html = _read(SUB_FOOTER)
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", html)
    head = html[:gate.start()] if gate else html
    for path in ALWAYS_LOADED:
        assert f"{path}?v=" in head, (
            f"{path} must stay outside the post-layout conditional: "
            "every page needs it (#253)"
        )


# --- built-HTML guards (need the real `jekyll build`, no browser) ---------


def _non_post_pages(built_site):
    pages = [
        "index.html",
        "vi/index.html",
        "tags/index.html",
        "about/index.html",
        "portfolio/index.html",
        "search/index.html",
        "vi/tim-kiem/index.html",
    ]
    pages.extend(
        path.relative_to(built_site).as_posix()
        for path in sorted(built_site.glob("tags/*/index.html"))[:1]
    )
    return pages


def test_non_post_pages_skip_both_post_only_scripts(built_site):
    """Home, tag, about, portfolio, search: no post-only downloads (#253).

    Non-post pages drop from 9 to 7 sub-footer scripts (search pages carry
    their own ``search.js`` + helper tags on top); every page keeps the
    seven scripts it actually needs.
    """
    for page in _non_post_pages(built_site):
        assert (built_site / page).is_file(), f"{page} is missing"
        html = _read(built_site / page)
        assert SHARE_PATH not in html, (
            f"{page} downloads share.js although it renders no share "
            "row (#253)"
        )
        assert PROGRESS_PATH not in html, (
            f"{page} downloads reading-progress.js although it renders "
            "no progress controls (#253)"
        )
        for path in ALWAYS_LOADED:
            assert f"{path}?v=" in html, (
                f"{page} lost {path}, which every page needs (#253)"
            )
        scripts = re.findall(r'<script src="(/assets/js/[^"]+)" defer>', html)
        assert len(scripts) == 7, (
            f"{page} loads {len(scripts)} deferred first-party scripts, "
            f"expected 7 (got {scripts}) (#253)"
        )


def test_post_pages_still_load_both_scripts(built_site):
    """EN + VI posts keep both tags with a real epoch token (#253)."""
    for rel in (EN_POST_REL, VI_POST_REL):
        assert (built_site / rel).is_file(), f"{rel} is missing"
        html = _read(built_site / rel)
        for path in (SHARE_PATH, PROGRESS_PATH):
            match = re.search(
                rf'<script src="({re.escape(path)}\?v=([^"]+))" defer>', html
            )
            assert match, f"{rel} no longer links {path} (#253)"
            assert re.fullmatch(r"\d+", match.group(2)), (
                f"{rel}: the {path} token must be a non-empty epoch, got "
                f"{match.group(2)!r}"
            )
        assert html.index(f"{SHARE_PATH}?v=") < html.index(
            f"{PROGRESS_PATH}?v="
        ), f"{rel}: script order must be unchanged (#253)"
