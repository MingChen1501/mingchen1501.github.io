"""Guards for #112 (reader-UX audit): posts whose primary tag has no
published siblings still get a sidebar section.

Background: the audit found the Internet post (EN + VI) renders no Related
posts — its pillar-mate stays unpublished, so `site.tags` holds it alone.
The post layout now falls back to the newest posts of the page's language
under an honest "Latest posts" / "Bài viết mới nhất" heading (the same
wording as the sidebar's newest-posts fallback), while posts with real
tag siblings keep the "Related posts" / "Bài viết cùng chủ đề" section.

Guarded here:

- (static) the layout computes the fallback from the page's language
  source (`site.posts` / nil-safe `site.vi_posts`), switches the heading
  only when falling back, and the render loop still skips the current page
  with at most five entries;
- (built HTML) the singleton-tag Internet pages (EN + VI) render the
  fallback section with same-language links that exclude the page itself,
  and a multi-sibling post keeps the true Related section.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"

EN_SINGLETON = "2022/12/25/explaining-the-internet.html"
VI_SINGLETON = "vi/2022/12/25/gioi-thieu-ve-internet.html"
EN_RELATED = "2026/10/17/real-world-agent-orchestration-with-free-opencode.html"


def _read(path):
    return path.read_text(encoding="utf-8")


def _sidebar_sections(html):
    """(heading, links) for every related-posts sidebar section."""
    sections = []
    for match in re.finditer(
        r'<h2 class="post-sidebar__heading">([^<]*)</h2>\s*'
        r'<ul class="related-posts">(.*?)</ul>',
        html,
        re.S,
    ):
        links = re.findall(r'href="([^"]+)"', match.group(2))
        sections.append((match.group(1), links))
    return sections


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_layout_falls_back_to_latest_posts_without_siblings():
    text = _read(POST_LAYOUT)
    assert "latest_source" in text
    assert "use_latest" in text
    # The English source is the published EN stream; the Vietnamese source
    # is the nil-safe collection (upstream CI builds without it).
    assert "latest_source = site.posts" in text
    assert "latest_source = rel_vi_source" in text
    # Honest headings: fallback says Latest, siblings say Related.
    assert "Latest posts" in text
    assert "Bài viết mới nhất" in text
    assert "Related posts" in text
    assert "Bài viết cùng chủ đề" in text


@pytest.mark.static
def test_layout_still_skips_current_page_and_caps_at_five():
    text = _read(POST_LAYOUT)
    assert "other.url != page.url" in text
    assert "shown < 5" in text


# --- built-HTML guards (need the real `jekyll build`, no browser) ----------


def test_singleton_posts_render_latest_posts_fallback(built_site):
    for page, heading, prefix in (
        (EN_SINGLETON, "Latest posts", "/"),
        (VI_SINGLETON, "Bài viết mới nhất", "/vi/"),
    ):
        html = _read(built_site / page)
        sections = _sidebar_sections(html)
        assert len(sections) == 1, f"{page}: want exactly one section"
        section_heading, links = sections[0]
        assert section_heading == heading, f"{page}: {section_heading!r}"
        assert 1 <= len(links) <= 5, f"{page}: {len(links)} links"
        assert all(link.startswith(prefix) for link in links), (
            f"{page}: fallback links must stay in the page's language: {links}"
        )
        assert not any(link.endswith("internet.html") for link in links), (
            f"{page}: fallback must exclude the current page"
        )


def test_sibling_posts_keep_true_related_section(built_site):
    html = _read(built_site / EN_RELATED)
    sections = _sidebar_sections(html)
    assert len(sections) == 1
    heading, links = sections[0]
    assert heading == "Related posts"
    assert links == [
        "/2026/10/14/setting-up-ai-coding-agent-orchestration.html"
    ]
