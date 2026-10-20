"""Bilingual SEO surface, phase 3 (#98, after #93/#96/#97).

English default at `/` (`_posts/`, jekyll-feed `/feed.xml`), Vietnamese under
`/vi/` (the `site.vi_posts` collection, the Liquid-mirrored `/vi/feed.xml`).
Every sitemap entry links its counterpart via `xhtml:link` alternates (same
`ref` resolution as the head `hreflang` links); `llms.txt` maps each language
in its own section; each language's pages advertise their own feed in `head`.

Static guards (no Ruby) cover the source contract; build guards (need Ruby, no
browser) cover the emitted site.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://mingchen.id.vn"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"
ATOM_NS = "http://www.w3.org/2005/Atom"

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


def _file_for(site_dir, url):
    """Map a site URL onto the file that serves it inside the built site."""
    if url.startswith(SITE_URL):
        path = url[len(SITE_URL):]
    elif url.startswith("http://mingchen.id.vn"):
        path = url[len("http://mingchen.id.vn"):]
    else:
        path = url
    if path in ("", "/"):
        return site_dir / "index.html"
    path_clean = path.lstrip("/")
    if path_clean.endswith("/"):
        return site_dir / path_clean / "index.html"
    if (site_dir / path_clean).suffix == "":
        return site_dir / path_clean / "index.html"
    return site_dir / path_clean


def _sitemap_root(built_site):
    sitemap_path = built_site / "sitemap.xml"
    assert sitemap_path.exists(), "sitemap.xml must exist in the build"
    try:
        return ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        pytest.fail("sitemap.xml does not parse as valid XML")


def _sitemap_entries(root):
    """`(loc, {hreflang: href})` for every `<url>` in the sitemap."""
    entries = []
    for url in root.findall(f".//{{{SITEMAP_NS}}}url"):
        loc_el = url.find(f"{{{SITEMAP_NS}}}loc")
        assert loc_el is not None and loc_el.text, "every sitemap <url> needs a <loc>"
        alternates = {}
        for link in url.findall(f"{{{XHTML_NS}}}link"):
            hreflang = link.attrib.get("hreflang")
            href = link.attrib.get("href")
            assert hreflang and href, "every xhtml:link needs hreflang + href"
            assert hreflang not in alternates, f"duplicate xhtml:link hreflang={hreflang} on {loc_el.text}"
            alternates[hreflang] = href
        entries.append((loc_el.text, alternates))
    return entries


def _head_alternates(html):
    return dict(
        (hreflang, href)
        for hreflang, href in re.findall(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html
        )
    )


def _feed_entries(feed_path):
    """`(self_href, [entry_hrefs])` of an Atom feed file."""
    assert feed_path.exists(), f"{feed_path} must exist in the build"
    try:
        root = ET.fromstring(feed_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        pytest.fail(f"{feed_path} does not parse as valid XML")
    assert root.tag == f"{{{ATOM_NS}}}feed", f"{feed_path} must be an Atom feed"
    self_href = None
    for link in root.findall(f"{{{ATOM_NS}}}link"):
        if link.attrib.get("rel") == "self":
            self_href = link.attrib.get("href")
    entry_hrefs = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        link = entry.find(f"{{{ATOM_NS}}}link")
        assert link is not None, f"an entry in {feed_path} has no link"
        entry_hrefs.append(link.attrib.get("href"))
    return root, self_href, entry_hrefs


def _published_posts(posts_dir):
    return sorted(
        p for p in posts_dir.glob("*.md")
        if "published: false" not in _read(p)
    )


def _post_url(path):
    """Built URL of a published post source."""
    if path.parent == REPO_ROOT / "_posts":
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        return f"/{path.stem[:10].replace('-', '/')}/{slug}.html"
    date = _value(_front_matter(path), "date") or ""
    return f"/vi/{date.replace('-', '/')}/{path.stem}.html"


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_sitemap_source_declares_xhtml_and_covers_vi():
    sitemap = _read(REPO_ROOT / "sitemap.xml")
    assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in sitemap
    assert "include sitemap-alternates.html" in sitemap
    assert "site.vi_posts" in sitemap, "the sitemap must list the Vietnamese collection"
    assert "/vi/" in sitemap, "the sitemap must list the Vietnamese homepage"
    assert "/vi/page" in sitemap, "the sitemap must enumerate the paginated VI pages (#155)"
    include = REPO_ROOT / "_includes" / "sitemap-alternates.html"
    assert include.is_file(), "the sitemap alternates include is missing"
    snippet = _read(include)
    assert "site.vi_posts" in snippet
    for hreflang in ('hreflang="en"', 'hreflang="vi"', 'hreflang="x-default"'):
        assert hreflang in snippet, f"sitemap alternates must emit {hreflang}"


@pytest.mark.static
def test_llms_source_has_two_language_sections():
    llms = _read(REPO_ROOT / "llms.txt")
    assert "## English" in llms, "llms.txt needs an English section"
    assert "## Ti" in llms and "ng Vi" in llms, "llms.txt needs a Vietnamese section"
    assert "site.vi_posts" in llms, "llms.txt must map the Vietnamese collection"


@pytest.mark.static
def test_vi_feed_source_mirrors_jekyll_feed_and_is_nil_safe():
    feed = REPO_ROOT / "vi" / "feed.xml"
    assert feed.is_file(), "vi/feed.xml (the Vietnamese Atom feed) is missing"
    source = _read(feed)
    assert 'layout: null' in _front_matter(feed)
    assert "site.vi_posts" in source
    # `sort`/`where_exp` crash on nil: the collection must be read through a
    # nil-guarded variable for the `_config_theme-dev.yml` CI build, where the
    # collection is undefined.
    assert "== nil" in source, "vi/feed.xml must nil-guard the collection"
    assert '"" | split: ""' in source
    # Same Atom shape and limits as the jekyll-feed template behind /feed.xml.
    assert 'xmlns="http://www.w3.org/2005/Atom"' in source
    assert 'rel="self"' in source
    assert "<entry" in source and "</entry>" in source
    assert "posts_limit" in source and "default: 10" in source


@pytest.mark.static
def test_head_wires_a_feed_link_per_language():
    head = _read(REPO_ROOT / "_includes" / "head.html")
    assert "feed_meta" in head, "English pages keep the jekyll-feed link"
    assert "/vi/feed.xml" in head, "Vietnamese pages must advertise /vi/feed.xml"
    assert "page.lang" in head, "the feed link must follow the page language"


# --- build guards (need Ruby; no browser) -----------------------------------


def test_sitemap_lists_vi_home_and_vi_posts(built_site):
    root = _sitemap_root(built_site)
    locs = [loc for loc, _ in _sitemap_entries(root)]
    assert f"{SITE_URL}/vi/" in locs, "the sitemap must list the Vietnamese homepage"
    for path in _published_posts(REPO_ROOT / "_vi_posts"):
        url = f"{SITE_URL}{_post_url(path)}"
        assert url in locs, f"the sitemap is missing the Vietnamese post {url}"


def test_sitemap_alternates_resolve_and_match_head(built_site):
    """Every entry carries en/vi/x-default alternates that resolve — and match
    the `hreflang` links the head renders for that same URL (#93)."""
    entries = _sitemap_entries(_sitemap_root(built_site))
    assert entries, "the sitemap must contain entries"
    checked = 0
    for loc, alternates in entries:
        assert {"en", "vi", "x-default"} <= set(alternates), (
            f"{loc} is missing xhtml:link alternates: {alternates}"
        )
        assert alternates["x-default"] == alternates["en"], (
            f"{loc} x-default must point at the English URL"
        )
        for hreflang, href in alternates.items():
            assert href.startswith(SITE_URL), (
                f"{loc} hreflang={hreflang} must be absolute: {href}"
            )
            assert _file_for(built_site, href).is_file(), (
                f"{loc} hreflang={hreflang} points at {href}, "
                "which is not in the build"
            )
        # The sitemap alternates must agree with the head alternates of the
        # page served at that URL.
        built = _file_for(built_site, loc)
        assert built.is_file(), f"sitemap loc {loc} is not in the build"
        head = _head_alternates(built.read_text(encoding="utf-8"))
        assert head == alternates, (
            f"{loc} sitemap alternates {alternates} disagree with "
            f"the head alternates {head}"
        )
        checked += 1
    assert checked > 20, "the sitemap alternates guard measured almost nothing"


def test_llms_txt_has_two_language_sections_with_resolving_urls(built_site):
    """`llms.txt` maps English under `## English` and Vietnamese under
    `## Tiếng Việt`; every listed site URL resolves to a built file."""
    llms_path = built_site / "llms.txt"
    assert llms_path.exists(), "llms.txt must exist in the build"
    lines = llms_path.read_text(encoding="utf-8").splitlines()

    sections = {}
    current = None
    for line in lines:
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            sections.setdefault(current, [])
            continue
        bullet = re.match(r"^-\s+(https?://\S+?):\s", line)
        if bullet and current is not None:
            sections[current].append(bullet.group(1))

    assert "English" in sections, "llms.txt needs a `## English` section"
    vi_heading = next((h for h in sections if "Vi" in h), None)
    assert vi_heading is not None, "llms.txt needs a Vietnamese section"
    en_urls = sections["English"]
    vi_urls = sections[vi_heading]
    assert en_urls, "the English llms.txt section lists no URLs"
    assert vi_urls, "the Vietnamese llms.txt section lists no URLs"

    for url in en_urls:
        assert "/vi/" not in url, f"English llms.txt section lists {url}"
        assert _file_for(built_site, url).is_file(), (
            f"llms.txt URL {url} should resolve to a built file"
        )
    for url in vi_urls:
        assert "/vi/" in url, f"Vietnamese llms.txt section lists {url}"
        assert _file_for(built_site, url).is_file(), (
            f"llms.txt URL {url} should resolve to a built file"
        )

    # Every published post must appear in its language's section.
    for path in _published_posts(REPO_ROOT / "_posts"):
        assert f"{SITE_URL}{_post_url(path)}" in en_urls
    for path in _published_posts(REPO_ROOT / "_vi_posts"):
        assert f"{SITE_URL}{_post_url(path)}" in vi_urls

    # Non-section site URLs (the `Canonical:` header) must resolve too;
    # owned here so every llms.txt URL has exactly one build guard (#297).
    content = llms_path.read_text(encoding="utf-8")
    canonical = re.search(r"^Canonical:\s*(https?://\S+)", content, re.M)
    assert canonical, "llms.txt must declare its `Canonical:` header URL"
    assert _file_for(built_site, canonical.group(1).rstrip(".,)")).is_file(), (
        f"llms.txt Canonical URL {canonical.group(1)} is not in the build"
    )


def test_feeds_split_by_language(built_site):
    """`/feed.xml` carries the English posts, `/vi/feed.xml` the Vietnamese
    ones — same Atom shape, no cross-language entries."""
    _, en_self, en_entries = _feed_entries(built_site / "feed.xml")
    assert en_self == f"{SITE_URL}/feed.xml", f"EN feed self link is {en_self}"
    assert en_entries, "the English feed lists no entries"
    for href in en_entries:
        assert href.startswith(SITE_URL), f"EN feed entry must be absolute: {href}"
        assert "/vi/" not in href, f"EN feed lists the Vietnamese post {href}"

    vi_root, vi_self, vi_entries = _feed_entries(built_site / "vi" / "feed.xml")
    assert vi_self == f"{SITE_URL}/vi/feed.xml", f"VI feed self link is {vi_self}"
    assert vi_root.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "vi") == "vi"
    vi_posts = _published_posts(REPO_ROOT / "_vi_posts")
    assert len(vi_entries) == len(vi_posts), (
        f"the VI feed lists {len(vi_entries)} entries "
        f"but there are {len(vi_posts)} Vietnamese posts"
    )
    for href in vi_entries:
        assert href.startswith(f"{SITE_URL}/vi/"), (
            f"VI feed entry must live under /vi/: {href}"
        )
        assert _file_for(built_site, href).is_file(), (
            f"VI feed entry {href} is not in the build"
        )


