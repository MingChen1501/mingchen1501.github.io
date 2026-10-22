"""Automatic table of contents for posts with enough sections (#134, #345).

Posts need no opt-in flag: `_layouts/post.html` renders the `<details
class="post-toc" open>` ToC from `_includes/post-toc.html` whenever the post
has at least `toc_min_h2` (4) `h2` headings, unless the post sets
`toc: false`. GitHub Pages builds with `--safe`, so `jekyll-toc` is
unavailable, and kramdown's own `{:toc}` marker cannot be injected from the
layout (it only expands inside the post's Markdown source). The include
therefore builds the TOC in pure Liquid from the rendered `h2`/`h3`/`h4`
headings (kramdown `auto_ids` supply the anchors) as a NESTED list:
children `<ul>`s are real descendants of their parent `<li>`, each branch
carrying a disclosure `<button>` (`aria-expanded`/`aria-controls` with a
mount-scoped id). The static markup ships fully expanded with no hidden
subtree, so no JavaScript is needed for the list itself; #345 adds a
post-only scroll-spy (`assets/js/toc-spy.js`, guarded in `test_toc_spy.py`)
that collapses branches on load and auto-expands the branch being read.

The same include is mounted twice (with `mount="inline"`/`"sidebar"` so
branch control ids never collide): inline at the top of `.post-content`
(phones) and as the first `.post-sidebar` section above Tags/Related posts
(desktop). CSS shows exactly one copy per viewport.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted site; one viewport guard covers the
mobile/desktop split.
"""

import re
from pathlib import Path

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
TOC_INCLUDE = REPO_ROOT / "_includes" / "post-toc.html"

LONG_EN_POST = REPO_ROOT / "_posts" / "2022-12-25-explaining-the-internet.md"
LONG_VI_POST = REPO_ROOT / "_vi_posts" / "gioi-thieu-ve-internet.md"
BOUNDARY_VI_POST = REPO_ROOT / "_vi_posts" / "migrate-windows-11-to-fedora.md"
OPTOUT_EN_POST = (
    REPO_ROOT / "_posts" / "2026-01-01-switching-from-windows-11-to-fedora.md"
)
SHORT_POST = REPO_ROOT / "_posts" / "2023-01-31-my-tet-holiday-2023.md"
PLAIN_POST = REPO_ROOT / "_posts" / "2022-10-27-brewing-vietnamese-coffee.md"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _toc_flag(path):
    match = re.search(r"^toc:\s*(\S+)\s*$", _front_matter(path), re.M)
    return match.group(1) if match else None


# --- source contract (static) ------------------------------------------------


@pytest.mark.static
def test_post_layout_shows_toc_automatically_above_a_single_threshold():
    html = _read(POST_LAYOUT)
    # Single constant: the minimum h2 count, documented in the jekyll-post
    # skill front-matter reference.
    assert re.search(r"assign toc_min_h2 = 4", html)
    assert html.count("toc_min_h2") >= 2  # defined once, compared once
    assert "toc_h2_count >= toc_min_h2" in html
    assert "split: '<h2'" in html
    # Explicit opt-out only: an unset flag still shows the ToC.
    assert "page.toc != false" in html
    assert "page.toc == true" not in html


@pytest.mark.static
def test_post_layout_mounts_the_same_include_inline_and_in_the_sidebar():
    html = _read(POST_LAYOUT)
    assert html.count("include post-toc.html") == 2
    assert 'mount="inline"' in html and 'mount="sidebar"' in html, (
        "each mount must scope its branch control ids (#345)"
    )
    inline = html.index("post-toc-mount--inline")
    sidebar = html.index("post-toc-mount--sidebar")
    body_start = html.index('class="post-content e-content"')
    content = html.index("{{ content }}")
    aside = html.index('class="post-sidebar"')
    # Inline copy leads the article body; sidebar copy lives in the aside.
    assert body_start < inline < content < aside < sidebar
    # Both mounts share the one automatic gate.
    assert html.count("if show_toc") >= 2


@pytest.mark.static
def test_sidebar_renders_on_toc_alone_with_toc_first():
    html = _read(POST_LAYOUT)
    assert "post_tags.size > 0 or show_toc" in html
    toc_section = html.index("post-sidebar__section--toc")
    # The tags heading is the first `.post-sidebar__heading` below the ToC
    # section (localized in #142: `Chủ đề` on VI pages, `Tags` on EN ones,
    # so the template no longer carries a literal `>Tags` heading).
    tags_heading = html.index("post-sidebar__heading", toc_section)
    related = html.index("related-posts")
    assert toc_section < tags_heading < related


