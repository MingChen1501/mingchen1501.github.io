"""Guards for #343: posts may carry more than one pillar tag.

Covered here:

- (static) the post layout builds Related posts as the union of same-language
  posts sharing ANY of the page's tags — newest first across the union
  (same-date ties broken by URL), de-duplicated, current page excluded,
  capped at five — and keys the Latest-posts fallback off that union;
- (static) the list sidebar's tag groups and the tag pages filter by tag
  membership, so a two-tag post appears under both groups without row
  duplication, and the chip list wraps (two chips + counts fit at 320px);
- (overlay build) a throwaway copy of the repo plus synthetic two-tag posts
  (EN + VI) proves the union behaviour in real built HTML: the main fixture
  lists siblings from BOTH tags, newest first, with no duplicates and without
  itself — while the pre-existing singleton-fallback guards in
  `test_related_posts_fallback.py` keep pinning the no-sibling pillar case.

The overlay build is deliberate: no published multi-tag post exists yet, and
adding a fixture post to the real tree would leak into every other guard
(counts, feeds, pagination). The overlay copies the working tree (never
`_site`/`.git`), adds the fixtures, and builds into its own destination, so
the session's shared `built_site` stays untouched.
"""

import contextlib
import functools
import os
import re
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
POST_TAGS_INCLUDE = REPO_ROOT / "_includes" / "post-tags.html"

EN_MAIN_URL = "/2026/10/20/multi-tag-fixture-main.html"
EN_ALPHA_URL = "/2026/10/18/multi-tag-fixture-alpha.html"
EN_BETA_URL = "/2026/10/19/multi-tag-fixture-beta.html"

VI_MAIN_URL = "/vi/2026/10/20/multi-tag-fixture-chinh.html"
VI_SIB_A_URL = "/vi/2026/10/18/multi-tag-fixture-sib-a.html"
VI_SIB_B_URL = "/vi/2026/10/19/multi-tag-fixture-sib-b.html"

EN_FIXTURES = {
    # Stem -> (tags, body title). Dates come from the file-name prefix.
    # Alpha deliberately carries BOTH tags: it enters the raw union twice,
    # so the built-HTML no-duplicate assertion below is meaningful.
    "2026-10-18-multi-tag-fixture-alpha": (
        ["ai-agent", "linux-tooling"],
        "Multi-tag fixture alpha",
    ),
    "2026-10-19-multi-tag-fixture-beta": (["linux-tooling"], "Multi-tag fixture beta"),
    "2026-10-20-multi-tag-fixture-main": (
        ["ai-agent", "linux-tooling"],
        "Multi-tag fixture main",
    ),
}

VI_FIXTURES = {
    # Stem -> (date, tags, title). VI URLs embed the front-matter date.
    "multi-tag-fixture-sib-a": ("2026-10-18", ["ai-agent"], "Fixture sib A"),
    "multi-tag-fixture-sib-b": ("2026-10-19", ["linux-tooling"], "Fixture sib B"),
    "multi-tag-fixture-chinh": (
        "2026-10-20",
        ["ai-agent", "linux-tooling"],
        "Fixture chinh",
    ),
}


def _read(path):
    return Path(path).read_text(encoding="utf-8")


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


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_layout_unions_every_tag_in_the_pages_language():
    text = _read(POST_LAYOUT)
    # One pass per tag of the page, concatenated into a single union —
    # English from `site.tags`, Vietnamese from a nil-safe `site.vi_posts`
    # membership filter on the loop variable (never the first tag alone).
    assert "for rel_tag in post_tags" in text
    assert "site.tags[rel_tag]" in text
    assert '"rel_post.tags contains rel_tag"' in text
    assert "rel_union" in text and "concat" in text
    # Ordering rule (#343): newest first across the union; the URL pre-sort
    # breaks same-date ties deterministically before the date sort.
    assert 'sort: "url"' in text
    assert 'sort: "date"' in text
    assert "reverse" in text
    # A post carrying two of the page's tags renders once (first/newest
    # occurrence wins the seen-set); the current page is still excluded and
    # the list still caps at five.
    assert "push: rel_post" in text
    assert "rel_seen" in text
    assert "other.url != page.url" in text
    assert "shown < 5" in text


