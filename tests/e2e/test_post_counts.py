"""Post-count copy guards (#149).

Two small count/copy defects: ``_layouts/tag.html`` rendered
``{{ tag_posts | size }} posts tagged with`` unconditionally (so a
single-post tag read "1 posts"), and the EN/VI homes could silently
disagree about the archive size.

Decision (documented here and in ``_layouts/home.html``): totals are
language-specific — the English home counts the English-only
``site.posts`` while the Vietnamese home counts ``site.vi_posts``
(translations lag the originals). Both homes paginate 5 per page (#155)
and each home states its own total, so the sizes are never silently
compared. English inflects ("1 post" / "N posts"); Vietnamese nouns do
not ("1 bài" / "N bài" share one form).

Static guards (no Ruby) cover the template contract; build guards (need
Ruby, no browser) cover the emitted copy.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_LABELS = REPO_ROOT / "_data" / "tag_labels.yml"

PILLARS = ["backend-production", "ai-agent", "linux-tooling", "doi-song"]
EN_PER_PAGE = 5
VI_PER_PAGE = 5

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _value(block, key):
    match = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", block, re.M)
    if not match:
        return None
    value = match.group(1)
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _published_posts(posts_dir):
    """Published post sources in a directory (``published: false`` excluded)."""
    posts = []
    for path in sorted(posts_dir.glob("*.md")):
        if _value(_front_matter(path), "published") == "false":
            continue
        posts.append(path)
    return posts


def _post_tags(path):
    front_matter = _front_matter(path)
    inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
    if not inline:
        return []
    return [t.strip().strip("'\"") for t in inline.group(1).split(",")]


def _pillar_count(posts_dir, pillar):
    return sum(1 for p in _published_posts(posts_dir) if pillar in _post_tags(p))


def _slugs(lang):
    labels = yaml.safe_load(TAG_LABELS.read_text(encoding="utf-8")) or {}
    key = "slug_en" if lang == "en" else "slug_vi"
    return {pillar: labels[pillar][key] for pillar in PILLARS}


def _squashed(html):
    return re.sub(r"\s+", " ", html)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_tag_layout_pluralizes_the_english_count():
    layout = _read(REPO_ROOT / "_layouts" / "tag.html")
    assert re.search(r"\{\%\s*if\s+tag_posts\.size\s*!=\s*1\s*\%\}s", layout), (
        "_layouts/tag.html must branch the English 'post'/'posts' on the count"
    )
    assert "1 posts" not in layout, (
        "_layouts/tag.html must not hard-code the unconditional 'posts' form"
    )


@pytest.mark.static
def test_tag_layout_keeps_the_vietnamese_count_invariant():
    """Vietnamese nouns do not inflect: 'N bài viết' is correct for N = 1."""
    layout = _read(REPO_ROOT / "_layouts" / "tag.html")
    assert re.search(
        r"\{\{\s*tag_posts\s*\|\s*size\s*\}\}\s*bài viết với tag", layout
    ), "_layouts/tag.html must keep the invariant Vietnamese count form"


@pytest.mark.static
def test_tag_indexes_pluralize_per_language():
    english = _read(REPO_ROOT / "tags.md")
    assert re.search(r"\{\%\s*if\s+index_posts\.size\s*!=\s*1\s*\%\}s", english), (
        "tags.md must branch 'post'/'posts' on the count"
    )
    vietnamese = _read(REPO_ROOT / "vi" / "tags.md")
    assert re.search(
        r"\{\{\s*index_posts\s*\|\s*size\s*\}\}\s*bài</span>", vietnamese
    ), "vi/tags.md must keep the invariant 'N bài' count form"


@pytest.mark.static
def test_sidebar_pluralizes_its_topic_counts():
    """The sidebar topic rows share the tag-index count contract (#149)."""
    sidebar = _read(REPO_ROOT / "_includes" / "site-sidebar.html")
    assert re.search(r"\{\%\s*if\s+sidebar_tag_posts\.size\s*!=\s*1\s*\%\}s", sidebar), (
        "site-sidebar.html must branch the English 'post'/'posts' on the count"
    )


@pytest.mark.static
def test_home_layout_states_a_per_language_total():
    """Each home states its own language-specific total (#149).

    The English home counts the paginator stream (``site.posts``) while the
    Vietnamese home counts ``site.vi_posts``; both windows stay at 5 per
    page (#155) so the pages agree and only the totals may differ.
    """
    layout = _read(REPO_ROOT / "_layouts" / "home.html")
    assert "paginator.total_posts" in layout, (
        "the EN home count must use the paginator total"
    )
    assert re.search(r"home_total\s*=\s*vi_total", layout), (
        "the VI home count must use the Vietnamese collection total"
    )
    assert re.search(r"Showing.*of.*home_total.*post", layout), (
        "the EN home must render its total with singular/plural copy"
    )
    assert re.search(r"Hiển thị.*home_total.*bài", layout), (
        "the VI home must render its total"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def test_no_page_anywhere_renders_one_posts(built_site):
    """No emitted page renders the '1 posts' form — the sidebar topic rows
    appear on the homes and every tag page too (#149)."""
    offenders = []
    for page in built_site.rglob("*.html"):
        if re.search(r"\b1 posts\b", _squashed(page.read_text(encoding="utf-8"))):
            offenders.append(page.relative_to(built_site).as_posix())
    assert not offenders, f"pages rendering '1 posts': {offenders}"


def _tag_intro(html):
    match = re.search(r'<p class="tag-page__intro">(.*?)</p>', html, re.S)
    assert match is not None, "tag page must render <p class=\"tag-page__intro\">"
    return _squashed(match.group(1))


def test_single_post_tag_pages_read_singular(built_site):
    """A tag with exactly one post reads '1 post ...' in EN (#149)."""
    en_slugs = _slugs("en")
    vi_slugs = _slugs("vi")
    checked_en = checked_vi = 0
    for pillar in PILLARS:
        en_count = _pillar_count(REPO_ROOT / "_posts", pillar)
        if en_count == 1:
            html = (
                built_site / "tags" / en_slugs[pillar] / "index.html"
            ).read_text(encoding="utf-8")
            intro = _tag_intro(html)
            assert "1 post tagged with" in intro, (
                f"/tags/{en_slugs[pillar]}/ must read '1 post tagged with': {intro!r}"
            )
            checked_en += 1
        vi_count = _pillar_count(REPO_ROOT / "_vi_posts", pillar)
        if vi_count == 1:
            html = (
                built_site / "vi" / "tags" / vi_slugs[pillar] / "index.html"
            ).read_text(encoding="utf-8")
            intro = _tag_intro(html)
            assert "1 bài viết với tag" in intro, (
                f"/vi/tags/{vi_slugs[pillar]}/ must read '1 bài viết với tag': {intro!r}"
            )
            checked_vi += 1
    assert checked_en >= 1, "no single-post EN tag found — the guard covers nothing"
    assert checked_vi >= 1, "no single-post VI tag found — the guard covers nothing"


def test_no_tag_page_renders_one_posts(built_site):
    """No emitted tag page ever renders the '1 posts' form (#149)."""
    pages = list((built_site / "tags").rglob("index.html")) + list(
        (built_site / "vi" / "tags").rglob("index.html")
    )
    assert pages, "no tag pages in the build"
    for page in pages:
        squashed = _squashed(page.read_text(encoding="utf-8"))
        assert re.search(r"\b1 posts\b", squashed) is None, (
            f"{page} renders '1 posts'"
        )


def test_tag_pages_state_their_exact_post_count(built_site):
    """Every tag page intro states its language-specific post count (#149)."""
    en_slugs = _slugs("en")
    vi_slugs = _slugs("vi")
    for pillar in PILLARS:
        en_count = _pillar_count(REPO_ROOT / "_posts", pillar)
        html = (
            built_site / "tags" / en_slugs[pillar] / "index.html"
        ).read_text(encoding="utf-8")
        noun = "post" if en_count == 1 else "posts"
        assert f"{en_count} {noun} tagged with" in _tag_intro(html), (
            f"/tags/{en_slugs[pillar]}/ must read '{en_count} {noun} tagged with'"
        )
        vi_count = _pillar_count(REPO_ROOT / "_vi_posts", pillar)
        html = (
            built_site / "vi" / "tags" / vi_slugs[pillar] / "index.html"
        ).read_text(encoding="utf-8")
        assert f"{vi_count} bài viết với tag" in _tag_intro(html), (
            f"/vi/tags/{vi_slugs[pillar]}/ must read '{vi_count} bài viết với tag'"
        )


def test_tag_indexes_pluralize_counts(built_site):
    """`/tags/` and `/vi/tags/` pluralize their per-topic counts (#149)."""
    english = _squashed((built_site / "tags" / "index.html").read_text(encoding="utf-8"))
    for pillar in PILLARS:
        count = _pillar_count(REPO_ROOT / "_posts", pillar)
        noun = "post" if count == 1 else "posts"
        assert f"{count} {noun}</span>" in english, (
            f"`/tags/` must show '{count} {noun}' for {pillar}"
        )
    assert re.search(r"\b1 posts\b", english) is None, "`/tags/` renders '1 posts'"
    vietnamese = _squashed(
        (built_site / "vi" / "tags" / "index.html").read_text(encoding="utf-8")
    )
    for pillar in PILLARS:
        count = _pillar_count(REPO_ROOT / "_vi_posts", pillar)
        assert f"{count} bài</span>" in vietnamese, (
            f"`/vi/tags/` must show '{count} bài' for {pillar}"
        )


def _home_count(html):
    match = re.search(r'<p class="home-count">(.*?)</p>', html, re.S)
    assert match is not None, "home must render <p class=\"home-count\">"
    return _squashed(match.group(1))


def test_homes_state_their_language_specific_totals(built_site):
    """`/` and `/vi/` state their own totals over the same 5-per-page window."""
    en_total = len(_published_posts(REPO_ROOT / "_posts"))
    vi_total = len(_published_posts(REPO_ROOT / "_vi_posts"))

    index = _home_count(
        (built_site / "index.html").read_text(encoding="utf-8")
    )
    assert index == (
        f"Showing {min(EN_PER_PAGE, en_total)} of {en_total} "
        f"{'post' if en_total == 1 else 'posts'}"
    ), f"`/` states the wrong window/total: {index!r}"

    vi_index = _home_count(
        (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    )
    assert vi_index == (
        f"Hiển thị {min(VI_PER_PAGE, vi_total)} trong {vi_total} bài"
    ), f"`/vi/` states the wrong window/total: {vi_index!r}"


def test_second_pages_state_the_remainder_of_their_total(built_site):
    """Page 2 of each home shows the leftover window against the same total."""
    en_total = len(_published_posts(REPO_ROOT / "_posts"))
    vi_total = len(_published_posts(REPO_ROOT / "_vi_posts"))
    if en_total > EN_PER_PAGE:
        page2 = _home_count(
            (built_site / "page2" / "index.html").read_text(encoding="utf-8")
        )
        assert page2 == (
            f"Showing {en_total - EN_PER_PAGE} of {en_total} "
            f"{'post' if en_total == 1 else 'posts'}"
        ), f"`/page2/` states the wrong window/total: {page2!r}"
    if vi_total > VI_PER_PAGE:
        vi_page2 = _home_count(
            (built_site / "vi" / "page2" / "index.html").read_text(encoding="utf-8")
        )
        assert vi_page2 == (
            f"Hiển thị {vi_total - VI_PER_PAGE} trong {vi_total} bài"
        ), f"`/vi/page2/` states the wrong window/total: {vi_page2!r}"
