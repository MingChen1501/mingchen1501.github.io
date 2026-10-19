"""Estimated reading time on post pages and post lists (#124).

Every post shows a localized estimate — `N min read` (EN) / `N phút đọc`
(VI) — computed from the rendered content word count at ~200 wpm, rounded
up, minimum 1 minute. The estimate lives in the post header
(`_layouts/post.html`) and in every home/tag list item
(`_layouts/home.html`, `_layouts/tag.html`), all through the single shared
`_includes/reading-time.html` (pure Liquid: `number_of_words`, no plugins,
so the GitHub Pages `--safe` build keeps working).

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted site: the label is present and correctly
worded per language, and the list figure always agrees with the post page
(both count the same full content, so excerpt shortening cannot skew the
list).
"""

import re
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
READING_TIME_INCLUDE = REPO_ROOT / "_includes" / "reading-time.html"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"

# A short and a long post per language, each listed on its tag page (tag
# pages list every post with the tag; the home list is paginated, so the
# build guards scan every home page for the post link instead of assuming
# page one). EN lifestyle posts live under the "Life" slug (#129).
CASES = [
    {
        "post": "2022/10/27/brewing-vietnamese-coffee.html",
        "tag_page": "tags/life/index.html",
        "label": "min read",
    },
    {
        "post": "2022/12/25/explaining-the-internet.html",
        "tag_page": "tags/backend-production/index.html",
        "label": "min read",
    },
    {
        "post": "vi/2022/10/27/cach-pha-ca-phe.html",
        "tag_page": "vi/tags/doi-song/index.html",
        "label": "phút đọc",
    },
    {
        "post": "vi/2022/12/25/gioi-thieu-ve-internet.html",
        "tag_page": "vi/tags/backend-production/index.html",
        "label": "phút đọc",
    },
]

READING_TIME_RE = re.compile(
    r'<time class="reading-time__value" datetime="PT(\d+)M">([^<]+)</time>'
)


def _read(path):
    return path.read_text(encoding="utf-8")


# --- source contract (static) ------------------------------------------------


@pytest.mark.static
def test_reading_time_include_counts_words_at_200wpm_rounded_up_min_one():
    html = _read(READING_TIME_INCLUDE)
    assert "number_of_words" in html
    assert "divided_by: 200" in html
    assert "ceil" in html
    # An empty post still reads "1 min read", never "0 min read".
    assert re.search(r"rt_minutes < 1", html)
    assert "min read" in html
    assert "phút đọc" in html
    # A `<time>` element consistent with the post-meta style, with a valid
    # ISO 8601 duration so the element is not a bare span.
    assert '<time class="reading-time__value" datetime="PT' in html


@pytest.mark.static
def test_reading_time_include_uses_no_plugins_or_js():
    html = _read(READING_TIME_INCLUDE)
    assert "<script" not in html
    assert "{%" in html  # Liquid only
    assert "{% toc" not in html


@pytest.mark.static
def test_post_header_renders_reading_time_from_page_content():
    html = _read(POST_LAYOUT)
    assert "include reading-time.html" in html
    assert "include reading-time.html content=content" in html
    assert "lang=post_lang" in html
    # Inside the header meta, so it inherits the meta font and divider style.
    meta_start = html.index('class="post-meta"')
    assert meta_start < html.index("include reading-time.html")


@pytest.mark.static
@pytest.mark.parametrize("layout", [HOME_LAYOUT, TAG_LAYOUT], ids=["home", "tag"])
def test_list_layouts_render_reading_time_from_full_post_content(layout):
    html = _read(layout)
    assert "include reading-time.html" in html
    # The full content — not the excerpt — so the list figure always agrees
    # with the post page.
    assert "content=post.content" in html
    assert "reading-time.html" in html
    # Inside the list item's `.post-meta` line, next to the date.
    assert '<span class="post-meta">' in html
    assert html.index('<span class="post-meta">') < html.index(
        "include reading-time.html"
    )


@pytest.mark.static
def test_list_layouts_keep_the_page_language_for_the_label():
    assert "lang=home_lang" in _read(HOME_LAYOUT)
    assert "lang=tag_lang" in _read(TAG_LAYOUT)


