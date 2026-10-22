"""Single-H1 guard for the resume pages (#143, follow-up of #112).

`/resume/` and `/vi/resume/` use `_layouts/page.html`, which renders the
page `title` ("Resume" / "Hồ sơ") as the single `<h1 class="post-title">`. The
Markdown body used to start with its own `# <name>` H1 nameplate, producing
two H1 elements and weakening the document outline for screen readers and
search engines. The nameplate is now an H2; the layout H1 stays untouched.

#387 renamed the pages from `portfolio` to `resume` (`/resume/`,
`/vi/resume/`, `ref: resume`) and split each into a short Resume plus a
`#cv` section with jump links both ways: the old `/portfolio/` URLs survive
as `redirect_from` stubs, and the CV carries `OWNER FACT NEEDED` markers
instead of invented history.

Static guards (no Ruby) pin the source contract; build guards (need Ruby, no
browser) pin the emitted pages: exactly one `<h1`, the layout title as that
H1, and the name/role/contact block still rendered.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EN_PAGE = REPO_ROOT / "resume.md"
VI_PAGE = REPO_ROOT / "vi" / "resume.md"
PAGE_LAYOUT = REPO_ROOT / "_layouts" / "page.html"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _body(path):
    match = FRONT_MATTER_RE.match(_read(path))
    assert match, f"{path} has no front matter"
    return _read(path)[match.end():]


def _front_matter_block(path):
    match = FRONT_MATTER_RE.match(_read(path))
    assert match, f"{path} has no front matter"
    return match.group(1)


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_resume_bodies_have_no_h1_nameplate():
    for page in (EN_PAGE, VI_PAGE):
        body = _body(page)
        assert not re.search(r"^# ", body, re.M), (
            f"{page.relative_to(REPO_ROOT)} must not start a line with `# `: "
            "the layout H1 stays the single H1 (#143)"
        )


@pytest.mark.static
def test_resume_nameplates_stay_visible_h2_headings():
    assert re.search(r"^## Tran Cong Minh\s*$", _body(EN_PAGE), re.M), (
        "EN resume must keep the visible name nameplate as an H2"
    )
    assert re.search(r"^## Trần Công Minh\s*$", _body(VI_PAGE), re.M), (
        "VI resume must keep the visible name nameplate as an H2"
    )


@pytest.mark.static
def test_resume_front_matter_keeps_permalink_ref_and_title():
    for page, permalink, ref, title in (
        (EN_PAGE, "/resume/", "resume", "Resume"),
        (VI_PAGE, "/vi/resume/", "resume", "Hồ sơ"),
    ):
        block = _front_matter_block(page)
        assert re.search(rf"^permalink:\s*{re.escape(permalink)}\s*$", block, re.M)
        assert re.search(rf"^ref:\s*{re.escape(ref)}\s*$", block, re.M)
        assert re.search(rf"^title:\s*{re.escape(title)}\s*$", block, re.M)


@pytest.mark.static
def test_resume_front_matter_keeps_old_portfolio_redirects():
    """#387: the old `/portfolio/` URLs must survive via `redirect_from`."""
    for page, old_url in (
        (EN_PAGE, "/portfolio/"),
        (VI_PAGE, "/vi/portfolio/"),
    ):
        block = _front_matter_block(page)
        assert re.search(r"^redirect_from:\s*$", block, re.M), (
            f"{page.relative_to(REPO_ROOT)} must declare `redirect_from:`"
        )
        assert re.search(rf"^[ \t]*-[ \t]*{re.escape(old_url)}\s*$", block, re.M), (
            f"{page.relative_to(REPO_ROOT)} must redirect {old_url} "
            "so old links do not 404 (#387)"
        )


@pytest.mark.static
def test_resume_bodies_have_cv_section_with_jump_links():
    """#387: Resume first, then a `#cv` part with jump links both ways."""
    en_body = _body(EN_PAGE)
    assert re.search(r"^## Full CV \{#cv\}\s*$", en_body, re.M), (
        "EN resume must delimit the CV part with `## Full CV {#cv}`"
    )
    assert "[Full CV" in en_body and "](#cv)" in en_body, (
        "EN resume must link down to the CV (`Full CV ↓`)"
    )
    assert "[Back to Resume" in en_body and "](#resume-top)" in en_body, (
        "EN resume must link back up (`Back to Resume ↑`)"
    )
    vi_body = _body(VI_PAGE)
    assert re.search(r"^## CV đầy đủ \{#cv\}\s*$", vi_body, re.M), (
        "VI resume must delimit the CV part with `## CV đầy đủ {#cv}`"
    )
    assert "[CV đầy đủ" in vi_body and "](#cv)" in vi_body, (
        "VI resume must link down to the CV (`CV đầy đủ ↓`)"
    )
    assert "[Về đầu Hồ sơ" in vi_body and "](#resume-top)" in vi_body, (
        "VI resume must link back up (`Về đầu Hồ sơ ↑`)"
    )


