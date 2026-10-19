"""Single-H1 guard for the portfolio pages (#143, follow-up of #112).

`/portfolio/` and `/vi/portfolio/` use `_layouts/page.html`, which renders the
page `title` ("Resume" / "Hồ sơ") as the single `<h1 class="post-title">`. The
Markdown body used to start with its own `# <name>` H1 nameplate, producing
two H1 elements and weakening the document outline for screen readers and
search engines. The nameplate is now an H2; the layout H1 stays untouched.

Static guards (no Ruby) pin the source contract; build guards (need Ruby, no
browser) pin the emitted pages: exactly one `<h1`, the layout title as that
H1, and the name/role/contact block still rendered.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EN_PAGE = REPO_ROOT / "portfolio.md"
VI_PAGE = REPO_ROOT / "vi" / "portfolio.md"
PAGE_LAYOUT = REPO_ROOT / "_layouts" / "page.html"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _body(path):
    match = FRONT_MATTER_RE.match(_read(path))
    assert match, f"{path} has no front matter"
    return _read(path)[match.end():]


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_portfolio_bodies_have_no_h1_nameplate():
    for page in (EN_PAGE, VI_PAGE):
        body = _body(page)
        assert not re.search(r"^# ", body, re.M), (
            f"{page.relative_to(REPO_ROOT)} must not start a line with `# `: "
            "the layout H1 stays the single H1 (#143)"
        )


@pytest.mark.static
def test_portfolio_nameplates_stay_visible_h2_headings():
    assert re.search(r"^## Tran Cong Minh\s*$", _body(EN_PAGE), re.M), (
        "EN portfolio must keep the visible name nameplate as an H2"
    )
    assert re.search(r"^## Trần Công Minh\s*$", _body(VI_PAGE), re.M), (
        "VI portfolio must keep the visible name nameplate as an H2"
    )


@pytest.mark.static
def test_portfolio_front_matter_keeps_permalink_ref_and_title():
    for page, permalink, ref, title in (
        (EN_PAGE, "/portfolio/", "portfolio", "Resume"),
        (VI_PAGE, "/vi/portfolio/", "portfolio", "Hồ sơ"),
    ):
        match = FRONT_MATTER_RE.match(_read(page))
        assert match, f"{page} has no front matter"
        block = match.group(1)
        assert re.search(rf"^permalink:\s*{re.escape(permalink)}\s*$", block, re.M)
        assert re.search(rf"^ref:\s*{re.escape(ref)}\s*$", block, re.M)
        assert re.search(rf"^title:\s*{re.escape(title)}\s*$", block, re.M)


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
        (("portfolio", "index.html"), "Tran Cong Minh", "Backend Engineer"),
        (("vi", "portfolio", "index.html"), "Trần Công Minh", "Backend Engineer"),
    ],
)
def test_portfolio_pages_render_exactly_one_h1(built_site, parts, name, role):
    html = _built_html(built_site, *parts)
    assert len(re.findall(r"<h1[\s>]", html)) == 1, (
        f"{'/'.join(parts)} must render exactly one H1 (#143)"
    )
    assert re.search(r"<h1[^>]*>.*?</h1>", html, re.S), "portfolio page has no H1"
    # The nameplate survives as a visible H2 followed by the role line.
    assert re.search(rf"<h2[^>]*>{re.escape(name)}</h2>", html), (
        f"{'/'.join(parts)} lost the visible {name!r} nameplate"
    )
    assert role in html, f"{'/'.join(parts)} lost the {role!r} role line"
    # The contact block survives untouched.
    for contact in ("mingchen1501@gmail.com", "linkedin.com/in/mingchen1501"):
        assert contact in html, f"{'/'.join(parts)} lost contact {contact!r}"