@pytest.mark.static
def test_custom_styles_keep_the_reading_time_label_unsplit():
    scss = conftest.custom_styles_text()
    assert ".reading-time" in scss
    block = scss.split(".reading-time {", 1)[1].split("}", 1)[0]
    assert "white-space: nowrap" in block


# --- emitted site (needs Ruby, no browser) -----------------------------------


def _post_minutes_and_label(post_html, rel):
    matches = READING_TIME_RE.findall(post_html)
    assert matches, f"{rel}: no reading-time element on the post page"
    assert len(matches) == 1, (
        f"{rel}: expected exactly one reading-time element, found {len(matches)}"
    )
    minutes, label = int(matches[0][0]), matches[0][1].strip()
    return minutes, label


def _list_minutes(list_html, post_rel, list_rel):
    """Minutes shown for the post link in one home/tag list page.

    Matches from the list item's own `<span class="post-meta">` up to its
    title link without crossing a `</li>`, so nested tag-chip items and the
    sidebar's post links can never leak into the match.
    """
    region = re.search(
        r'<span class="post-meta">(?:(?!</li>).)*?href="[^"]*'
        + re.escape(post_rel)
        + r'"',
        list_html,
        re.S,
    )
    assert region, f"{list_rel}: no list item linking to {post_rel}"
    matches = READING_TIME_RE.findall(region.group(0))
    assert matches, (
        f"{list_rel}: list item for {post_rel} shows no reading time"
    )
    assert len(matches) == 1, (
        f"{list_rel}: list item for {post_rel} shows {len(matches)} "
        "reading-time elements"
    )
    return int(matches[0][0])


def _home_pages(built_site, lang):
    """Every paginated home list page of one language."""
    pages = []
    if lang == "vi":
        for rel in ["vi/index.html", "vi/page2/index.html", "vi/page3/index.html"]:
            candidate = built_site / rel
            if candidate.is_file():
                pages.append(candidate)
    else:
        for rel in ["index.html", "page2/index.html", "page3/index.html"]:
            candidate = built_site / rel
            if candidate.is_file():
                pages.append(candidate)
    assert pages, f"no built home list page found for lang={lang!r}"
    return pages


@pytest.mark.parametrize("case", CASES, ids=[c["post"] for c in CASES])
def test_post_page_shows_a_localized_reading_time_of_at_least_one_minute(
    built_site, case
):
    page = built_site / case["post"]
    assert page.is_file(), f"expected a built page at {case['post']}"
    minutes, label = _post_minutes_and_label(
        page.read_text(encoding="utf-8"), case["post"]
    )
    assert minutes >= 1, f"{case['post']}: reading time must be at least 1 minute"
    assert label == f"{minutes} {case['label']}", (
        f"{case['post']}: expected {minutes} {case['label']!r}, got {label!r}"
    )


@pytest.mark.parametrize("case", CASES, ids=[c["post"] for c in CASES])
def test_list_and_post_page_agree_on_the_reading_time(built_site, case):
    post_html = (built_site / case["post"]).read_text(encoding="utf-8")
    post_minutes, _ = _post_minutes_and_label(post_html, case["post"])

    lang = "vi" if case["post"].startswith("vi/") else "en"
    list_pages = _home_pages(built_site, lang)
    tag_page = built_site / case["tag_page"]
    assert tag_page.is_file(), f"expected a built tag page at {case['tag_page']}"
    list_pages.append(tag_page)

    checked = 0
    for list_page in list_pages:
        html = list_page.read_text(encoding="utf-8")
        # The sidebar repeats post links (highlights + collapsed tag rows),
        # so only the main list column counts: the sidebar `<aside>` always
        # follows `.site-main` in the DOM on home/tag pages.
        main_html = html.split('<aside class="site-sidebar"', 1)[0]
        if f'href="/{case["post"]}"' not in main_html:
            continue  # paginated home page without this post
        rel = list_page.relative_to(built_site).as_posix()
        assert _list_minutes(main_html, case["post"], rel) == post_minutes, (
            f"{rel}: list shows a different reading time for "
            f"{case['post']} than the post page ({post_minutes} min)"
        )
        checked += 1
    assert checked >= 2, (
        f"{case['post']}: expected the post on its tag page and at least one "
        "home page, found it on fewer"
    )
