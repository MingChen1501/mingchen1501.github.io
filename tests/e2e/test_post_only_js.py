"""Guards for #253 + #318 + #345 + #417: post-only JS loads on post pages only.

Every page used to ship every first-party script: ``_includes/sub-footer.html``
loaded nine deferred scripts unconditionally, including ``share.js`` (which
wires the copy-link button rendered by ``_includes/share.html``, itself only
included from ``_layouts/post.html``), ``reading-progress.js`` (which
drives the progress bar + back-to-top button that ship ``hidden`` in
``_layouts/post.html``), ``copy-code.js`` (which enhances ``pre > code``,
rendered only on posts), ``lightbox.js`` (which queries
``.post-content img``, absent from non-post ``.post-content`` blocks) and
the ToC modules (``toc-spy.js`` core, ``toc-sheet.js`` phone sheet,
``toc-fab-drag.js`` drag, which mark the ``.post-toc__nav`` row being read,
rendered only from ``_layouts/post.html``). Home, tag, about and resume pages
rendered none of those controls yet downloaded all seven files (#253 gated
share + reading-progress; #318 gated copy-code + lightbox the same way;
#345 gates toc-spy the same way; #417 splits it into core + sheet + drag
without leaving the gate).

Guarded here:

- the seven tags stay in ``sub-footer.html`` with the ``?v=`` build token in
  the same relative order (copy-code, lightbox, share, reading-progress,
  then the ToC core, sheet and drag, all after ``site-utils.js``), wrapped
  in a single ``page.layout == 'post'`` conditional (static);
- the five scripts every page needs stay unconditional (static);
- built non-post pages (home EN/VI, tag index + one tag page, about,
  resume) link none of the seven scripts and go from 10 to 5
  sub-footer script requests, while built EN/VI post pages still link
  all seven with a non-empty epoch token (built, needs Ruby).
"""

import re
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUB_FOOTER = REPO_ROOT / "_includes" / "sub-footer.html"

# Scripts every page needs: helper first, then the site-wide enhancements.
ALWAYS_LOADED = (
    "/assets/js/site-utils.js",
    "/assets/js/lazy-load.js",
    "/assets/js/nav-toggle.js",
    "/assets/js/lang-switch.js",
    "/assets/js/theme-toggle.js",
)

# Scripts that only post pages need, in document order (#253, #318, #345,
# #417 splits the ToC scroll-spy into core + sheet + drag).
POST_ONLY = (
    "/assets/js/copy-code.js",
    "/assets/js/lightbox.js",
    "/assets/js/share.js",
    "/assets/js/reading-progress.js",
    "/assets/js/toc-spy.js",
    "/assets/js/toc-sheet.js",
    "/assets/js/toc-fab-drag.js",
)

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _read(path):
    return Path(path).read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_post_only_scripts_are_gated_on_the_post_layout():
    """All seven tags render only where the post markup lives (#253, #318, #345, #417)."""
    html = _read(SUB_FOOTER)
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", html)
    assert gate, (
        "sub-footer must gate the post-only scripts on "
        "`{% if page.layout == 'post' %}` (#253)"
    )
    endif = html.find("endif", gate.end())
    assert endif != -1, "the post-layout conditional must be closed"
    gated = html[gate.end():endif]
    for path in POST_ONLY:
        assert f"{path}?v=" in gated, (
            f"the {path.rsplit('/', 1)[-1]} script tag must live inside the "
            "post-layout conditional (#253, #318, #345)"
        )


@pytest.mark.static
def test_the_gated_scripts_keep_token_and_order():
    """Cache versioning and document order survive the gating (#253, #318, #345)."""
    html = _read(SUB_FOOTER)
    assert re.search(r"site\.time", conftest.template_with_includes(SUB_FOOTER)), (
        "the version token must still be derived from the build"
    )
    positions = [html.index(f"{path}?v=") for path in POST_ONLY]
    assert positions == sorted(positions), (
        "post-only order must stay copy-code, lightbox, share, "
        "reading-progress, toc-spy, toc-sheet, toc-fab-drag "
        "(deferred scripts run in document order)"
    )
    helper_pos = html.index("/assets/js/site-utils.js?v=")
    assert helper_pos < positions[0], (
        "the shared helper must still load before its users (#246)"
    )


@pytest.mark.static
def test_the_site_wide_scripts_stay_unconditional():
    """Gating must not swallow a script every page needs (#253, #318, #345)."""
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
        "resume/index.html",
    ]
    pages.extend(
        path.relative_to(built_site).as_posix()
        for path in sorted(built_site.glob("tags/*/index.html"))[:1]
    )
    return pages


def test_non_post_pages_skip_all_post_only_scripts(built_site):
    """Home, tag, about, resume: no post-only downloads (#318).

    Non-post pages drop from 10 to 5 sub-footer scripts; every page keeps the
    five scripts it actually needs.
    """
    for page in _non_post_pages(built_site):
        assert (built_site / page).is_file(), f"{page} is missing"
        html = _read(built_site / page)
        for path in POST_ONLY:
            assert path not in html, (
                f"{page} downloads {path.rsplit('/', 1)[-1]} although it "
                "renders no post controls (#253, #318, #345)"
            )
        for path in ALWAYS_LOADED:
            assert f"{path}?v=" in html, (
                f"{page} lost {path}, which every page needs (#253)"
            )
        scripts = re.findall(r'<script src="(/assets/js/[^"]+)" defer>', html)
        assert len(scripts) == 5, (
            f"{page} loads {len(scripts)} deferred first-party scripts, "
            f"expected 5 (got {scripts}) (#318)"
        )


def test_post_pages_still_load_all_post_only_scripts(built_site):
    """EN + VI posts keep all seven tags with a real epoch token (#318, #345, #417)."""
    for rel in (EN_POST_REL, VI_POST_REL):
        assert (built_site / rel).is_file(), f"{rel} is missing"
        html = _read(built_site / rel)
        for path in POST_ONLY:
            match = re.search(
                rf'<script src="({re.escape(path)}\?v=([^"]+))" defer>', html
            )
            assert match, f"{rel} no longer links {path} (#253, #318, #345)"
            assert re.fullmatch(r"\d+", match.group(2)), (
                f"{rel}: the {path} token must be a non-empty epoch, got "
                f"{match.group(2)!r}"
            )
        positions = [html.index(f"{path}?v=") for path in POST_ONLY]
        assert positions == sorted(positions), (
            f"{rel}: script order must be unchanged (#253, #318, #345)"
        )
