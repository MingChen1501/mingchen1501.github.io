"""Site-wide internal link crawl + sitemap/feed XML validation (#210).

E2E coverage never verified that internal links resolve or that the
sitemap/feed surface matches the built site, so broken links and stale
sitemap entries shipped silently. These guards close that gap using the
shared session ``built_site`` fixture (one ``jekyll build`` per session,
no live network, no browser):

- crawl: breadth-first walk from ``/`` and ``/vi/`` over every internal
  page link; every internal reference found on a visited page (anchors,
  stylesheets, scripts, images, feeds) must resolve to a file in the
  build, and the walk must reach every sitemap URL (so no indexed page
  is silently unreachable);
- orphans: any built HTML page the crawl never reaches must be either a
  ``jekyll-redirect-from`` stub whose target resolves, or a documented
  orphan below — nothing else may ship unlinked;
- XML: ``sitemap.xml``, ``feed.xml`` and ``vi/feed.xml`` must be
  well-formed with the expected roots/namespaces, and every sitemap loc
  and feed entry URL must resolve to a built file.

Out of scope (deliberately unchecked here):

- external links (any host other than ``mingchen.id.vn``, ``mailto:``,
  ``tel:``, ``data:``, …) — no network dependency by design;
- HTML validity and feed content semantics;
- the contents of the documented orphans: ``gift.html`` is a standalone
  hand-written page and ``fullmonth/`` a standalone event invitation,
  both intentionally unlinked (shared directly, never navigated to).
  Note: ``fullmonth/index.html`` references two stylesheets
  (``css/ekko-lightbox.css``, ``styles/main.css``) that are absent from
  the build — dead links on an unlinked legacy page, left alone here.
"""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SITE_URL = "https://mingchen.id.vn"
SITE_HOST = "mingchen.id.vn"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ATOM_NS = "http://www.w3.org/2005/Atom"

# Crawl entry points: the English and Vietnamese homepages (#210).
CRAWL_SEEDS = ("/", "/vi/")

# Built HTML pages the crawl legitimately never reaches, with reasons.
# Anything else unvisited fails `test_unlinked_pages_are_documented`.
DOCUMENTED_ORPHANS = {
    # GitHub Pages serves this for missing URLs; it is never linked to.
    "404.html": "error page served by the host, never linked",
    # Standalone hand-written page shared directly, never navigated to.
    "gift.html": "standalone unlinked page, contents out of scope",
    # Standalone event invitation shared directly, never navigated to.
    "fullmonth/index.html": "standalone unlinked page, contents out of scope",
}

# Schemes that are never internal links (external by design, #210).
_EXTERNAL_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "sms:", "skype:")


def _file_for(site_dir, url_path):
    """Map a site path onto the file that serves it (GitHub Pages rules).

    Exact files serve as-is; anything else must be a directory carrying
    an ``index.html``. There is deliberately no ``.html`` guessing: an
    extension-less link to a non-directory is a 404, not a match.
    """
    if url_path in ("", "/"):
        return site_dir / "index.html"
    clean = url_path.lstrip("/")
    if clean.endswith("/"):
        return site_dir / clean / "index.html"
    candidate = site_dir / clean
    if candidate.is_dir():
        return candidate / "index.html"
    return candidate


class _RefCollector(HTMLParser):
    """Collect navigable/resource references from one HTML page."""

    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.refs.append(values["href"])
        elif tag == "link" and values.get("href"):
            self.refs.append(values["href"])
        elif tag in ("img", "script", "source", "video", "audio", "track", "embed") and values.get("src"):
            self.refs.append(values["src"])
        elif tag == "form" and values.get("action"):
            self.refs.append(values["action"])
        elif tag in ("img", "source") and values.get("srcset"):
            for item in values["srcset"].split(","):
                url = item.strip().split(" ")[0]
                if url:
                    self.refs.append(url)


def _internal_path(ref, page_url):
    """Return the site path for an internal reference, or ``None``.

    ``None`` means out of scope for the crawl: fragments, queries on the
    current page, non-HTTP schemes, and every external URL (#210 keeps
    external links unchecked so the suite needs no network).
    """
    ref = ref.strip()
    if not ref or ref.startswith(("#", "?")):
        return None
    if ref.lower().startswith(_EXTERNAL_SCHEMES):
        return None
    if ref.startswith("//"):
        parsed = urlparse("https:" + ref)
        if parsed.hostname != SITE_HOST:
            return None
        ref = parsed.path or "/"
    elif "://" in ref:
        parsed = urlparse(ref)
        if parsed.scheme not in ("http", "https") or parsed.hostname != SITE_HOST:
            return None
        ref = parsed.path or "/"
    if not ref.startswith("/"):
        base = page_url if page_url.endswith("/") else page_url.rsplit("/", 1)[0] + "/"
        ref = posixpath.normpath(posixpath.join(base, ref))
        if ref == ".":
            return None
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if ref in ("", "/."):
        return None
    if not ref.startswith("/"):
        ref = "/" + ref
    return ref


