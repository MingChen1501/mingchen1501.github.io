"""Guards for #112 (reader-UX audit) as constrained by #328, plus the #343
multi-tag union: posts whose tags have no published siblings still get a
sidebar section, but an older evergreen page must never suggest newer
unrelated posts.

Background: the audit found the Internet post (EN + VI) renders no Related
posts — its pillar-mate stays unpublished, so `site.tags` holds it alone.
The post layout falls back to the newest posts of the page's language that
are not newer than the current page (#328: `other.date <= page.date`) under
an honest "Latest posts" / "Bài viết mới nhất" heading (the same wording as
the sidebar's newest-posts fallback), while posts with real tag siblings
keep the "Related posts" / "Bài viết cùng chủ đề" section. When nothing
that old exists, the section stays suppressed.

Guarded here:

- (static) the layout computes the fallback from the page's language
  source (`site.posts` / nil-safe `site.vi_posts`), filters it to posts
  not newer than the current page, switches the heading only when falling
  back, and the render loop still skips the current page with at most five
  entries;
- (built HTML) the singleton-tag Internet pages (EN + VI) render either a
  suppressed section or a fallback section with same-language links that
  exclude the page itself and every post newer than the page, and a
  multi-sibling post keeps the true Related section.
"""

import re
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

EN_SINGLETON = "2022/12/25/explaining-the-internet.html"
VI_SINGLETON = "vi/2022/12/25/gioi-thieu-ve-internet.html"
EN_SINGLETON_DATE = datetime(2022, 12, 25)
VI_SINGLETON_DATE = datetime(2022, 12, 25)
EN_RELATED = "2026/10/17/real-world-agent-orchestration-with-free-opencode.html"


def _read(path):
    return path.read_text(encoding="utf-8")


def _en_post_dates():
    """Published EN post URL -> datetime, from filename day plus any
    front-matter `date:` time override (#398: same-day posts declare
    `HH:MM`, which outranks the filename midnight)."""
    posts = {}
    for path in (REPO_ROOT / "_posts").glob("*.md"):
        text = _read(path)
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", path.name)
        if not match:
            continue
        if re.search(r"^published:\s*false", text, re.M):
            continue
        year, month, day, slug = match.groups()
        moment = datetime(int(year), int(month), int(day))
        declared = re.search(
            r"^date:\s*\d{4}-\d{2}-\d{2}[ \t]+(\d{2}):(\d{2})", text, re.M
        )
        if declared:
            moment = moment.replace(
                hour=int(declared.group(1)), minute=int(declared.group(2))
            )
        posts[f"/{year}/{month}/{day}/{slug}.html"] = moment
    return posts


def _vi_post_dates():
    """VI post URL -> front-matter datetime, from `_vi_posts`.

    Day-only `date:` values mean midnight; #398 same-day posts declare
    `HH:MM` so the expectation model matches the layout's time sort.
    """
    posts = {}
    for path in (REPO_ROOT / "_vi_posts").glob("*.md"):
        match = re.search(
            r"^date:\s*(\d{4})-(\d{2})-(\d{2})(?:[ \t]+(\d{2}):(\d{2}))?",
            _read(path),
            re.M,
        )
        if not match:
            continue
        year, month, day, hour, minute = match.groups()
        posts[f"/vi/{year}/{month}/{day}/{path.stem}.html"] = datetime(
            int(year), int(month), int(day),
            int(hour or 0), int(minute or 0),
        )
    return posts


def _front_matter_tags(text):
    """Tag list from a post source, supporting inline and block forms."""
    match = FRONT_MATTER_RE.match(text)
    front_matter = match.group(1) if match else ""
    inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
    if inline:
        return [
            t.strip().strip("'\"")
            for t in inline.group(1).split(",")
            if t.strip()
        ]
    block = re.search(r"^tags:\s*\n((?:[ \t]*-[ \t]*.+?\n)+)", front_matter, re.M)
    if block:
        return [
            line.strip()[1:].strip().strip("'\"")
            for line in block.group(1).splitlines()
            if line.strip()
        ]
    return []


def _en_post_tags():
    """Published EN post URL -> tag list, from `_posts` front matter."""
    posts = {}
    for path in (REPO_ROOT / "_posts").glob("*.md"):
        text = _read(path)
        if re.search(r"^published:\s*false", text, re.M):
            continue
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", path.name)
        if not match:
            continue
        year, month, day, slug = match.groups()
        posts[f"/{year}/{month}/{day}/{slug}.html"] = _front_matter_tags(text)
    return posts


def _expected_related_links(page_url):
    """Data-driven Related expectation for a page with tag siblings.

    Mirrors the `_layouts/post.html` (#343) contract from the post sources
    instead of hardcoding URLs: the union over the page's tags of
    same-language published posts, newest-first, excluding the page itself.
    New posts sharing the tag extend the list without touching this test.
    """
    dates = _en_post_dates()
    tags = _en_post_tags()
    key = page_url if page_url.startswith("/") else "/" + page_url
    page_tags = set(tags.get(key, []))
    candidates = [
        (dates[url], url)
        for url, post_tags in tags.items()
        if url != key and page_tags & set(post_tags) and url in dates
    ]
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [url for _, url in candidates][:5]


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
    # #328: the fallback must never suggest posts newer than the page.
    assert "where_exp" in text
    assert "<= page.date" in text
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


def test_singleton_fallback_never_suggests_newer_posts(built_site):
    """#328: the Internet-post fallback lists nothing newer than itself."""
    for page, page_date, catalog in (
        (EN_SINGLETON, EN_SINGLETON_DATE, _en_post_dates()),
        (VI_SINGLETON, VI_SINGLETON_DATE, _vi_post_dates()),
    ):
        html = _read(built_site / page)
        sections = _sidebar_sections(html)
        assert len(sections) <= 1, f"{page}: want at most one section"
        if not sections:
            continue  # Suppressed: nothing that old left to suggest.
        _, links = sections[0]
        assert links, f"{page}: a rendered fallback must not be empty"
        for link in links:
            target_date = catalog.get(link)
            assert target_date is not None, (
                f"{page}: fallback links to unknown post {link}"
            )
            assert target_date <= page_date, (
                f"{page}: fallback must not suggest newer post "
                f"{link} ({target_date} > {page_date})"
            )


def test_sibling_posts_keep_true_related_section(built_site):
    html = _read(built_site / EN_RELATED)
    sections = _sidebar_sections(html)
    assert len(sections) == 1
    heading, links = sections[0]
    assert heading == "Related posts"
    expected = _expected_related_links(EN_RELATED)
    assert len(expected) >= 1, (
        f"{EN_RELATED}: test needs at least one tag sibling on master"
    )
    assert links == expected
    # Invariants that hold no matter how many siblings exist.
    assert len(links) == len(set(links)), "related links must not repeat"
    assert all(
        link.startswith("/") and not link.startswith("/vi/") for link in links
    ), f"related links must stay in the page's language: {links}"