@pytest.mark.static
def test_layout_fallback_keys_off_the_union():
    text = _read(POST_LAYOUT)
    # No siblings under ANY tag -> Latest posts; the size check reads the
    # de-duplicated union, and the fallback still honours #328 (nothing newer
    # than the page) with the honest heading in both languages.
    assert "tag_posts.size <= 1" in text
    assert "use_latest" in text
    assert "latest_post" in text and "<= page.date" in text
    assert "Latest posts" in text
    assert "Bài viết mới nhất" in text


@pytest.mark.static
def test_sidebar_tag_groups_key_off_membership():
    text = _read(SIDEBAR_INCLUDE)
    # Every tag group lists the posts carrying that tag (EN via the tag
    # index, VI via a membership filter), so a two-tag post shows up under
    # both of its groups; the inner loop walks posts (capped at three), so
    # it can never repeat a row inside one group.
    assert "site.tags[sidebar_tag_name]" in text
    assert '"sidebar_tag_post.tags contains sidebar_tag_name"' in text
    assert "for sidebar_tag_post in sidebar_tag_posts limit: 3" in text


@pytest.mark.static
def test_tag_pages_key_off_membership():
    text = _read(TAG_LAYOUT)
    # EN tag pages read Jekyll's per-tag index (a multi-tag post is indexed
    # under every tag it carries); VI pages filter by membership.
    assert "site.tags[tag_name]" in text
    assert '"tag_post.tags contains tag_name"' in text


@pytest.mark.static
def test_chip_list_wraps_two_chips_plus_counts():
    # Both chips render from the shared include (one `<li>` per tag) inside
    # a flex container that wraps, so two chips plus counts fit at 320px
    # without overflow; the browser guard below proves it on built HTML.
    assert "for tag in chips" in _read(POST_TAGS_INCLUDE)
    assert re.search(
        r"ul\.tag-chip-list\s*\{[^}]*flex-wrap:\s*wrap;", conftest.custom_styles_text(), re.S
    )


# --- overlay build (throwaway copy + synthetic two-tag posts) ----------------


def _write_en_fixture(posts_dir, stem, tags, title):
    ref = stem[11:]  # strip the YYYY-MM-DD- prefix
    (posts_dir / f"{stem}.md").write_text(
        "---\n"
        "layout: post\n"
        "lang: en\n"
        f"ref: {ref}\n"
        "author: Ming Chen\n"
        f'title: "{title}"\n'
        f"tags: [{', '.join(tags)}]\n"
        'description: "Synthetic #343 fixture post proving multi-tag union behaviour in an isolated overlay build."\n'
        "---\n\n"
        "Fixture body.\n",
        encoding="utf-8",
    )


def _write_vi_fixture(posts_dir, stem, date, tags, title):
    (posts_dir / f"{stem}.md").write_text(
        "---\n"
        "layout: post\n"
        "lang: vi\n"
        f"ref: {stem}\n"
        f"date: {date}\n"
        "author: Ming Chen\n"
        f'title: "{title}"\n'
        f"tags: [{', '.join(tags)}]\n"
        'description: "Bai fixture tong hop cho #343: bai viet hai tag trong build overlay tach biet."\n'
        "---\n\n"
        "Noi dung fixture.\n",
        encoding="utf-8",
    )


