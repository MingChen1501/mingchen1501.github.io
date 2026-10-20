"""Footer description and author name language guard (#105, #123).

`site.description` and `site.author.name` in `_config.yml` are Vietnamese,
so `_includes/footer.html` used to render them on every page — including the
English ones. The footer is now language-aware: English pages (`lang: en`,
the default) render `site.description_en` and `site.author.name_en`,
Vietnamese pages (`lang: vi`) keep `site.description` and `site.author.name`.
The footer lives in `_layouts/base.html`, so the single conditional covers
every layout (home, page, post, tag).

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) assert the rendered footer on EN and VI homes, pages and posts,
with no cross-language leak.
"""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _config_value(key):
    """Read a folded (`>`) scalar string from `_config.yml`."""
    lines = (REPO_ROOT / "_config.yml").read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"^{key}:[ \t]*(>.*)?$", line):
            chunks = []
            for follow in lines[i + 1:]:
                if re.match(r"^[ \t]+\S", follow):
                    chunks.append(follow.strip())
                else:
                    break
            return " ".join(chunks)
    raise AssertionError(f"_config.yml has no `{key}` key")


def _author_value(key):
    """Read a nested `author.<key>` scalar string from `_config.yml`."""
    lines = (REPO_ROOT / "_config.yml").read_text(encoding="utf-8").splitlines()
    in_author = False
    for line in lines:
        if re.match(r"^author:[ \t]*$", line):
            in_author = True
            continue
        if in_author:
            m = re.match(rf"^[ \t]+{key}:[ \t]*(.+?)[ \t]*$", line)
            if m:
                return m.group(1)
            if re.match(r"^\S", line):
                break
    raise AssertionError(f"_config.yml has no `author.{key}` key")


def _footer_description(page_html, url):
    """The unescaped footer tagline paragraph of a built page."""
    footer = re.search(
        r'<footer class="site-footer.*?</footer>', page_html, re.S
    )
    assert footer, f"{url} renders no site footer"
    paragraphs = re.findall(
        r'<div class="footer-col">\s*<p>(.*?)</p>', footer.group(0), re.S
    )
    assert paragraphs, f"{url} footer has no description paragraph"
    return html_lib.unescape(paragraphs[0].strip())


def _footer_author_name(page_html, url):
    """The unescaped footer author name of a built page."""
    footer = re.search(
        r'<footer class="site-footer.*?</footer>', page_html, re.S
    )
    assert footer, f"{url} renders no site footer"
    names = re.findall(
        r'<li class="p-name">(.*?)</li>', footer.group(0), re.S
    )
    assert names, f"{url} footer has no author name"
    return html_lib.unescape(names[0].strip())


def _first_post_rel(home_html, url):
    """The first listed post of a built home page, as a build-relative path."""
    post_href = re.search(r'class="post-link" href="([^"]+)"', home_html)
    assert post_href, f"{url} lists no posts"
    return post_href.group(1).lstrip("/")


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_footer_template_branches_on_page_language():
    footer = (REPO_ROOT / "_includes" / "footer.html").read_text(
        encoding="utf-8"
    )
    assert "site.description_en" in footer, (
        "footer.html must render `site.description_en` on English pages (#105)"
    )
    assert "site.description" in footer
    assert "page.lang" in footer, (
        "footer.html must branch on the page language, not render one "
        "fixed description"
    )


@pytest.mark.static
def test_config_declares_both_footer_descriptions():
    en = _config_value("description_en")
    vi = _config_value("description")
    assert en, "_config.yml needs a `description_en` key (#105)"
    assert vi, "_config.yml must keep the Vietnamese `description`"
    assert en != vi, "the two footer descriptions must differ by language"


@pytest.mark.static
def test_footer_template_branches_author_name_on_page_language():
    footer = (REPO_ROOT / "_includes" / "footer.html").read_text(
        encoding="utf-8"
    )
    assert "site.author.name_en" in footer, (
        "footer.html must render `site.author.name_en` on English pages "
        "(#123)"
    )
    assert "site.author.name" in footer
    assert "page.lang" in footer, (
        "footer.html must branch on the page language, not render one "
        "fixed author name"
    )


@pytest.mark.static
def test_config_declares_both_author_names():
    en = _author_value("name_en")
    vi = _author_value("name")
    assert en, "_config.yml needs an `author.name_en` key (#123)"
    assert vi, "_config.yml must keep the Vietnamese `author.name`"
    assert en != vi, "the two author names must differ by language"


# --- build guards (need Ruby; no browser) -----------------------------------


def test_footer_description_matches_the_page_language(built_site):
    en = _config_value("description_en")
    vi = _config_value("description")

    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    en_post_rel = _first_post_rel(en_home, "/")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    vi_post_rel = _first_post_rel(vi_home, "/vi/")

    en_pages = [
        "index.html",
        "about/index.html",
        "portfolio/index.html",
        "tags/index.html",
        en_post_rel,
    ]
    for rel in en_pages:
        page = built_site / rel
        assert page.is_file(), f"English page /{rel} is missing from the build"
        html = page.read_text(encoding="utf-8")
        assert _footer_description(html, f"/{rel}") == en, (
            f"English page /{rel} footer must render the English description"
        )
        assert vi not in html.split('<footer class="site-footer')[1], (
            f"English page /{rel} footer leaks the Vietnamese description"
        )

    vi_pages = [
        "vi/index.html",
        "vi/about/index.html",
        "vi/portfolio/index.html",
        "vi/tags/index.html",
        vi_post_rel,
    ]
    for rel in vi_pages:
        page = built_site / rel
        assert page.is_file(), (
            f"Vietnamese page /{rel} is missing from the build"
        )
        html = page.read_text(encoding="utf-8")
        assert _footer_description(html, f"/{rel}") == vi, (
            f"Vietnamese page /{rel} footer must render the Vietnamese "
            "description"
        )
        assert en not in html.split('<footer class="site-footer')[1], (
            f"Vietnamese page /{rel} footer leaks the English description"
        )


def test_footer_author_name_matches_the_page_language(built_site):
    en = _author_value("name_en")
    vi = _author_value("name")

    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    en_post_rel = _first_post_rel(en_home, "/")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    vi_post_rel = _first_post_rel(vi_home, "/vi/")

    en_pages = [
        "index.html",
        en_post_rel,
    ]
    for rel in en_pages:
        page = built_site / rel
        assert page.is_file(), f"English page /{rel} is missing from the build"
        html = page.read_text(encoding="utf-8")
        assert _footer_author_name(html, f"/{rel}") == en, (
            f"English page /{rel} footer must render the English author name"
        )
        assert vi not in html.split('<footer class="site-footer')[1], (
            f"English page /{rel} footer leaks the Vietnamese author name"
        )

    vi_pages = [
        "vi/index.html",
        vi_post_rel,
    ]
    for rel in vi_pages:
        page = built_site / rel
        assert page.is_file(), (
            f"Vietnamese page /{rel} is missing from the build"
        )
        html = page.read_text(encoding="utf-8")
        assert _footer_author_name(html, f"/{rel}") == vi, (
            f"Vietnamese page /{rel} footer must render the Vietnamese "
            "author name"
        )
        assert en not in html.split('<footer class="site-footer')[1], (
            f"Vietnamese page /{rel} footer leaks the English author name"
        )
