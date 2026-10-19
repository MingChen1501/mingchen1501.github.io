"""Opt-in table of contents for long posts (#125).

Long posts (16-18 sections) get a table of contents without a plugin:
GitHub Pages builds with `--safe`, so `jekyll-toc` is unavailable, and
kramdown's own `{:toc}` marker cannot be injected from the layout (it only
expands inside the post's Markdown source). `_includes/post-toc.html`
therefore builds the TOC in pure Liquid from the rendered `h2`/`h3` headings
(kramdown `auto_ids` supply the anchors), with no JavaScript.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted site.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
TOC_INCLUDE = REPO_ROOT / "_includes" / "post-toc.html"
CUSTOM_STYLES = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"

TOC_EN_POST = REPO_ROOT / "_posts" / "2022-12-25-explaining-the-internet.md"
TOC_VI_POST = REPO_ROOT / "_vi_posts" / "gioi-thieu-ve-internet.md"
PLAIN_POST = REPO_ROOT / "_posts" / "2022-10-27-brewing-vietnamese-coffee.md"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _has_toc_flag(path):
    return bool(re.search(r"^toc:\s*true\s*$", _front_matter(path), re.M))


# --- source contract (static) ------------------------------------------------


@pytest.mark.static
def test_post_layout_gates_toc_on_the_opt_in_flag():
    html = _read(POST_LAYOUT)
    assert "page.toc == true" in html
    assert "include post-toc.html" in html
    # The TOC leads the article body; short posts (no flag) render nothing.
    body_start = html.index('class="post-content e-content"')
    assert body_start < html.index("page.toc == true") < html.index("{{ content }}")


@pytest.mark.static
def test_toc_include_uses_a_details_block_with_a_localized_summary():
    html = _read(TOC_INCLUDE)
    assert '<details class="post-toc">' in html
    assert '<summary class="post-toc__summary">' in html
    assert "On this page" in html
    assert "Trong bài này" in html
    # The summary is a plain label: links are invalid inside `<summary>`.
    summary = html.split("<summary", 1)[1].split("</summary>", 1)[0]
    assert "<a" not in summary


@pytest.mark.static
def test_toc_include_links_h2_and_h3_anchors_without_plugins_or_js():
    html = _read(TOC_INCLUDE)
    # Pure Liquid over the rendered headings: no plugin tag, no script.
    assert "<script" not in html
    assert "{% toc" not in html
    assert "toc_level == '2' or toc_level == '3'" in html
    assert 'split: \'id="\'' in html
    assert 'href="#' in html
    assert "strip_html" in html
    # The kramdown `{:toc}` alternative was evaluated and rejected: it only
    # expands inside the post source, so the layout cannot inject it.
    assert "{:toc}" in html
    assert "--safe" in html


@pytest.mark.static
def test_toc_include_renders_nothing_without_headings():
    html = _read(TOC_INCLUDE)
    # A `toc: true` post with no `h2`/`h3` must not emit an empty box.
    assert "toc_items != ''" in html


@pytest.mark.static
def test_custom_styles_keep_the_toc_compact():
    scss = _read(CUSTOM_STYLES)
    assert ".post-toc" in scss
    assert ".post-toc__summary" in scss
    assert ".post-toc__item--h3" in scss
    block = scss.split(".post-toc {", 1)[1].split("}", 1)[0]
    assert "border:" in block
    assert "border-radius:" in block
    assert "font-size: $small-font-size;" in block
    # Inside the reading measure: no fixed width that could break the
    # column on phones or crowd the sidebar.
    assert "width" not in block


@pytest.mark.static
def test_long_posts_opt_in_and_short_posts_do_not():
    assert _has_toc_flag(TOC_EN_POST), f"{TOC_EN_POST.name} must set `toc: true`"
    assert _has_toc_flag(TOC_VI_POST), f"{TOC_VI_POST.name} must set `toc: true`"
    assert not _has_toc_flag(PLAIN_POST), (
        f"{PLAIN_POST.name} must not set `toc: true` (opt-in only)"
    )


# --- emitted site (needs Ruby, no browser) -----------------------------------


def _toc_links(html):
    details = re.search(r'<details class="post-toc">(.*?)</details>', html, re.S)
    assert details, "expected a `<details class=\"post-toc\">` block"
    return re.findall(r'href="#([^"]+)"', details.group(1)), details.group(1)


@pytest.mark.parametrize(
    ("rel", "label"),
    [
        ("2022/12/25/explaining-the-internet.html", "On this page"),
        ("vi/2022/12/25/gioi-thieu-ve-internet.html", "Trong bài này"),
    ],
)
def test_toc_post_renders_a_toc_with_working_anchors(built_site, rel, label):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {rel}"
    html = page.read_text(encoding="utf-8")
    hrefs, details = _toc_links(html)
    assert label in details
    assert len(hrefs) >= 2, "a TOC with fewer than two entries is noise"
    ids = set(re.findall(r'id="([^"]+)"', html))
    missing = [href for href in hrefs if href not in ids]
    assert not missing, f"TOC links without a matching heading id: {missing}"


def test_post_without_the_flag_renders_no_toc(built_site):
    page = built_site / "2022/10/27/brewing-vietnamese-coffee.html"
    assert page.is_file(), "expected the plain post in the build"
    html = page.read_text(encoding="utf-8")
    assert '<details class="post-toc">' not in html
