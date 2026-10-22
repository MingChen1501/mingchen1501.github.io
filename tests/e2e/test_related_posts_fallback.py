"""Guards for #386 (post sidebar shows Related posts and Latest posts together).

Background: a post page used to show either Related posts (same topic) or a
Latest-posts fallback when its topic had no siblings (#328/#306/#112). The
owner direction (2026-10-22) wants both sections at the same time:

1. Related posts — the same-topic union (#343) over all the post's tags,
   de-duplicated, newest first, cap 5, current page excluded;
2. Latest posts — the newest posts of the same language below Related,
   excluding the current page and anything already listed under Related,
   cap 3 (#386 supersedes the #328 no-newer rule for this section).

Guarded here:

- (static) the layout builds both sections from the page's language
  source (`site.posts` / nil-safe `site.vi_posts`), renders Related first
  (cap five) then Latest (cap three) with the same `related-posts` list
  markup, excludes the current page from both and Related entries from
  Latest, keeps honest localized headings, and no longer filters Latest to
  `date <= page.date` (the old single-section fallback is gone);
- (built HTML) a tagged post with siblings renders Related then Latest
  with no overlap and without the current page; the singleton-tag Internet
  pages (no published siblings) render Latest only; EN/VI isolation holds;
- (overlay build) a fixture where the current page is among the newest
  posts proves it is absent from both lists and no URL repeats across the
  two sections.
"""

import contextlib
import functools
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

EN_SINGLETON = "2022/12/25/explaining-the-internet.html"
VI_SINGLETON = "vi/2022/12/25/gioi-thieu-ve-internet.html"
EN_RELATED = "2026/10/17/real-world-agent-orchestration-with-free-opencode.html"
EN_ONE_SIBLING = "2026/10/22/back-to-linux-fundamentals.html"

EN_NEWEST_STEM = "2026-10-21-newest-guard-post"
VI_NEWEST_STEM = "newest-guard-post"
EN_NEWEST_URL = "/2026/10/21/newest-guard-post.html"
VI_NEWEST_URL = "/vi/2026/10/21/newest-guard-post.html"


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
def test_layout_renders_related_then_latest_with_shared_markup():
    text = _read(POST_LAYOUT)
    assert "latest_source" in text
    assert "related_urls" in text
    assert "latest_posts" in text
    assert "related_count" in text
    # The English source is the published EN stream; the Vietnamese source
    # is the nil-safe collection (upstream CI builds without it).
    assert "latest_source = site.posts" in text
    assert "latest_source = rel_vi_source" in text
    # Related first (cap five), Latest below (cap three), same list markup.
    assert text.index("related_count") < text.index("latest_posts")
    assert "shown < 5" in text
    assert "latest_shown < 3" in text
    assert text.count('class="related-posts"') >= 2
    # Honest headings in both languages for both sections.
    assert "Related posts" in text
    assert "Bài viết cùng chủ đề" in text
    assert "Latest posts" in text
    assert "Bài viết mới nhất" in text
    # The old single-section fallback is gone: no mode flag, no no-newer
    # filter on the Latest section (#386 supersedes #328 here).
    assert "use_latest" not in text
    assert "<= page.date" not in text


@pytest.mark.static
def test_layout_excludes_current_and_related_from_latest():
    text = _read(POST_LAYOUT)
    assert "other.url != page.url" in text
    assert "latest_post.url == page.url" in text
    assert "related_urls contains" in text


# --- built-HTML guards (need the real `jekyll build`, no browser) ----------


def test_tagged_post_with_siblings_shows_related_then_latest(built_site):
    html = _read(built_site / EN_RELATED)
    sections = _sidebar_sections(html)
    assert len(sections) == 2, f"{EN_RELATED}: want Related + Latest, got {sections}"
    (related_heading, related_links), (latest_heading, latest_links) = sections
    assert related_heading == "Related posts"
    assert latest_heading == "Latest posts"
    expected = _expected_related_links(EN_RELATED)
    assert len(expected) >= 1, (
        f"{EN_RELATED}: test needs at least one tag sibling on master"
    )
    assert related_links == expected
    assert 1 <= len(related_links) <= 5
    assert 1 <= len(latest_links) <= 3
    # Current page absent from both; no URL repeats across sections.
    assert f"/{EN_RELATED}" not in related_links + latest_links
    assert not (set(related_links) & set(latest_links)), (
        f"{EN_RELATED}: Related and Latest must not overlap: "
        f"{related_links} vs {latest_links}"
    )
    # Language isolation: English lists stay out of /vi/.
    for link in related_links + latest_links:
        assert link.startswith("/") and not link.startswith("/vi/"), (
            f"{EN_RELATED}: lists must stay in the page's language: {link}"
        )


def test_singleton_posts_render_latest_only(built_site):
    for page, heading, prefix in (
        (EN_SINGLETON, "Latest posts", "/"),
        (VI_SINGLETON, "Bài viết mới nhất", "/vi/"),
    ):
        html = _read(built_site / page)
        sections = _sidebar_sections(html)
        assert len(sections) == 1, f"{page}: want Latest only, got {sections}"
        section_heading, links = sections[0]
        assert section_heading == heading, f"{page}: {section_heading!r}"
        assert 1 <= len(links) <= 3, f"{page}: {len(links)} links"
        assert all(link.startswith(prefix) for link in links), (
            f"{page}: latest links must stay in the page's language: {links}"
        )
        if prefix == "/":
            assert all(not link.startswith("/vi/") for link in links)
        assert not any(link.endswith("internet.html") for link in links), (
            f"{page}: latest must exclude the current page"
        )


