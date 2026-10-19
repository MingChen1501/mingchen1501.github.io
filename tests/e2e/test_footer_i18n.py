"""Footer description language guard (#105).

`site.description` in `_config.yml` is Vietnamese, so `_includes/footer.html`
used to render the Vietnamese tagline on every page — including the English
ones. The footer is now language-aware: English pages (`lang: en`, the
default) render `site.description_en`, Vietnamese pages (`lang: vi`) keep
`site.description`. The footer lives in `_layouts/base.html`, so the single
conditional covers every layout (home, page, post, tag).

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


# --- build guards (need Ruby; no browser) -----------------------------------


def test_footer_description_matches_the_page_language(built_site):
    en = _config_value("description_en")
    vi = _config_value("description")

    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    en_post_href = re.search(r'class="post-link" href="([^"]+)"', en_home)
    assert en_post_href, "the English home lists no posts"
    en_post_rel = en_post_href.group(1).lstrip("/")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    vi_post_href = re.search(r'class="post-link" href="([^"]+)"', vi_home)
    assert vi_post_href, "the Vietnamese home lists no posts"
    vi_post_rel = vi_post_href.group(1).lstrip("/")

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