@pytest.mark.static
def test_toc_include_uses_a_details_block_with_a_localized_summary():
    html = _read(TOC_INCLUDE)
    assert '<details class="post-toc" open>' in html
    assert '<summary class="post-toc__summary">' in html
    assert "On this page" in html
    assert "Trong bài này" in html
    # The summary is a plain label: links are invalid inside `<summary>`.
    summary = html.split("<summary", 1)[1].split("</summary>", 1)[0]
    assert "<a" not in summary


@pytest.mark.static
def test_toc_include_nests_h2_h3_h4_with_per_branch_toggles():
    html = _read(TOC_INCLUDE)
    # Pure Liquid over the rendered headings: no plugin tag, no script.
    assert "<script" not in html
    assert "{% toc" not in html
    assert "toc_level == '2' or toc_level == '3' or toc_level == '4'" in html
    assert 'split: \'id="\'' in html
    assert 'href="#' in html
    assert "strip_html" in html
    # The kramdown `{:toc}` alternative was evaluated and rejected: it only
    # expands inside the post source, so the layout cannot inject it.
    assert "{:toc}" in html
    assert "--safe" in html
    # Nesting fidelity: children lists are real descendants of their
    # parent branch, each branch carrying a disclosure button with a
    # mount-scoped control id and a data-level row marker.
    assert "post-toc__children" in html
    assert "post-toc__toggle" in html
    assert "aria-expanded" in html and "aria-controls" in html
    assert "data-level" in html
    assert "toc_mount" in html, (
        "branch control ids must scope per mount (#345)"
    )


@pytest.mark.static
def test_toc_include_renders_nothing_without_headings():
    html = _read(TOC_INCLUDE)
    # A qualifying post with no `h2`/`h3`/`h4` must not emit an empty box.
    assert "toc_records != ''" in html


@pytest.mark.static
def test_only_the_post_layout_references_the_toc():
    hits = []
    for layout in (REPO_ROOT / "_layouts").glob("*.html"):
        if "post-toc" in _read(layout):
            hits.append(layout.name)
    assert hits == ["post.html"], f"ToC leaked into non-post layouts: {hits}"


@pytest.mark.static
def test_custom_styles_show_exactly_one_toc_mount_per_viewport():
    scss = conftest.custom_styles_text()
    assert ".post-toc-mount--sidebar" in scss
    assert ".post-toc-mount--inline" in scss
    # Phones: sidebar copy hidden (it would duplicate the inline copy at the
    # bottom of the stacked layout); desktop: inline copy hidden.
    sidebar_block = scss.split(".post-toc-mount--sidebar {", 1)[1].split("}", 1)[0]
    assert "display: none;" in sidebar_block
    assert "min-width: $two-column-breakpoint" in scss


@pytest.mark.static
def test_long_posts_need_no_flag_and_short_posts_carry_none():
    assert _toc_flag(LONG_EN_POST) is None
    assert _toc_flag(LONG_VI_POST) is None
    assert _toc_flag(BOUNDARY_VI_POST) is None
    assert _toc_flag(SHORT_POST) is None
    assert _toc_flag(PLAIN_POST) is None
    assert _toc_flag(OPTOUT_EN_POST) == "false"


# --- emitted site (needs Ruby, no browser) -----------------------------------


def _toc_mounts(html):
    # The mount divs wrap the whole `<details>` block, which now contains
    # nested `.post-toc__row` divs: capture up to `</details>`, not the
    # first inner `</div>`.
    inlines = re.findall(
        r'<div class="post-toc-mount post-toc-mount--inline">(.*?</details>)',
        html,
        re.S,
    )
    sidebars = re.findall(
        r'<div class="post-toc-mount post-toc-mount--sidebar">(.*?</details>)',
        html,
        re.S,
    )
    return inlines, sidebars


def _toc_hrefs(mount):
    details = re.search(
        r'<details class="post-toc"[^>]*>(.*?)</details>', mount, re.S
    )
    assert details, "expected a `<details class=\"post-toc\">` block"
    return re.findall(r'href="#([^"]+)"', details.group(1))


