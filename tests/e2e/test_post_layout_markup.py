"""Static guard tests for the post-page layout and the tag pages.

Epic #44 ("UX layout: post page with secondary tag column + tag pages"):
#45 adds the two-column post page, #46 adds ``/tags/<tag>/``, #47 reuses the
same chips on the home post list.

These run without a browser and fail fast when the templates drift:

- ``_layouts/post.html`` must keep the two-column structure (main = post,
  secondary = the post's tags) and the comments gating that
  ``tests/e2e`` browser tests rely on.
- ``_includes/post-tags.html`` must link every chip to ``/tags/<tag>/`` and
  stay the single source of the chip markup (the home list may only pass the
  extra-class parameter added for #47).
- ``_layouts/home.html`` must render those chips per list item, after the
  date/title/excerpt, without forking the include.
- Every tag used by a *published* post must have a ``tags/<tag>.md`` page
  whose front matter declares the same tag and permalink, so a tag chip can
  never 404.
- ``tags.md`` (the ``/tags/`` index) and ``_layouts/tag.html`` must stay in
  sync with those tag pages.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
BASE_LAYOUT = REPO_ROOT / "_layouts" / "base.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
POST_TAGS_INCLUDE = REPO_ROOT / "_includes" / "post-tags.html"
TAGS_INDEX = REPO_ROOT / "tags.md"
TAG_PAGES_DIR = REPO_ROOT / "tags"
CUSTOM_STYLES = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
POSTS_DIR = REPO_ROOT / "_posts"

PILLARS = ["backend-production", "ai-agent", "linux-tooling", "doi-song"]

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
TAG_PERMALINK = "/tags/{tag}/"


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _front_matter_tags(front_matter):
    inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
    if inline:
        return [t.strip().strip("'\"") for t in inline.group(1).split(",") if t.strip()]

    block = re.search(r"^tags:\s*\n((?:[ \t]*-[ \t]*.+?\n)+)", front_matter, re.M)
    if block:
        return [
            line.strip()[1:].strip().strip("'\"")
            for line in block.group(1).splitlines()
            if line.strip()
        ]
    return []


def _published_post_tags():
    """Tag list per published post, as ``(post_name, tags)``."""
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        front_matter = _front_matter(path)
        if re.search(r"^published:\s*false\s*$", front_matter, re.M):
            continue
        tags = _front_matter_tags(front_matter)
        if tags:
            posts.append((path.name, tags))
    return posts


def _tag_pages():
    return {
        path.stem: _front_matter(path) for path in sorted(TAG_PAGES_DIR.glob("*.md"))
    }


# --- post layout (#45) -----------------------------------------------------


def test_post_layout_is_two_column():
    html = _read(POST_LAYOUT)
    assert 'class="post-layout"' in html
    assert 'class="post-main"' in html
    assert '<aside class="post-sidebar"' in html
    # The post itself stays the main column.
    assert '<div class="post-content e-content" itemprop="articleBody">' in html


def test_post_sidebar_renders_the_posts_tags():
    html = _read(POST_LAYOUT)
    assert "post_tags = page.tags" in html
    assert "include post-tags.html" in html
    # No tags -> no empty sidebar box.
    assert "post_tags.size > 0" in html


def test_post_sidebar_lists_posts_sharing_the_first_tag():
    html = _read(POST_LAYOUT)
    assert "primary_tag = post_tags.first" in html
    assert "site.tags[primary_tag]" in html
    assert 'class="related-posts"' in html
    # The current post must not list itself.
    assert "other.url != page.url" in html


def test_post_layout_keeps_comments_outside_the_grid():
    html = _read(POST_LAYOUT)
    aside_end = html.index("</aside>")
    grid_end = html.index("</div>", aside_end)  # closes .post-layout
    comments = html.index("comments_provider = site.comments.provider")
    assert aside_end < grid_end < comments, "comments must stay full width, outside the grid"
    # Comments gating stays intact (also guarded by test_comments_markup.py).
    assert "jekyll.environment == 'production'" in html
    assert "page.comments == false" in html
    assert "include comments.html" in html


def test_base_layout_exposes_the_layout_name_for_styling():
    html = _read(BASE_LAYOUT)
    assert 'class="layout-{{ page.layout | default: ' in html


def test_custom_styles_define_the_two_column_grid():
    scss = _read(CUSTOM_STYLES)
    # Both grid declarations must guard the track with minmax(0, ...): plain
    # `1fr` means minmax(auto, 1fr), so a long unbreakable run can widen the
    # column (and the document) past a 375px viewport on phones.
    assert "grid-template-columns: minmax(0, 1fr) 240px;" in scss
    # Single column below the desktop breakpoint.
    assert "grid-template-columns: minmax(0, 1fr);" in scss
    assert "grid-template-columns: 1fr;" not in scss
    # The extra width belongs to the post content wrapper only; a bare
    # `.layout-post .wrapper` also matches the header/footer wrappers.
    assert ".layout-post main .wrapper" in scss
    assert "min-width: 960px" in scss


# --- tag chips + tag pages (#46) ------------------------------------------


def test_post_tags_include_links_every_chip_to_its_tag_page():
    html = _read(POST_TAGS_INCLUDE)
    assert "include.tags" in html
    assert "tag-chip" in html
    assert "'/tags/' | append: tag | append: '/'" in html
    assert "relative_url" in html


def test_tag_layout_lists_posts_for_page_tag():
    html = _read(TAG_LAYOUT)
    assert "tag_name = page.tag" in html
    assert "site.tags[tag_name]" in html
    assert 'class="post-list"' in html
    assert "'/tags/' | relative_url" in html


def test_every_published_post_tag_has_a_tag_page():
    tag_pages = _tag_pages()
    for post_name, tags in _published_post_tags():
        for tag in tags:
            assert tag in tag_pages, f"{post_name} uses tag '{tag}' with no tags/{tag}.md"


def test_published_posts_only_use_the_four_pillars():
    for post_name, tags in _published_post_tags():
        assert set(tags) <= set(PILLARS), f"{post_name} uses tags outside the pillars: {tags}"


def test_tag_pages_declare_the_matching_tag_and_permalink():
    for tag, front_matter in _tag_pages().items():
        assert re.search(rf"^tag:\s*{re.escape(tag)}\s*$", front_matter, re.M), (
            f"tags/{tag}.md must declare `tag: {tag}`"
        )
        assert re.search(
            rf"^permalink:\s*{re.escape(TAG_PERMALINK.format(tag=tag))}\s*$",
            front_matter,
            re.M,
        ), f"tags/{tag}.md must declare `permalink: {TAG_PERMALINK.format(tag=tag)}`"
        assert re.search(r"^layout:\s*tag\s*$", front_matter, re.M)


def test_tags_index_links_every_tag_page():
    index = _read(TAGS_INDEX)
    tag_pages = _tag_pages()

    listed = re.search(r'assign pillars = "([^"]+)"', index)
    assert listed, "tags.md must list the pillars to build the index"
    assert listed.group(1).split(",") == PILLARS

    # The index builds the chip URL from the loop variable, so the pillar list
    # plus the permalink shape are what has to stay in sync.
    assert "'/tags/' | append: pillar | append: '/'" in index
    for tag in tag_pages:
        assert tag in listed.group(1), f"tags.md does not link tags/{tag}.md"


def test_permalinks_of_generated_tag_pages_are_unique():
    permalinks = []
    for tag, front_matter in _tag_pages().items():
        permalinks.append(TAG_PERMALINK.format(tag=tag))
    assert len(permalinks) == len(set(permalinks)) == len(PILLARS)


# --- home list chips (#47) -------------------------------------------------


def test_post_tags_include_takes_an_optional_extra_class():
    html = _read(POST_TAGS_INCLUDE)
    # #47 varies the chips' spacing from the home list, so the include takes a
    # class instead of the layout forking the chip markup.
    assert "extra_class = include.class" in html
    assert 'class="tag-chip-list{% if extra_class != ' in html
    # The chips themselves stay identical for every caller.
    assert '<a class="tag-chip" rel="tag"' in html


def test_home_list_renders_the_shared_tag_chips():
    html = _read(HOME_LAYOUT)
    assert "include post-tags.html" in html
    assert "tags=post.tags" in html
    assert 'class="tag-chip-list--home"' in html
    # No forked chip markup: the chips come from the shared include.
    assert 'class="tag-chip"' not in html
    assert "'/tags/' | append" not in html


def test_home_list_chips_come_after_the_excerpt_inside_the_item():
    html = _read(HOME_LAYOUT)
    loop = html.index("{%- for post in posts -%}")
    excerpt = html.index("{{ post.excerpt }}", loop)
    chips = html.index("include post-tags.html", loop)
    item_end = html.index("</li>", loop)
    # Date/title/excerpt stay where they were; the chips are appended last.
    assert excerpt < chips < item_end
    # The include itself renders nothing without tags, so untagged posts keep
    # the original spacing.
    assert "chips.size > 0" in _read(POST_TAGS_INCLUDE)


def test_custom_styles_keep_the_home_chip_variant_to_spacing():
    scss = _read(CUSTOM_STYLES)
    assert "ul.tag-chip-list--home" in scss
    # The variant may only adjust spacing; the chip look is shared with the
    # post sidebar (#45) and the tag pages (#46).
    assert ".tag-chip--home" not in scss
    assert "flex-wrap: wrap" in scss