@pytest.mark.static
def test_resume_links_never_sit_inside_prose():
    """Axe `link-in-text-block` (#387): the house link style is color-only
    (underline on hover/focus), so a link sharing a paragraph with other
    text fails the browser smoke — every Markdown link outside a list item
    must own its paragraph, the style posts already use."""
    for page in (EN_PAGE, VI_PAGE):
        for lineno, line in enumerate(_body(page).splitlines(), 1):
            if "](" not in line or re.match(r"\s*[-*]\s", line):
                continue
            assert re.fullmatch(r"\[[^\]]+\]\([^)]+\)\s*", line.strip()), (
                f"{page.relative_to(REPO_ROOT)}:{lineno} puts a link inside "
                "prose — give it its own paragraph (#387)"
            )


@pytest.mark.static
def test_resume_cv_sections_carry_owner_fact_markers():
    """#387: missing CV history is marked, never invented."""
    for page in (EN_PAGE, VI_PAGE):
        markers = re.findall(r"OWNER FACT NEEDED:.+", _body(page))
        assert len(markers) >= 5, (
            f"{page.relative_to(REPO_ROOT)} must mark every missing CV item "
            f"with `OWNER FACT NEEDED: <what>` — found {len(markers)}"
        )


@pytest.mark.static
def test_resume_bodies_have_no_portfolio_copy():
    """#387: no `portfolio` left in reader-facing copy (redirect stubs and
    this guard's own front-matter redirect excepted)."""
    for page in (EN_PAGE, VI_PAGE):
        assert "portfolio" not in _body(page).lower(), (
            f"{page.relative_to(REPO_ROOT)} body still mentions portfolio (#387)"
        )


@pytest.mark.static
def test_page_layout_h1_is_untouched():
    html = _read(PAGE_LAYOUT)
    assert html.count("<h1") == 1, "page layout must render exactly one H1"
    assert '<h1 class="post-title">{{ page.title | escape }}</h1>' in html


# --- build guards (need Ruby; no browser) ------------------------------------


def _built_html(built_site, *parts):
    return (built_site.joinpath(*parts)).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "parts,name,role",
    [
        (("resume", "index.html"), "Tran Cong Minh", "Backend Engineer"),
        (("vi", "resume", "index.html"), "Trần Công Minh", "Backend Engineer"),
    ],
)
def test_resume_pages_render_exactly_one_h1(built_site, parts, name, role):
    html = _built_html(built_site, *parts)
    assert len(re.findall(r"<h1[\s>]", html)) == 1, (
        f"{'/'.join(parts)} must render exactly one H1 (#143)"
    )
    assert re.search(r"<h1[^>]*>.*?</h1>", html, re.S), "resume page has no H1"
    # The nameplate survives as a visible H2 followed by the role line.
    assert re.search(rf"<h2[^>]*>{re.escape(name)}</h2>", html), (
        f"{'/'.join(parts)} lost the visible {name!r} nameplate"
    )
    assert role in html, f"{'/'.join(parts)} lost the {role!r} role line"
    # The contact block survives untouched.
    for contact in ("mingchen1501@gmail.com", "linkedin.com/in/mingchen1501"):
        assert contact in html, f"{'/'.join(parts)} lost contact {contact!r}"


@pytest.mark.parametrize(
    "parts",
    [
        ("resume", "index.html"),
        ("vi", "resume", "index.html"),
    ],
)
def test_resume_pages_render_cv_anchor_and_jump_links(built_site, parts):
    """#387: the `#cv` anchor and both jump links survive the build."""
    html = _built_html(built_site, *parts)
    assert re.search(r'<h2[^>]*id="cv"', html), (
        f"{'/'.join(parts)} lost the `#cv` anchor (#387)"
    )
    assert 'href="#cv"' in html, (
        f"{'/'.join(parts)} lost the down jump link to `#cv` (#387)"
    )
    assert 'href="#resume-top"' in html, (
        f"{'/'.join(parts)} lost the back jump link to `#resume-top` (#387)"
    )


@pytest.mark.parametrize(
    "old,new",
    [
        (("portfolio", "index.html"), "/resume/"),
        (("vi", "portfolio", "index.html"), "/vi/resume/"),
    ],
)
def test_old_portfolio_urls_emit_redirects_to_resume(built_site, old, new):
    """#387: `/portfolio/` and `/vi/portfolio/` redirect, never 404."""
    stub = built_site.joinpath(*old)
    assert stub.is_file(), f"/{'/'.join(old)} is missing from the build (404)"
    html = stub.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in html, (
        f"/{'/'.join(old)} must emit a redirect stub, not a page"
    )
    assert new in html, f"/{'/'.join(old)} must redirect to {new}"