def _atom_feed_hrefs(html):
    """Hrefs of every `application/atom+xml` discovery link in the head."""
    return re.findall(
        r'<link type="application/atom\+xml" rel="alternate" href="([^"]+)"',
        html,
    )


def test_head_feed_link_matches_page_language(built_site):
    """English pages advertise `/feed.xml`, Vietnamese pages `/vi/feed.xml`."""
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    assert _atom_feed_hrefs(en_home) == [f"{SITE_URL}/feed.xml"], (
        "the English home must advertise only /feed.xml"
    )

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    assert _atom_feed_hrefs(vi_home) == [f"{SITE_URL}/vi/feed.xml"], (
        "the Vietnamese home must advertise only /vi/feed.xml"
    )

    en_post_href = re.search(r'class="post-link" href="([^"]+)"', en_home)
    assert en_post_href
    en_post = _file_for(built_site, en_post_href.group(1)).read_text(encoding="utf-8")
    assert _atom_feed_hrefs(en_post) == [f"{SITE_URL}/feed.xml"]

    vi_post_href = re.search(r'class="post-link" href="([^"]+)"', vi_home)
    assert vi_post_href
    vi_post = _file_for(built_site, vi_post_href.group(1)).read_text(encoding="utf-8")
    assert _atom_feed_hrefs(vi_post) == [f"{SITE_URL}/vi/feed.xml"]