def _crawl(built_site):
    """Walk internal page links from the seeds; return ``(visited, broken)``.

    ``visited`` maps each reached site path to its built file; ``broken``
    lists ``(page, ref, target)`` triples for internal references with no
    file in the build. Asset references (images, stylesheets, scripts)
    are checked but never followed; only HTML pages extend the walk.
    """
    visited = {}
    broken = []
    queue = list(CRAWL_SEEDS)
    while queue:
        page_url = queue.pop(0)
        if page_url in visited:
            continue
        target = _file_for(built_site, page_url)
        if not target.is_file():
            broken.append(("<crawl-seed>", page_url, page_url))
            visited[page_url] = None
            continue
        visited[page_url] = target
        if target.suffix != ".html":
            continue
        collector = _RefCollector()
        collector.feed(target.read_text(encoding="utf-8"))
        for ref in collector.refs:
            site_path = _internal_path(ref, page_url)
            if site_path is None:
                continue
            resolved = _file_for(built_site, site_path)
            if not resolved.is_file():
                broken.append((page_url, ref, site_path))
            elif resolved.suffix == ".html" and site_path not in visited:
                queue.append(site_path)
    return visited, broken


def _sitemap_locs(built_site):
    """Parse ``sitemap.xml``; return the ``<loc>`` URL list."""
    sitemap_path = built_site / "sitemap.xml"
    assert sitemap_path.is_file(), "sitemap.xml must exist in the build"
    try:
        root = ET.fromstring(sitemap_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        raise AssertionError("sitemap.xml does not parse as valid XML")
    assert root.tag == f"{{{SITEMAP_NS}}}urlset", (
        f"sitemap.xml root must be the sitemap urlset, got {root.tag}"
    )
    urls = root.findall(f"{{{SITEMAP_NS}}}url")
    assert urls, "sitemap.xml must contain at least one <url>"
    locs = []
    for url in urls:
        loc = url.find(f"{{{SITEMAP_NS}}}loc")
        assert loc is not None and (loc.text or "").strip(), (
            "every sitemap <url> needs a <loc>"
        )
        assert (url.find(f"{{{SITEMAP_NS}}}lastmod") is not None), (
            f"sitemap entry {loc.text} has no <lastmod>"
        )
        locs.append(loc.text.strip())
    return locs


def _feed_entries(feed_path):
    """Parse an Atom feed; return ``(self_href, [entry_hrefs])``."""
    assert feed_path.is_file(), f"{feed_path.name} must exist in the build"
    try:
        root = ET.fromstring(feed_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        raise AssertionError(f"{feed_path.name} does not parse as valid XML")
    assert root.tag == f"{{{ATOM_NS}}}feed", (
        f"{feed_path.name} root must be an Atom feed, got {root.tag}"
    )
    for child in ("title", "id", "updated"):
        element = root.find(f"{{{ATOM_NS}}}{child}")
        assert element is not None and (element.text or "").strip(), (
            f"{feed_path.name} feed needs a <{child}>"
        )
    self_links = [
        link.attrib.get("href")
        for link in root.findall(f"{{{ATOM_NS}}}link")
        if link.attrib.get("rel") == "self"
    ]
    assert len(self_links) == 1, (
        f"{feed_path.name} must carry exactly one self link, got {self_links}"
    )
    entries = root.findall(f"{{{ATOM_NS}}}entry")
    assert entries, f"{feed_path.name} must contain at least one <entry>"
    hrefs = []
    for entry in entries:
        link = entry.find(f"{{{ATOM_NS}}}link")
        assert link is not None and link.attrib.get("href"), (
            f"an entry in {feed_path.name} has no link href"
        )
        for child in ("title", "id", "updated"):
            element = entry.find(f"{{{ATOM_NS}}}{child}")
            assert element is not None and (element.text or "").strip(), (
                f"an entry in {feed_path.name} has no <{child}>"
            )
        hrefs.append(link.attrib["href"])
    return self_links[0], hrefs


def _page_path_for_loc(built_site, loc):
    """Map a sitemap/feed absolute URL onto its crawled site path."""
    assert loc.startswith(SITE_URL + "/") or loc == SITE_URL, (
        f"sitemap/feed URL must be on {SITE_URL}: {loc}"
    )
    return "/" + loc[len(SITE_URL):].lstrip("/")


# --- crawl guards -----------------------------------------------------------


def test_internal_link_crawl_has_no_404s(built_site):
    """Every internal link/asset reachable from ``/`` or ``/vi/`` resolves."""
    visited, broken = _crawl(built_site)
    assert not broken, (
        "internal references with no file in the build:\n"
        + "\n".join(f"{page}: {ref} -> {target}" for page, ref, target in broken)
    )
    # The walk must be real: both language homes plus paginated/tag/post pages.
    assert len(visited) > 20, (
        f"the crawl visited only {len(visited)} pages — it measured almost nothing"
    )


def test_crawl_reaches_every_sitemap_url(built_site):
    """No sitemap URL is silently unreachable from the crawl seeds."""
    visited, _ = _crawl(built_site)
    missing = [
        _page_path_for_loc(built_site, loc)
        for loc in _sitemap_locs(built_site)
        if _page_path_for_loc(built_site, loc) not in visited
    ]
    assert not missing, (
        "sitemap URLs the crawl from / and /vi/ never reaches:\n" + "\n".join(missing)
    )


def test_unlinked_pages_are_documented_or_redirects(built_site):
    """Built HTML outside the crawl is a resolving redirect or documented."""
    visited, _ = _crawl(built_site)
    visited_files = {path.relative_to(built_site).as_posix() for path in visited.values() if path}
    offenders = []
    for page in sorted(built_site.rglob("*.html")):
        name = page.relative_to(built_site).as_posix()
        if name in visited_files:
            continue
        if name in DOCUMENTED_ORPHANS:
            continue
        html = page.read_text(encoding="utf-8")
        refresh = re.search(
            r'<meta http-equiv="refresh" content="0; url=([^"]+)"', html
        )
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if refresh and canonical and refresh.group(1) == canonical.group(1):
            site_path = _internal_path(canonical.group(1), "/")
            assert site_path is not None, f"{name} redirects off-site: {canonical.group(1)}"
            assert _file_for(built_site, site_path).is_file(), (
                f"{name} redirects to {site_path}, which is not in the build"
            )
            continue
        offenders.append(name)
    assert not offenders, (
        "built pages neither reached by the crawl, redirecting, nor documented in "
        "DOCUMENTED_ORPHANS:\n" + "\n".join(offenders)
    )


# --- XML guards -------------------------------------------------------------


def test_sitemap_urls_are_unique_and_resolve(built_site):
    """Sitemap structure holds and every loc exists in the build."""
    locs = _sitemap_locs(built_site)
    assert len(locs) == len(set(locs)), (
        "sitemap.xml lists duplicates: "
        + ", ".join(sorted(loc for loc in set(locs) if locs.count(loc) > 1))
    )
    assert f"{SITE_URL}/" in locs, "the sitemap must list the English homepage"
    assert f"{SITE_URL}/vi/" in locs, "the sitemap must list the Vietnamese homepage"
    missing = [
        loc
        for loc in locs
        if not _file_for(built_site, _page_path_for_loc(built_site, loc)).is_file()
    ]
    assert not missing, (
        "sitemap URLs with no file in the build:\n" + "\n".join(missing)
    )


def test_feeds_are_valid_atom_and_entries_resolve(built_site):
    """Both feeds are well-formed Atom and every entry resolves."""
    en_self, en_entries = _feed_entries(built_site / "feed.xml")
    assert en_self == f"{SITE_URL}/feed.xml", f"EN feed self link is {en_self}"
    vi_self, vi_entries = _feed_entries(built_site / "vi" / "feed.xml")
    assert vi_self == f"{SITE_URL}/vi/feed.xml", f"VI feed self link is {vi_self}"

    for href in en_entries:
        assert "/vi/" not in href, f"EN feed lists the Vietnamese post {href}"
    for href in vi_entries:
        assert href.startswith(f"{SITE_URL}/vi/"), (
            f"VI feed entry must live under /vi/: {href}"
        )
    missing = [
        href
        for href in en_entries + vi_entries
        if not _file_for(built_site, _page_path_for_loc(built_site, href)).is_file()
    ]
    assert not missing, (
        "feed entries with no file in the build:\n" + "\n".join(missing)
    )