def _post_tag_catalog(posts_dir, pattern, date_re):
    """Post URL -> set of tags, from fixture + real post sources."""
    catalog = {}
    for path in sorted(posts_dir.glob(pattern)):
        front_matter = path.read_text(encoding="utf-8")
        if re.search(r"^published:\s*false", front_matter, re.M):
            continue
        match = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
        tags = (
            [t.strip().strip("'\"") for t in match.group(1).split(",") if t.strip()]
            if match
            else []
        )
        date_match = date_re(path, front_matter)
        if date_match is None:
            continue
        catalog[date_match] = set(tags)
    return catalog


@pytest.fixture(scope="module")
def overlay_site(tmp_path_factory):
    """Build an isolated copy of the repo plus synthetic two-tag posts."""
    bundle = shutil.which("bundle")
    if bundle is None:
        pytest.skip("`bundle` not found: the overlay build needs Ruby + Jekyll")
    overlay = tmp_path_factory.getbasetemp() / "multi-tag-overlay"
    shutil.copytree(
        REPO_ROOT,
        overlay,
        ignore=shutil.ignore_patterns(".git", "_site", ".jekyll-cache"),
    )
    for stem, (tags, title) in EN_FIXTURES.items():
        _write_en_fixture(overlay / "_posts", stem, tags, title)
    for stem, (date, tags, title) in VI_FIXTURES.items():
        _write_vi_fixture(overlay / "_vi_posts", stem, date, tags, title)
    destination = tmp_path_factory.mktemp("multi-tag-overlay-build")
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
    return overlay, destination


@pytest.fixture(scope="module")
def overlay_catalogs(overlay_site):
    overlay, _ = overlay_site
    en = _post_tag_catalog(
        overlay / "_posts",
        "*.md",
        lambda path, _fm: re.match(
            r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", path.name
        )
        and f"/{path.name[0:4]}/{path.name[5:7]}/{path.name[8:10]}/{path.name[11:-3]}.html",
    )
    vi = _post_tag_catalog(
        overlay / "_vi_posts",
        "*.md",
        lambda path, fm: (
            (m := re.search(r"^date:\s*(\d{4})-(\d{2})-(\d{2})", fm, re.M))
            and f"/vi/{m.group(1)}/{m.group(2)}/{m.group(3)}/{path.stem}.html"
        )
        or None,
    )
    return en, vi


def _assert_union_section(html, main_url, main_tags, catalog, heading):
    sections = _sidebar_sections(html)
    assert len(sections) == 1, f"{main_url}: want exactly one section"
    section_heading, links = sections[0]
    # A union with siblings keeps the true Related heading (no fallback).
    assert section_heading == heading, f"{main_url}: {section_heading!r}"
    assert 1 <= len(links) <= 5, f"{main_url}: {len(links)} links"
    # The current page never lists itself, and never twice.
    assert main_url not in links, f"{main_url}: lists itself"
    assert len(links) == len(set(links)), f"{main_url}: duplicate links {links}"
    # Every link shares at least one tag with the page: the union proof.
    for link in links:
        assert link in catalog, f"{main_url}: links to unknown post {link}"
        assert catalog[link] & main_tags, (
            f"{main_url}: {link} shares no tag with {sorted(main_tags)}"
        )
    return links


def test_en_multi_tag_post_unions_both_tags(overlay_site, overlay_catalogs):
    _, destination = overlay_site
    en_catalog, _ = overlay_catalogs
    html = _read(destination / EN_MAIN_URL.lstrip("/"))
    links = _assert_union_section(
        html, EN_MAIN_URL, {"ai-agent", "linux-tooling"}, en_catalog, "Related posts"
    )
    # Siblings from EACH tag appear: alpha via ai-agent, beta via linux-tooling.
    assert EN_ALPHA_URL in links, f"missing ai-agent sibling: {links}"
    assert EN_BETA_URL in links, f"missing linux-tooling sibling: {links}"
    # Newest first across the union: beta (10-19) outranks alpha (10-18).
    assert links.index(EN_BETA_URL) < links.index(EN_ALPHA_URL), links