def test_latest_section_may_list_newer_posts(built_site):
    """#386 supersedes the #328 no-newer rule for the Latest section."""
    catalog = _en_post_dates()
    page_date = datetime(2022, 12, 25)
    html = _read(built_site / EN_SINGLETON)
    _, links = _sidebar_sections(html)[0]
    assert any(catalog.get(link, page_date) > page_date for link in links), (
        f"{EN_SINGLETON}: Latest should list posts newer than the page (#386)"
    )


def test_one_sibling_post_keeps_both_sections_without_overlap(built_site):
    html = _read(built_site / EN_ONE_SIBLING)
    sections = _sidebar_sections(html)
    assert len(sections) == 2, f"{EN_ONE_SIBLING}: want two sections"
    (related_heading, related_links), (latest_heading, latest_links) = sections
    assert related_heading == "Related posts"
    assert latest_heading == "Latest posts"
    assert f"/{EN_ONE_SIBLING}" not in related_links + latest_links
    assert not (set(related_links) & set(latest_links))


# --- overlay build: current page among the newest posts ---------------------


def _write_en_newest(posts_dir):
    (posts_dir / f"{EN_NEWEST_STEM}.md").write_text(
        "---\n"
        "layout: post\n"
        "lang: en\n"
        "ref: newest-guard-post\n"
        "author: Ming Chen\n"
        'title: "Newest guard post"\n'
        "tags: [ai-agent]\n"
        'description: "Synthetic #386 fixture: the newest EN post proves the current page stays out of both sidebar lists."\n'
        "---\n\n"
        "Fixture body.\n",
        encoding="utf-8",
    )


def _write_vi_newest(posts_dir):
    (posts_dir / f"{VI_NEWEST_STEM}.md").write_text(
        "---\n"
        "layout: post\n"
        "lang: vi\n"
        "ref: newest-guard-post\n"
        "date: 2026-10-21\n"
        "author: Ming Chen\n"
        'title: "Bai moi nhat guard"\n'
        "tags: [ai-agent]\n"
        'description: "Bai fixture cho #386: bai moi nhat khong tu liet ke trong sidebar."\n'
        "---\n\n"
        "Noi dung fixture.\n",
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def newest_overlay_site(tmp_path_factory):
    """Isolated copy of the repo plus a newest-dated EN+VI fixture pair.

    The fixtures use 2026-10-21: among the newest posts on master but still
    in the past, so Jekyll builds them (future-dated posts are skipped).
    """
    import shutil as _shutil

    bundle = _shutil.which("bundle")
    if bundle is None:
        pytest.skip("`bundle` not found: the overlay build needs Ruby + Jekyll")
    overlay = tmp_path_factory.getbasetemp() / "newest-guard-overlay"
    _shutil.copytree(
        REPO_ROOT,
        overlay,
        ignore=_shutil.ignore_patterns(".git", "_site", ".jekyll-cache"),
    )
    _write_en_newest(overlay / "_posts")
    _write_vi_newest(overlay / "_vi_posts")
    destination = tmp_path_factory.mktemp("newest-guard-build")
    env = {k: v for k, v in os.environ.items() if k != "JEKYLL_ENV"}
    env["PATH"] = os.pathsep.join(
        [str(Path(bundle).parent), env.get("PATH", "")]
    ).rstrip(os.pathsep)
    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(overlay),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"overlay `jekyll build` failed:\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    return destination


def test_newest_post_absent_from_both_lists_without_overlap(newest_overlay_site):
    """The current page stays out of both lists even when it is newest."""
    for page, heading_related, heading_latest, prefix in (
        (EN_NEWEST_URL, "Related posts", "Latest posts", "/"),
        (VI_NEWEST_URL, "Bài viết cùng chủ đề", "Bài viết mới nhất", "/vi/"),
    ):
        html = _read(newest_overlay_site / page.lstrip("/"))
        sections = _sidebar_sections(html)
        assert len(sections) == 2, f"{page}: want Related + Latest, got {sections}"
        (related_heading, related_links), (latest_heading, latest_links) = sections
        assert related_heading == heading_related, f"{page}: {related_heading!r}"
        assert latest_heading == heading_latest, f"{page}: {latest_heading!r}"
        assert 1 <= len(related_links) <= 5, f"{page}: {related_links}"
        assert 1 <= len(latest_links) <= 3, f"{page}: {latest_links}"
        combined = related_links + latest_links
        assert page not in combined, f"{page}: lists the current page"
        assert len(combined) == len(set(combined)), (
            f"{page}: a URL repeats across the two sections: {combined}"
        )
        for link in combined:
            assert link.startswith(prefix), (
                f"{page}: link {link} leaves the page's language"
            )
            if prefix == "/":
                assert not link.startswith("/vi/"), (
                    f"{page}: English list leaks a Vietnamese post {link}"
                )
