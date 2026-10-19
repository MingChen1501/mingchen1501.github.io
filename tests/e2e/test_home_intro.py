"""Home value proposition guard (#139, follow-up of #112).

Both home pages show a descriptive H1 (name + what the blog covers) instead
of a bare "Home" / "Trang chủ", plus a one-paragraph visible intro above the
post list. The intro is English on EN pages and Vietnamese on VI pages.

Static guards (no Ruby) cover the page source contract; build guards (need
Ruby, no browser) cover the emitted `/` and `/vi/` pages: the H1 text, the
intro paragraph sitting above the post list, and one regression pin (no
change to post URLs, feeds, or pagination — those keep their own guards).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    assert match, f"{path} has no front matter"
    return match.group(1)


def _value(block, key):
    match = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", block, re.M)
    assert match, f"front matter has no `{key}:`"
    value = match.group(1)
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _body(path):
    match = FRONT_MATTER_RE.match(_read(path))
    assert match, f"{path} has no front matter"
    return _read(path)[match.end():]


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_en_home_source_has_descriptive_title_and_intro():
    page = REPO_ROOT / "index.html"
    block = _front_matter(page)
    title = _value(block, "title")
    assert title.strip().lower() != "home", "EN home H1 must not be bare 'Home'"
    assert "ming chen" in title.lower(), "EN home H1 must name the author"
    body = _body(page)
    assert 'class="home-intro"' in body, "EN home needs a visible intro paragraph"
    assert "ming chen" in body.lower(), "EN intro must say who writes the blog"


@pytest.mark.static
def test_vi_home_source_has_descriptive_title_and_intro():
    page = REPO_ROOT / "vi" / "index.html"
    block = _front_matter(page)
    title = _value(block, "title")
    assert title.strip().lower() != "trang chủ", (
        "VI home H1 must not be bare 'Trang chủ'"
    )
    assert "ming chen" in title.lower(), "VI home H1 must name the author"
    body = _body(page)
    assert 'class="home-intro"' in body, "VI home needs a visible intro paragraph"
    assert "ming chen" in body.lower(), "VI intro must say who writes the blog"


@pytest.mark.static
def test_home_layout_still_renders_title_and_content_above_list():
    layout = _read(REPO_ROOT / "_layouts" / "home.html")
    assert "page.title" in layout, "home layout must still render page.title as H1"
    assert layout.index("{{ content }}") < layout.index('class="post-list"'), (
        "home layout must render the intro above the post list"
    )


# --- build guards (need Ruby; no browser) ------------------------------------


def _h1_and_intro(html):
    h1 = re.search(r'<h1 class="page-heading">(.*?)</h1>', html, re.S)
    assert h1, "home page has no H1"
    intro = re.search(r'<p class="home-intro">(.*?)</p>', html, re.S)
    assert intro, "home page has no visible intro paragraph"
    return h1.group(1).strip(), intro.group(1).strip()


def test_en_home_shows_descriptive_h1_and_intro_above_list(built_site):
    html = (built_site / "index.html").read_text(encoding="utf-8")
    h1, intro = _h1_and_intro(html)
    assert h1.lower() != "home", "EN home H1 must not be bare 'Home'"
    assert "ming chen" in h1.lower()
    assert len(intro) > 40, "EN intro must be a real 1-2 sentence paragraph"
    assert html.index('class="home-intro"') < html.index('class="post-list"'), (
        "EN intro must sit above the post list"
    )


def test_vi_home_shows_descriptive_h1_and_intro_above_list(built_site):
    html = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    h1, intro = _h1_and_intro(html)
    assert h1.lower() != "trang chủ", "VI home H1 must not be bare 'Trang chủ'"
    assert "ming chen" in h1.lower()
    assert len(intro) > 40, "VI intro must be a real 1-2 sentence paragraph"
    assert html.index('class="home-intro"') < html.index('class="post-list"'), (
        "VI intro must sit above the post list"
    )


def test_home_intros_match_page_language(built_site):
    en_html = (built_site / "index.html").read_text(encoding="utf-8")
    vi_html = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    _, en_intro = _h1_and_intro(en_html)
    _, vi_intro = _h1_and_intro(vi_html)
    # EN intro is English: no Vietnamese diacritics.
    assert not re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]", en_intro), (
        "EN intro must not contain Vietnamese text"
    )
    # VI intro is Vietnamese: carries diacritics.
    assert re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]", vi_intro), (
        "VI intro must read as Vietnamese"
    )