def test_vi_multi_tag_post_unions_both_tags(overlay_site, overlay_catalogs):
    _, destination = overlay_site
    _, vi_catalog = overlay_catalogs
    html = _read(destination / VI_MAIN_URL.lstrip("/"))
    links = _assert_union_section(
        html,
        VI_MAIN_URL,
        {"ai-agent", "linux-tooling"},
        vi_catalog,
        "Bài viết cùng chủ đề",
    )
    assert VI_SIB_A_URL in links, f"missing ai-agent sibling: {links}"
    assert VI_SIB_B_URL in links, f"missing linux-tooling sibling: {links}"
    assert links.index(VI_SIB_B_URL) < links.index(VI_SIB_A_URL), links


def test_multi_tag_post_appears_on_both_tag_pages(overlay_site):
    _, destination = overlay_site
    for tag_page, main_url in (
        ("tags/ai-agent/index.html", EN_MAIN_URL),
        ("tags/linux-tooling/index.html", EN_MAIN_URL),
        ("vi/tags/ai-agent/index.html", VI_MAIN_URL),
        ("vi/tags/linux-tooling/index.html", VI_MAIN_URL),
    ):
        html = _read(destination / tag_page)
        assert f'href="{main_url}"' in html, (
            f"{tag_page} does not list the two-tag post {main_url}"
        )


def test_multi_tag_post_renders_two_chips(overlay_site):
    _, destination = overlay_site
    for main_url, chips in (
        (EN_MAIN_URL, ("ai-agent", "linux-tooling")),
        (VI_MAIN_URL, ("ai-agent", "linux-tooling")),
    ):
        html = _read(destination / main_url.lstrip("/"))
        aside = re.search(
            r'<aside class="post-sidebar".*?</aside>', html, re.S
        ).group(0)
        rendered = re.findall(r'<a class="tag-chip"[^>]*>(.*?)</a>', aside)
        assert len(rendered) == len(chips), (
            f"{main_url}: want {len(chips)} chips, got {rendered}"
        )


@contextlib.contextmanager
def _served(directory):
    handler = functools.partial(
        SimpleHTTPRequestHandler, directory=str(directory)
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_two_chips_fit_at_320px(overlay_site, browser):
    """Two sidebar chips plus counts fit at 320px with no page overflow."""
    from urllib.parse import urlparse

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    _, destination = overlay_site
    with _served(destination) as base_url:
        context = browser.new_context(
            viewport={"width": 320, "height": 800}, device_scale_factor=1
        )
        pg = context.new_page()
        try:
            pg.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost")
                    else route.abort()
                ),
            )
            for main_url in (EN_MAIN_URL, VI_MAIN_URL):
                pg.goto(base_url + main_url)
                try:
                    pg.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError:
                    pass
                metrics = pg.evaluate(
                    """() => {
                      const vw = window.innerWidth;
                      const chips = [];
                      for (const el of document.querySelectorAll('.post-sidebar a.tag-chip')) {
                        const r = el.getBoundingClientRect();
                        chips.push({left: r.left, right: r.right});
                      }
                      return {
                        scrollWidth: document.documentElement.scrollWidth,
                        innerWidth: vw,
                        chips: chips,
                      };
                    }"""
                )
                # The overlay fixtures carry no images, so no allowance: the
                # page itself must fit, and every sidebar chip must sit inside
                # the viewport.
                assert metrics["scrollWidth"] <= metrics["innerWidth"], (
                    f"{main_url}: page overflows at 320px "
                    f"(scrollWidth {metrics['scrollWidth']} > {metrics['innerWidth']})"
                )
                assert len(metrics["chips"]) == 2, (
                    f"{main_url}: want 2 sidebar chips, got {metrics['chips']}"
                )
                for chip in metrics["chips"]:
                    assert 0 <= chip["left"] and chip["right"] <= metrics["innerWidth"], (
                        f"{main_url}: chip overflows at 320px: {chip}"
                    )
        finally:
            context.close()
