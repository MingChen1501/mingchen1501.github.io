"""Localized lifestyle tag (#129).

Owner decision: tag labels/URLs follow the page language. The lifestyle
pillar is `/tags/life/` with label "Life" on English pages and stays
`/vi/tags/doi-song/` with label "Đời sống" on Vietnamese ones; the old
`/tags/doi-song/` redirects permanently to `/tags/life/`. Technical tags
(`backend-production`, `ai-agent`, `linux-tooling`) keep the same slug and
English label in both languages. Post front matter keeps the canonical
`doi-song` key — only display labels and the EN tag-page permalink change.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted site.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_LABELS = REPO_ROOT / "_data" / "tag_labels.yml"
SITE_URL = "https://mingchen.id.vn"

TECHNICAL_TAGS = ["backend-production", "ai-agent", "linux-tooling"]
TECHNICAL_LABELS = {
    "backend-production": "Backend Production",
    "ai-agent": "AI Agent",
    "linux-tooling": "Linux Tooling",
}

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


def _tag_labels():
    assert TAG_LABELS.is_file(), "_data/tag_labels.yml is missing"
    return yaml.safe_load(TAG_LABELS.read_text(encoding="utf-8")) or {}


def _file_for(site_dir, url):
    """Map a site URL onto the file that serves it inside the built site."""
    path = url[len(SITE_URL):] if url.startswith(SITE_URL) else url
    if path in ("", "/"):
        return site_dir / "index.html"
    path_clean = path.lstrip("/")
    if path_clean.endswith("/"):
        return site_dir / path_clean / "index.html"
    if (site_dir / path_clean).suffix == "":
        return site_dir / path_clean / "index.html"
    return site_dir / path_clean


def _post_url(path):
    """Built URL of a published post source."""
    if path.parent == REPO_ROOT / "_posts":
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        return f"/{path.stem[:10].replace('-', '/')}/{slug}.html"
    date = _value(_front_matter(path), "date") or ""
    return f"/vi/{date.replace('-', '/')}/{path.stem}.html"


def _post_with_tag(posts_dir, tag):
    for path in sorted(posts_dir.glob("*.md")):
        front_matter = _front_matter(path)
        if _value(front_matter, "published") == "false":
            continue
        inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
        tags = (
            [t.strip().strip("'\"") for t in inline.group(1).split(",")]
            if inline
            else []
        )
        if tag in tags:
            return path
    raise AssertionError(f"no published post with tag {tag!r} in {posts_dir}")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_tag_labels_is_the_single_source_of_truth():
    labels = _tag_labels()
    assert set(labels) == set(TECHNICAL_TAGS + ["doi-song"])
    for key, entry in labels.items():
        for field in ("en", "vi", "slug_en", "slug_vi"):
            assert entry.get(field), f"tag_labels.yml[{key}] is missing `{field}`"
    # Technical tags keep the same slug and the English label in both.
    for key in TECHNICAL_TAGS:
        assert labels[key]["en"] == labels[key]["vi"] == TECHNICAL_LABELS[key], (
            f"technical tag {key} must keep its English label in both languages"
        )
        assert labels[key]["slug_en"] == labels[key]["slug_vi"] == key, (
            f"technical tag {key} must keep its slug in both languages"
        )
    # The lifestyle pillar is localized.
    assert labels["doi-song"]["en"] == "Life"
    assert labels["doi-song"]["slug_en"] == "life"
    assert labels["doi-song"]["vi"] == "Đời sống"
    assert labels["doi-song"]["slug_vi"] == "doi-song"


@pytest.mark.static
def test_english_life_page_replaces_doi_song_with_a_redirect():
    assert not (REPO_ROOT / "tags" / "doi-song.md").is_file(), (
        "tags/doi-song.md must go — the English page is tags/life.md"
    )
    life = REPO_ROOT / "tags" / "life.md"
    assert life.is_file(), "tags/life.md is missing"
    front_matter = _front_matter(life)
    assert _value(front_matter, "layout") == "tag"
    assert _value(front_matter, "lang") == "en"
    assert _value(front_matter, "ref") == "tag-doi-song", (
        "the EN page keeps ref tag-doi-song so hreflang still pairs it "
        "with the Vietnamese page"
    )
    assert _value(front_matter, "tag") == "doi-song", (
        "the canonical post tag key stays doi-song"
    )
    assert _value(front_matter, "permalink") == "/tags/life/"
    assert _value(front_matter, "title") == "Tag: Life"
    assert "/tags/doi-song/" in front_matter, (
        "tags/life.md must redirect_from the old /tags/doi-song/"
    )


@pytest.mark.static
def test_vietnamese_doi_song_page_keeps_slug_with_localized_title():
    page = REPO_ROOT / "vi" / "tags" / "doi-song.md"
    assert page.is_file(), "vi/tags/doi-song.md is missing"
    front_matter = _front_matter(page)
    assert _value(front_matter, "tag") == "doi-song"
    assert _value(front_matter, "ref") == "tag-doi-song"
    assert _value(front_matter, "permalink") == "/vi/tags/doi-song/"
    assert _value(front_matter, "title") == "Tag: Đời sống"


@pytest.mark.static
def test_post_taxonomy_keeps_the_canonical_doi_song_key():
    """Front matter is untouched: posts still declare `doi-song`, never the
    localized `life` slug."""
    for posts_dir in (REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"):
        for path in sorted(posts_dir.glob("*.md")):
            front_matter = _front_matter(path)
            if _value(front_matter, "published") == "false":
                continue
            inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
            tags = (
                [t.strip().strip("'\"") for t in inline.group(1).split(",")]
                if inline
                else []
            )
            assert "life" not in tags, (
                f"{path.name} must keep the canonical `doi-song` key, not `life`"
            )


@pytest.mark.static
def test_templates_resolve_labels_from_tag_labels_yml():
    for path in (
        REPO_ROOT / "_includes" / "post-tags.html",
        REPO_ROOT / "_layouts" / "tag.html",
        REPO_ROOT / "_includes" / "site-sidebar.html",
        REPO_ROOT / "tags.md",
        REPO_ROOT / "vi" / "tags.md",
    ):
        html = _read(path)
        assert "site.data.tag_labels" in html, (
            f"{path.relative_to(REPO_ROOT)} must read labels from "
            "_data/tag_labels.yml"
        )


# --- build guards (need Ruby; no browser) -----------------------------------


def test_english_life_page_renders_and_old_url_redirects(built_site):
    life = built_site / "tags" / "life" / "index.html"
    assert life.is_file(), "/tags/life/ is missing from the build"
    html = life.read_text(encoding="utf-8")
    assert "http-equiv=\"refresh\"" not in html, "/tags/life/ must be a page, not a redirect"
    assert re.search(r"<h1 class=\"page-heading\">Life</h1>", html), (
        "/tags/life/ must head with the Life label"
    )
    assert "Tag: Life" in html, "/tags/life/ must carry the Life title"
    assert "doi-song" not in re.search(
        r"<h1.*?</h1>", html, re.S
    ).group(0), "the /tags/life/ heading must not leak the canonical key"

    old = built_site / "tags" / "doi-song" / "index.html"
    assert old.is_file(), "old URL /tags/doi-song/ is missing from the build (must redirect)"
    stub = old.read_text(encoding="utf-8")
    assert "http-equiv=\"refresh\"" in stub, (
        "/tags/doi-song/ must emit a redirect stub, not a page"
    )
    assert "/tags/life/" in stub, "/tags/doi-song/ must redirect to /tags/life/"


def test_vietnamese_doi_song_page_renders_localized_label(built_site):
    page = built_site / "vi" / "tags" / "doi-song" / "index.html"
    assert page.is_file(), "/vi/tags/doi-song/ is missing from the build"
    html = page.read_text(encoding="utf-8")
    assert re.search(r"<h1 class=\"page-heading\">Đời sống</h1>", html), (
        "/vi/tags/doi-song/ must head with the Đời sống label"
    )


def _chips(html):
    return [
        (text.strip(), href)
        for href, text in re.findall(
            r'<a class="tag-chip"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html
        )
    ]


def test_post_chips_link_the_tag_page_of_the_current_language(built_site):
    en_post = _post_with_tag(REPO_ROOT / "_posts", "doi-song")
    en_html = _file_for(built_site, _post_url(en_post)).read_text(encoding="utf-8")
    en_chips = dict((href, text) for text, href in _chips(en_html))
    assert en_chips.get("/tags/life/") == "Life", (
        f"the English post must chip Life -> /tags/life/: {_chips(en_html)}"
    )
    assert not any(
        href.startswith("/vi/") for _, href in _chips(en_html)
    ), "English post chips must not jump to /vi/"

    vi_post = _post_with_tag(REPO_ROOT / "_vi_posts", "doi-song")
    vi_html = _file_for(built_site, _post_url(vi_post)).read_text(encoding="utf-8")
    vi_chips = dict((href, text) for text, href in _chips(vi_html))
    assert vi_chips.get("/vi/tags/doi-song/") == "Đời sống", (
        "the Vietnamese post must chip Đời sống -> /vi/tags/doi-song/: "
        f"{_chips(vi_html)}"
    )
    assert not any(
        href.startswith("/tags/") and not href.startswith("/vi/")
        for _, href in _chips(vi_html)
    ), "Vietnamese post chips must not jump to the English tag pages"


def test_tag_hreflang_pairs_english_life_with_vietnamese_doi_song(built_site):
    en_html = (built_site / "tags" / "life" / "index.html").read_text(encoding="utf-8")
    alternates = dict(
        (hreflang, href)
        for hreflang, href in re.findall(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', en_html
        )
    )
    assert alternates.get("en") == f"{SITE_URL}/tags/life/"
    assert alternates.get("vi") == f"{SITE_URL}/vi/tags/doi-song/"
    assert alternates.get("x-default") == f"{SITE_URL}/tags/life/"

    vi_html = (built_site / "vi" / "tags" / "doi-song" / "index.html").read_text(
        encoding="utf-8"
    )
    vi_alternates = dict(
        (hreflang, href)
        for hreflang, href in re.findall(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', vi_html
        )
    )
    assert vi_alternates.get("en") == f"{SITE_URL}/tags/life/"
    assert vi_alternates.get("vi") == f"{SITE_URL}/vi/tags/doi-song/"


def test_sitemap_lists_life_and_not_the_old_url(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    assert f"{SITE_URL}/tags/life/" in sitemap, "the sitemap must list /tags/life/"
    assert f"{SITE_URL}/vi/tags/doi-song/" in sitemap, (
        "the sitemap must list /vi/tags/doi-song/"
    )
    assert "/tags/doi-song/" not in [
        loc
        for loc in re.findall(r"<loc>(.*?)</loc>", sitemap)
        if "/vi/tags/doi-song/" not in loc
    ], "the sitemap must not list the old /tags/doi-song/"


def test_technical_tags_are_unchanged_in_both_languages(built_site):
    for key, label in TECHNICAL_LABELS.items():
        for url, heading in (
            (f"/tags/{key}/", label),
            (f"/vi/tags/{key}/", label),
        ):
            built = _file_for(built_site, url)
            assert built.is_file(), f"{url} is missing from the build"
            html = built.read_text(encoding="utf-8")
            assert re.search(
                rf"<h1 class=\"page-heading\">{re.escape(heading)}</h1>", html
            ), f"{url} must head with the English label {label!r}"


def test_feeds_never_list_tag_page_urls(built_site):
    for rel in ("feed.xml", "vi/feed.xml"):
        feed = (built_site / rel).read_text(encoding="utf-8")
        assert "/tags/doi-song/" not in feed, f"/{rel} lists the retired tag URL"
        assert "/tags/life/" not in feed, f"/{rel} must not list tag pages"
