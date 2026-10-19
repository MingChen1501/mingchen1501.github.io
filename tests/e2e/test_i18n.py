"""Bilingual guards, phase 2 — full translations (#97, PR B).

English default at `/` (`_posts/`), Vietnamese under `/vi/` (the `site.vi_posts`
collection plus `vi/*.md` pages). The two sides are linked by a shared `ref`.

Phase 1 (PR A) shipped the structure with English *stubs*: an English post/page
whose translation was still pending carried `fallback_vi: true` and temporarily
reused the Vietnamese body under a banner
(`_includes/vi-fallback-notice.html`). Phase 2 replaces every stub with a real
translation, so no content source may carry `fallback_vi: true` anymore and no
built page may render the banner. The layout/include plumbing stays wired (it
degrades to nothing without the flag) for any future untranslated post; PR C
adds the SEO surface (sitemap alternates, bilingual `llms.txt`, `/vi/feed.xml`).
There is no `translation_pending` marker — every English side is translated,
never a silent gap.

Static guards (no Ruby) cover the source contract; build guards (need Ruby, no
browser) cover the emitted site.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POSTS_DIR = REPO_ROOT / "_posts"
VI_POSTS_DIR = REPO_ROOT / "_vi_posts"
TAGS_DIR = REPO_ROOT / "tags"
VI_TAGS_DIR = REPO_ROOT / "vi" / "tags"
SITE_URL = "https://mingchen.id.vn"

PILLARS = ["backend-production", "ai-agent", "linux-tooling", "doi-song"]

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
NOTICE_INCLUDE = "{% include vi-fallback-notice.html %}"

# Old Vietnamese URLs (on `origin/master` when #93 was filed). Every one of
# them must keep resolving — via a redirect stub to `/vi/...` (#93) — except
# the language-neutral `/portfolio/`, `/tags/` and `/tags/<tag>/` paths, which
# the default language takes over (they were already English or
# language-neutral, so nothing is lost; the switcher leads to `/vi/`).
EXPECTED_REDIRECTS = {
    "/2022/10/27/cach-pha-ca-phe.html": "/vi/2022/10/27/cach-pha-ca-phe.html",
    "/2022/12/25/gioi-thieu-ve-internet.html": "/vi/2022/12/25/gioi-thieu-ve-internet.html",
    "/2023/01/31/tet-nguyen-dan-quy-mao-2023-cua-toi.html": "/vi/2023/01/31/tet-nguyen-dan-quy-mao-2023-cua-toi.html",
    "/2026/01/01/migrate-windows-11-to-fedora.html": "/vi/2026/01/01/migrate-windows-11-to-fedora.html",
    "/2026/01/01/migate-windows-11-to-fedora.html": "/vi/2026/01/01/migrate-windows-11-to-fedora.html",
    "/2026/10/14/setup-ai-coding-agent-orchestration.html": "/vi/2026/10/14/setup-ai-coding-agent-orchestration.html",
    "/2026/10/17/agent-orchestration-opencode-free.html": "/vi/2026/10/17/agent-orchestration-opencode-free.html",
    "/about-me/": "/vi/about/",
}

VI_ONLY_MARKERS = [
    "Bài nổi bật",
    "Bài mới nhất",
    "Bài viết cùng chủ đề",
    "Tất cả chủ đề",
    "Xem tất cả",
    "bài viết với tag",
]

EN_ONLY_MARKERS = [
    "Featured",
    "Related posts",
    "All topics",
    "View all",
    "Latest posts",
    "posts tagged with",
]


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _body(path):
    text = _read(path)
    match = FRONT_MATTER_RE.match(text)
    return text[match.end():] if match else text


def _value(block, key):
    match = re.search(rf"^{key}:[ \t]*(.+?)[ \t]*$", block, re.M)
    if not match:
        return None
    value = match.group(1)
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _tags(block):
    inline = re.search(r"^tags:\s*\[(.*?)\]", block, re.M)
    if inline:
        return [t.strip().strip("'\"") for t in inline.group(1).split(",") if t.strip()]
    return []


def _redirects(block):
    """All `redirect_from` entries of a front-matter block."""
    lines = block.splitlines()
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        inline = re.match(r"^redirect_from:\s*(\S.*)$", line)
        if inline and not inline.group(1).startswith("["):
            entries.append(inline.group(1).strip().strip("'\""))
        elif re.match(r"^redirect_from:\s*$", line):
            i += 1
            while i < len(lines):
                item = re.match(r"^[ \t]*-[ \t]*(.+?)[ \t]*$", lines[i])
                if not item:
                    break
                entries.append(item.group(1).strip().strip("'\""))
                i += 1
            continue
        i += 1
    return entries


def _content_sources():
    """`(directory, fixed lang or None)` of every content source with refs."""
    return [
        (POSTS_DIR, "en"),
        (VI_POSTS_DIR, "vi"),
        (REPO_ROOT, None),  # about.md, portfolio.md, tags.md
        (REPO_ROOT / "vi", None),  # vi/about.md, vi/tags.md
        (TAGS_DIR, None),
        (VI_TAGS_DIR, None),
    ]


def _iter_content_docs():
    """`(path, front matter, lang)` of every non-feed content doc with a ref."""
    for directory, fixed_lang in _content_sources():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            front_matter = _front_matter(path)
            if _value(front_matter, "published") == "false":
                continue
            if _value(front_matter, "ref") is None:
                continue
            lang = fixed_lang or _value(front_matter, "lang") or "en"
            yield path, front_matter, lang


def _ref_pairs():
    """`ref` -> `{"en": [rel paths], "vi": [rel paths]}` over content docs."""
    pairs = {}
    for path, _, lang in _iter_content_docs():
        ref = _value(_front_matter(path), "ref")
        pairs.setdefault(ref, {"en": [], "vi": []})
        pairs[ref][lang].append(str(path.relative_to(REPO_ROOT)))
    # The two home pages share `ref: home` but are `.html`, not `.md`.
    for path, lang in ((REPO_ROOT / "index.html", "en"),
                       (REPO_ROOT / "vi" / "index.html", "vi")):
        if path.is_file():
            ref = _value(_front_matter(path), "ref")
            if ref:
                pairs.setdefault(ref, {"en": [], "vi": []})
                pairs[ref][lang].append(str(path.relative_to(REPO_ROOT)))
    return pairs


def _file_for(site_dir, url):
    """Map a site URL onto the file that serves it inside the built site."""
    if url.startswith(SITE_URL):
        path = url[len(SITE_URL):]
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


def _built_for_source(built_site, path):
    """Built file for a source page/post, or None when it has no page URL."""
    front_matter = _front_matter(path)
    permalink = _value(front_matter, "permalink")
    if permalink:
        if "/feed.xml" in permalink:
            return None
        return _file_for(built_site, permalink)
    name = path.name
    if path.parent == POSTS_DIR:
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        return _file_for(built_site, f"/{path.stem[:10].replace('-', '/')}/{slug}.html")
    if path.parent == VI_POSTS_DIR:
        date = _value(front_matter, "date") or ""
        slug = path.stem
        return _file_for(built_site, f"/vi/{date.replace('-', '/')}/{slug}.html")
    if name == "index.html" and path.parent == REPO_ROOT:
        return built_site / "index.html"
    if name == "index.html" and path.parent == REPO_ROOT / "vi":
        return built_site / "vi" / "index.html"
    return None


def _normalized_body(path):
    """Doc body without the fallback notice line, for EN/VI comparison."""
    return _body(path).replace(NOTICE_INCLUDE, "").strip()


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_every_published_post_declares_lang_ref_and_pillar_tags():
    for posts_dir, lang in ((POSTS_DIR, "en"), (VI_POSTS_DIR, "vi")):
        assert posts_dir.is_dir(), f"{posts_dir} is missing"
        docs = [
            (p, _front_matter(p))
            for p in sorted(posts_dir.glob("*.md"))
            if _value(_front_matter(p), "published") != "false"
        ]
        assert docs, f"no published posts in {posts_dir}"
        for path, front_matter in docs:
            assert _value(front_matter, "lang") == lang, (
                f"{path.name} must declare `lang: {lang}`"
            )
            assert _value(front_matter, "ref"), (
                f"{path.name} must declare a `ref:` shared with its translation"
            )
            tags = _tags(front_matter)
            assert tags, f"{path.name} must declare tags"
            assert set(tags) <= set(PILLARS), (
                f"{path.name} uses tags outside the pillars: {tags}"
            )
            assert _value(front_matter, "description"), (
                f"{path.name} must declare a translated `description`"
            )
            if posts_dir == VI_POSTS_DIR:
                assert _value(front_matter, "date"), (
                    f"{path.name} needs `date:` for the collection permalink"
                )


@pytest.mark.static
def test_no_translation_pending_marker_exists():
    """The owner dropped `translation_pending`: every English side ships a real
    translation (PR B) — never a silent gap."""
    offenders = []
    for directory, _, in _content_sources():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if "translation_pending" in _front_matter(path):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        "`translation_pending` is retired — every English side ships a real "
        "translation: " + ", ".join(offenders)
    )


@pytest.mark.static
def test_no_fallback_vi_stubs_remain():
    """Phase 2 ships real translations: no content source may carry
    `fallback_vi: true` anymore (posts or pages, either language)."""
    offenders = []
    for directory, _ in _content_sources():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if _value(_front_matter(path), "fallback_vi") == "true":
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        "`fallback_vi` stubs are retired — translate the English side "
        "instead: " + ", ".join(offenders)
    )


@pytest.mark.static
def test_every_post_ref_has_vietnamese_and_real_english_translation():
    """Phase 2 pairing rule: every post ref resolves to Vietnamese and to a
    real English translation — flagged stubs are gone, and an English body
    identical to the Vietnamese one fails."""
    en_refs = {}
    vi_refs = {}
    for path in sorted(POSTS_DIR.glob("*.md")):
        front_matter = _front_matter(path)
        if _value(front_matter, "published") == "false":
            continue
        assert _value(front_matter, "fallback_vi") != "true", (
            f"{path.name} still carries `fallback_vi: true` — ship the real "
            "translation (PR B)"
        )
        en_refs[_value(front_matter, "ref")] = (path, front_matter)
    for path in sorted(VI_POSTS_DIR.glob("*.md")):
        front_matter = _front_matter(path)
        if _value(front_matter, "published") == "false":
            continue
        vi_refs[_value(front_matter, "ref")] = (path, front_matter)
    assert en_refs and vi_refs, "both post sources must be populated"
    for ref in sorted(set(en_refs) | set(vi_refs)):
        assert ref in vi_refs, f"ref `{ref}` has no Vietnamese side"
        assert ref in en_refs, f"ref `{ref}` has no English file (1 post = 2 files)"
        en_path, en_fm = en_refs[ref]
        vi_path, _ = vi_refs[ref]
        assert _normalized_body(en_path) != _normalized_body(vi_path), (
            f"{en_path.name} reuses the Vietnamese body without a real "
            "translation — translate it (PR B)"
        )


@pytest.mark.static
def test_refs_are_unique_within_each_language():
    seen = {"en": {}, "vi": {}}
    for ref, sides in _ref_pairs().items():
        for lang in ("en", "vi"):
            for name in sides[lang]:
                assert ref not in seen[lang], (
                    f"duplicate ref `{ref}` in {lang}: "
                    f"{seen[lang][ref]} and {name}"
                )
                seen[lang][ref] = name


@pytest.mark.static
def test_old_vietnamese_urls_keep_a_redirect():
    """Every historical URL must survive via `redirect_from` (#93)."""
    covered = set()
    for posts_dir in (POSTS_DIR, VI_POSTS_DIR):
        for path in sorted(posts_dir.glob("*.md")):
            covered.update(_redirects(_front_matter(path)))
    for page in ["about.md", "portfolio.md", "tags.md"]:
        for base in (REPO_ROOT, REPO_ROOT / "vi"):
            candidate = base / page
            if candidate.is_file():
                covered.update(_redirects(_front_matter(candidate)))
    for path in sorted((REPO_ROOT / "vi").glob("*.md")):
        covered.update(_redirects(_front_matter(path)))
    for old in EXPECTED_REDIRECTS:
        assert old in covered, (
            f"old URL {old} has no `redirect_from` — it would 404 after the move"
        )


@pytest.mark.static
def test_english_posts_avoid_the_old_vietnamese_slugs():
    """Redirect stubs and English pages must never claim the same output path."""
    vi_slugs = {
        re.sub(r"\.md$", "", path.name) for path in VI_POSTS_DIR.glob("*.md")
    }
    en_slugs = {
        re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        for path in POSTS_DIR.glob("*.md")
    }
    clash = {s.lower() for s in vi_slugs} & {s.lower() for s in en_slugs}
    assert not clash, (
        f"English slugs collide with old Vietnamese URLs: {sorted(clash)} — "
        "the English post and the redirect stub would overwrite each other"
    )


@pytest.mark.static
def test_vi_collection_lookups_are_nil_safe():
    """`site.vi_posts` is nil when the collection is undefined — the upstream
    `_config_theme-dev.yml` CI build (`script/cibuild`) must keep passing, so
    every Liquid *filter* over the collection degrades to an empty list instead
    of crashing `sort`/`where` on nil. (`for` over nil is already safe.)
    """
    guarded = {
        REPO_ROOT / "_layouts" / "tag.html": "tag_vi_source",
        REPO_ROOT / "_layouts" / "home.html": "home_vi_source",
        REPO_ROOT / "_layouts" / "post.html": "rel_vi_source",
        REPO_ROOT / "_includes" / "site-sidebar.html": "sidebar_source",
        REPO_ROOT / "vi" / "tags.md": "vi_tags_source",
    }
    for path, var in guarded.items():
        html = _read(path)
        assert re.search(
            rf"assign {var} = site\.vi_posts", html
        ), f"{path} must read the collection through `{var}`"
        assert re.search(
            rf"if {var} == nil", html
        ), f"{path} must nil-guard `{var}` for the theme-dev CI build"
        assert '"" | split: ""' in html, (
            f"{path} must degrade to an empty list (`\"\" | split: \"\"`)"
        )
    # No unguarded filter over the collection may remain: every other
    # `site.vi_posts` occurrence must be a nil-safe `for` loop or sit inside a
    # `{% comment %}` block.
    for path in [
        REPO_ROOT / "_layouts" / "tag.html",
        REPO_ROOT / "_layouts" / "home.html",
        REPO_ROOT / "_layouts" / "post.html",
        REPO_ROOT / "_includes" / "site-sidebar.html",
        REPO_ROOT / "vi" / "tags.md",
    ]:
        in_comment = False
        for i, line in enumerate(_read(path).splitlines(), 1):
            stripped = line.strip()
            if re.search(r"{%-?\s*comment", stripped):
                in_comment = True
            if in_comment:
                if re.search(r"endcomment", stripped):
                    in_comment = False
                continue
            if "site.vi_posts" not in stripped:
                continue
            assert (
                re.search(r"assign \w+ = site\.vi_posts\s*-?%}", stripped)
                or re.search(r"for \w+ in site\.vi_posts\s*-?%}", stripped)
            ), f"{path}:{i} uses site.vi_posts outside the nil-guard pattern: {stripped}"


@pytest.mark.static
def test_templates_wire_the_switcher_alternates_and_fallback_notice():
    head = _read(REPO_ROOT / "_includes" / "head.html")
    assert "include lang-alternates.html" in head
    assert "hreflang" in _read(REPO_ROOT / "_includes" / "lang-alternates.html")
    assert "x-default" in _read(REPO_ROOT / "_includes" / "lang-alternates.html")
    header = _read(REPO_ROOT / "_includes" / "header.html")
    assert "include lang-switcher.html" in header
    assert "vi/about.md" in header, "the Vietnamese nav must stay inside /vi/"
    comments = _read(REPO_ROOT / "_includes" / "comments.html")
    assert 'data-lang="{{ page.lang' in comments, (
        "giscus must follow the page language, not the site default"
    )
    notice = REPO_ROOT / "_includes" / "vi-fallback-notice.html"
    assert notice.is_file(), "the fallback banner include is missing"
    for layout in ("post.html", "page.html"):
        html = _read(REPO_ROOT / "_layouts" / layout)
        assert "page.fallback_vi" in html and "vi-fallback-notice.html" in html, (
            f"_layouts/{layout} must render the banner on fallback pages"
        )


# --- build guards (need Ruby; no browser) -----------------------------------


def test_html_lang_matches_the_page_language(built_site):
    checked = 0
    for path, _, lang in _iter_content_docs():
        built = _built_for_source(built_site, path)
        if built is None or not built.is_file():
            continue
        html = built.read_text(encoding="utf-8")
        match = re.search(r'<html lang="([^"]*)"', html)
        url = str(built.relative_to(built_site))
        assert match, f"{url} has no <html lang>"
        assert match.group(1) == lang, (
            f"{url} declares lang={match.group(1)!r}, expected {lang!r}"
        )
        checked += 1
    # The two home pages (`.html` sources, covered via their `ref: home`).
    for rel, lang in (("index.html", "en"), ("vi/index.html", "vi")):
        html = (built_site / rel).read_text(encoding="utf-8")
        match = re.search(r'<html lang="([^"]*)"', html)
        assert match and match.group(1) == lang, (
            f"/{rel} declares lang={match.group(1) if match else None!r}, "
            f"expected {lang!r}"
        )
        checked += 1
    assert checked > 20, "the lang guard measured almost nothing — check the URL mapping"


def _alternates(html):
    return re.findall(
        r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html
    )


def test_hreflang_alternates_resolve_to_built_files(built_site):
    checked = 0
    for ref, sides in _ref_pairs().items():
        if not (sides["en"] and sides["vi"]):
            continue  # single-language pages (completed in PR B/C)
        en_name = sides["en"][0]
        html = None
        for name in sides["en"]:
            candidate = _built_for_source(built_site, REPO_ROOT / name)
            if candidate is not None and candidate.is_file():
                html = candidate.read_text(encoding="utf-8")
                break
        if html is None:
            continue
        alternates = dict(
            (hreflang, href) for hreflang, href in _alternates(html)
        )
        assert set(("en", "vi", "x-default")) <= set(alternates), (
            f"ref `{ref}` ({en_name}) is missing hreflang alternates: {alternates}"
        )
        for hreflang, href in alternates.items():
            assert href.startswith(SITE_URL), (
                f"ref `{ref}` hreflang={hreflang} must be absolute: {href}"
            )
            assert _file_for(built_site, href).is_file(), (
                f"ref `{ref}` hreflang={hreflang} points at {href}, "
                "which is not in the build"
            )
        assert alternates["x-default"] == alternates["en"], (
            f"ref `{ref}` x-default must point at the English URL"
        )
        checked += 1
    assert checked > 10, "the hreflang guard measured almost nothing"


def test_no_built_page_renders_the_fallback_banner(built_site):
    """Phase 2 ships real translations: the fallback banner must appear on no
    built page (posts, pages or homes, either language)."""
    checked = 0
    for path, _, _ in _iter_content_docs():
        built = _built_for_source(built_site, path)
        if built is None or not built.is_file():
            continue
        html = built.read_text(encoding="utf-8")
        assert "translation-notice" not in html, (
            f"{built} renders the fallback banner, but phase 2 has no stubs"
        )
        checked += 1
    for rel in ("index.html", "vi/index.html"):
        html = (built_site / rel).read_text(encoding="utf-8")
        assert "translation-notice" not in html, (
            f"/{rel} renders the fallback banner, but phase 2 has no stubs"
        )
        checked += 1
    assert checked > 20, "the banner-absence guard measured almost nothing"


def test_switcher_points_to_a_real_counterpart(built_site):
    checked = 0
    for ref, sides in _ref_pairs().items():
        for lang in ("en", "vi"):
            for name in sides[lang]:
                built = _built_for_source(built_site, REPO_ROOT / name)
                if built is None or not built.is_file():
                    continue
                html = built.read_text(encoding="utf-8")
                match = re.search(
                    r'<a class="lang-switcher"[^>]*href="([^"]+)"', html
                )
                assert match, f"{built} has no language switcher"
                href = match.group(1)
                target = _file_for(built_site, href)
                assert target.is_file(), (
                    f"the switcher on {built} points at {href}, "
                    "which is not in the build"
                )
                if lang == "en":
                    assert href.startswith("/vi/") or href == "/vi/", (
                        f"the switcher on the English {built} must lead to /vi/"
                    )
                else:
                    assert not href.startswith("/vi/"), (
                        f"the switcher on the Vietnamese {built} must lead out "
                        "of /vi/"
                    )
                checked += 1
    assert checked > 20, "the switcher guard measured almost nothing"


def _switcher_href(html):
    """Href of the header language switcher, or None when absent."""
    match = re.search(r'<a class="lang-switcher"[^>]*href="([^"]+)"', html)
    return match.group(1) if match else None


def test_home_switchers_point_at_canonical_homes(built_site):
    """Home switchers must link the canonical homes (#104).

    Regression: `_includes/lang-switcher.html` resolved the counterpart by
    taking the *last* `ref: home` match over `site.pages`, so the
    jekyll-paginate duplicates (`/page2/`, …) overwrote `/` and the
    switcher on `/vi/` pointed at `/page2/` instead of `/`.
    """
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    assert _switcher_href(en_home) == "/vi/", (
        "the switcher on `/` must point at the canonical `/vi/`"
    )
    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    assert _switcher_href(vi_home) == "/", (
        "the switcher on `/vi/` must point at the canonical `/`, not /page2/"
    )
    page2 = built_site / "page2" / "index.html"
    assert page2.is_file(), "/page2/ must survive the move (English pagination stays)"
    assert _switcher_href(page2.read_text(encoding="utf-8")) == "/vi/", (
        "the switcher on `/page2/` must point at the canonical `/vi/`"
    )


def test_no_switcher_targets_a_paginated_url(built_site):
    """No built page may carry a switcher pointing at `/pageN/` (#104)."""
    paginated = re.compile(r"/page\d+/?(\?|#|$)")
    offenders = []
    for html_file in sorted(built_site.rglob("*.html")):
        try:
            html = html_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for href in re.findall(
            r'<a class="lang-switcher"[^>]*href="([^"]+)"', html
        ):
            if paginated.search(href):
                offenders.append(
                    f"{html_file.relative_to(built_site)} -> {href}"
                )
    assert not offenders, (
        "no language switcher may target a paginated URL: "
        + "; ".join(offenders)
    )


def test_switcher_pairs_stay_correct_after_the_pagination_fix(built_site):
    """Spot-check exact counterpart pairs (posts EN/VI, about, portfolio,
    tags) so the #104 first-match fix cannot misroute them."""
    pairs = [
        ("/about/", "/vi/about/"),
        ("/portfolio/", "/vi/portfolio/"),
        ("/tags/", "/vi/tags/"),
        ("/tags/ai-agent/", "/vi/tags/ai-agent/"),
        (
            "/2022/10/27/brewing-vietnamese-coffee.html",
            "/vi/2022/10/27/cach-pha-ca-phe.html",
        ),
    ]
    for en_url, vi_url in pairs:
        en_html = _file_for(built_site, en_url).read_text(encoding="utf-8")
        assert _switcher_href(en_html) == vi_url, (
            f"the switcher on {en_url} must point at {vi_url}"
        )
        vi_html = _file_for(built_site, vi_url).read_text(encoding="utf-8")
        assert _switcher_href(vi_html) == en_url, (
            f"the switcher on {vi_url} must point at {en_url}"
        )


def test_old_vietnamese_urls_emit_redirects_to_vi(built_site):
    for old, new in EXPECTED_REDIRECTS.items():
        stub = _file_for(built_site, old)
        assert stub.is_file(), f"old URL {old} is missing from the build (404)"
        html = stub.read_text(encoding="utf-8")
        assert 'http-equiv="refresh"' in html, (
            f"old URL {old} must emit a redirect stub, not a page"
        )
        assert new in html, f"old URL {old} must redirect to {new}"


def test_canonicals_are_self_referencing(built_site):
    for url in ["/", "/vi/", "/about/", "/vi/about/", "/portfolio/",
                "/vi/portfolio/", "/tags/ai-agent/", "/vi/tags/ai-agent/"]:
        built = _file_for(built_site, url)
        assert built.is_file(), f"{url} is missing from the build"
        html = built.read_text(encoding="utf-8")
        match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        assert match, f"{url} has no canonical"
        assert match.group(1) == f"{SITE_URL}{url}", (
            f"{url} canonical is {match.group(1)}, expected {SITE_URL}{url}"
        )


def test_sidebar_and_tag_pages_stay_in_their_language(built_site):
    en_pages = ["index.html", "page2/index.html", "tags/ai-agent/index.html"]
    home = (built_site / "index.html").read_text(encoding="utf-8")
    post = re.search(r'class="post-link" href="([^"]+)"', home)
    assert post
    en_pages.append(post.group(1).lstrip("/"))
    for rel in en_pages:
        html = (built_site / rel).read_text(encoding="utf-8")
        for marker in VI_ONLY_MARKERS:
            assert marker not in html, (
                f"English page /{rel} leaks the Vietnamese label {marker!r}"
            )
    vi_pages = ["vi/index.html", "vi/tags/ai-agent/index.html"]
    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    vi_post = re.search(r'class="post-link" href="([^"]+)"', vi_home)
    assert vi_post
    vi_pages.append(vi_post.group(1).lstrip("/"))
    for rel in vi_pages:
        html = (built_site / rel).read_text(encoding="utf-8")
        for marker in EN_ONLY_MARKERS:
            assert marker not in html, (
                f"Vietnamese page /{rel} leaks the English label {marker!r}"
            )


def test_tag_pages_list_only_their_own_language(built_site):
    for tag in PILLARS:
        en_html = (built_site / "tags" / tag / "index.html").read_text(
            encoding="utf-8"
        )
        for href in re.findall(r'class="post-link" href="([^"]+)"', en_html):
            assert not href.startswith("/vi/"), (
                f"/tags/{tag}/ links the Vietnamese post {href}"
            )
        vi_html = (built_site / "vi" / "tags" / tag / "index.html").read_text(
            encoding="utf-8"
        )
        links = re.findall(r'class="post-link" href="([^"]+)"', vi_html)
        assert links, f"/vi/tags/{tag}/ lists no posts"
        for href in links:
            assert href.startswith("/vi/"), (
                f"/vi/tags/{tag}/ links the English post {href}"
            )


def test_homes_paginate_in_english_and_list_all_in_vietnamese(built_site):
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    assert 'class="pager"' in en_home, "the English home must keep its pager"
    for href in re.findall(r'class="post-link" href="([^"]+)"', en_home):
        assert not href.startswith("/vi/"), (
            f"the English home lists the Vietnamese post {href}"
        )
    assert (built_site / "page2" / "index.html").is_file(), (
        "/page2/ must survive the move (English pagination stays)"
    )
    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    assert 'class="pager"' not in vi_home, (
        "the Vietnamese home lists every post with no pagination (#93)"
    )
    vi_links = re.findall(r'class="post-link" href="([^"]+)"', vi_home)
    assert len(vi_links) == 6, (
        f"/vi/ must list all 6 Vietnamese posts, got {len(vi_links)}"
    )
    for href in vi_links:
        assert href.startswith("/vi/"), f"/vi/ lists the English post {href}"