@pytest.mark.parametrize(
    ("rel", "label"),
    [
        ("2022/12/25/explaining-the-internet.html", "On this page"),
        ("vi/2022/12/25/gioi-thieu-ve-internet.html", "Trong bài này"),
        ("vi/2026/01/01/migrate-windows-11-to-fedora.html", "Trong bài này"),
    ],
)
def test_long_post_without_flag_renders_both_toc_mounts(built_site, rel, label):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {rel}"
    html = page.read_text(encoding="utf-8")
    inlines, sidebars = _toc_mounts(html)
    assert len(inlines) == 1 and len(sidebars) == 1
    for mount in inlines + sidebars:
        assert label in mount
        hrefs = _toc_hrefs(mount)
        assert len(hrefs) >= 2, "a TOC with fewer than two entries is noise"
        ids = set(re.findall(r'id="([^"]+)"', html))
        missing = [href for href in hrefs if href not in ids]
        assert not missing, f"TOC links without a matching heading id: {missing}"
    # Both mounts list the same sections.
    assert _toc_hrefs(inlines[0]) == _toc_hrefs(sidebars[0])
    # Structural invariants that hold for any heading corpus: toggle
    # targets exist, children lists nest inside branch items, and rows
    # carry their depth for the CSS/JS contract.
    for mount in inlines + sidebars:
        for control in re.findall(r'aria-controls="([^"]+)"', mount):
            assert f'id="{control}"' in mount, (
                f"{rel}: toggle target {control} must render (#345)"
            )
        for child in re.findall(
            r'<ul class="post-toc__list post-toc__children"[^>]*>',
            mount,
        ):
            assert mount.index(child) > mount.index("<li"), (
                f"{rel}: children lists must nest inside a branch (#345)"
            )
        for level in re.findall(r'data-level="(\d)"', mount):
            assert level in ("2", "3", "4"), (
                f"{rel}: unexpected ToC depth {level} (#345)"
            )


@pytest.mark.parametrize(
    "rel",
    [
        # Below the threshold but has headings.
        "2023/01/31/my-tet-holiday-2023.html",
        # No headings at all.
        "2022/10/27/brewing-vietnamese-coffee.html",
        # At the threshold but opted out.
        "2026/01/01/switching-from-windows-11-to-fedora.html",
    ],
)
def test_short_or_opted_out_post_renders_no_toc(built_site, rel):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {rel}"
    html = page.read_text(encoding="utf-8")
    assert '<details class="post-toc"' not in html
    assert "post-toc-mount" not in html


def test_sidebar_orders_toc_before_tags_before_related(built_site):
    # The orchestration post qualifies for a ToC and shares its tag, so all
    # three sidebar sections render.
    page = built_site / "2026/10/17/real-world-agent-orchestration-with-free-opencode.html"
    assert page.is_file(), "expected the long post in the build"
    html = page.read_text(encoding="utf-8")
    toc = html.index("post-sidebar__section--toc")
    tags = html.index('class="post-sidebar__heading">Tags')
    related = html.index("related-posts")
    assert toc < tags < related


# --- viewport behaviour (needs Ruby + browser) --------------------------------

_MOUNT_DISPLAY_JS = """() => {
  const display = (sel) => {
    const el = document.querySelector(sel);
    return el ? getComputedStyle(el).display : 'missing';
  };
  return {
    inline: display('.post-toc-mount--inline'),
    sidebar: display('.post-toc-mount--sidebar'),
  };
}"""


@pytest.mark.parametrize("width,visible,hidden", [(360, "inline", "sidebar"), (375, "inline", "sidebar"), (1280, "sidebar", "inline")])
def test_exactly_one_toc_mount_is_visible_per_viewport(
    built_site_url, browser, width, visible, hidden
):
    context = browser.new_context(viewport={"width": width, "height": 900})
    try:
        page = context.new_page()
        page.goto(
            f"{built_site_url}/2022/12/25/explaining-the-internet.html",
            wait_until="load",
        )
        displays = page.evaluate(_MOUNT_DISPLAY_JS)
        if width < 960:
            # Phone JS path (#383): the inline mount gives way to the
            # floating button, so neither static mount shows.
            assert displays["inline"] == "none", (
                f"the inline mount must hide behind the FAB at {width}px"
            )
            assert displays["sidebar"] == "none"
            assert page.locator(".toc-fab").is_visible(), (
                f"the FAB must be reachable at {width}px"
            )
        else:
            assert displays[visible] != "none", (
                f"expected the {visible} ToC mount to be visible at {width}px"
            )
            assert displays[hidden] == "none", (
                f"expected the {hidden} ToC mount to be hidden at {width}px"
            )
    finally:
        context.close()
