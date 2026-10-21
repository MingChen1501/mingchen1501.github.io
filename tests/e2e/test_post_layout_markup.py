"""Static guard tests for the post-page layout and the tag pages.

Epic #44 ("UX layout: post page with secondary tag column + tag pages"):
#45 adds the two-column post page, #46 adds ``/tags/<tag>/``, #47 reuses the
same chips on the home post list.

Bilingual (#93): English lives in ``_posts``/``tags``/``tags.md`` (``/``,
``/tags/``), Vietnamese in ``_vi_posts``/``vi/tags``/``vi/tags.md``
(``/vi/``, ``/vi/tags/``). Every guard below covers both languages.

These run without a browser and fail fast when the templates drift:

- ``_layouts/post.html`` must keep the two-column structure (main = post,
  secondary = the post's tags) and the comments gating that
  ``tests/e2e`` browser tests rely on.
- ``_includes/post-tags.html`` must link every chip to ``/tags/<tag>/`` on
  English pages and ``/vi/tags/<tag>/`` on Vietnamese ones, and stay the
  single source of the chip markup (the home list may only pass the
  extra-class parameter added for #47).
- ``_layouts/home.html`` must render those chips per list item, after the
  date/title/excerpt, without forking the include.
- Every tag used by a *published* post must have a tag page in its own
  language (``tags/<tag>.md`` / ``vi/tags/<tag>.md``) whose front matter
  declares the same tag and permalink, so a tag chip can never 404.
- ``tags.md`` / ``vi/tags.md`` (the ``/tags/`` / ``/vi/tags/`` indexes) and
  ``_layouts/tag.html`` must stay in sync with those tag pages.
"""

import re
from pathlib import Path

import conftest
import pytest
import yaml

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
HOME_LAYOUT = REPO_ROOT / "_layouts" / "home.html"
BASE_LAYOUT = REPO_ROOT / "_layouts" / "base.html"
TAG_LAYOUT = REPO_ROOT / "_layouts" / "tag.html"
POST_TAGS_INCLUDE = REPO_ROOT / "_includes" / "post-tags.html"
POST_CARD_INCLUDE = REPO_ROOT / "_includes" / "post-card.html"
TAGS_INDEX = REPO_ROOT / "tags.md"
TAG_PAGES_DIR = REPO_ROOT / "tags"
VI_TAGS_INDEX = REPO_ROOT / "vi" / "tags.md"
VI_TAG_PAGES_DIR = REPO_ROOT / "vi" / "tags"
POSTS_DIR = REPO_ROOT / "_posts"
VI_POSTS_DIR = REPO_ROOT / "_vi_posts"

PILLARS = ["backend-production", "ai-agent", "linux-tooling", "doi-song"]

TAG_LABELS = REPO_ROOT / "_data" / "tag_labels.yml"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


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


def _published_post_tags(posts_dir):
    """Tag list per published post in ``posts_dir``, as ``(post_name, tags)``."""
    posts = []
    for path in sorted(posts_dir.glob("*.md")):
        front_matter = _front_matter(path)
        if re.search(r"^published:\s*false\s*$", front_matter, re.M):
            continue
        tags = _front_matter_tags(front_matter)
        if tags:
            posts.append((path.name, tags))
    return posts


def _tag_pages(tag_pages_dir):
    return {
        path.stem: _front_matter(path) for path in sorted(tag_pages_dir.glob("*.md"))
    }


def _tag_labels():
    """The single source of truth for tag labels/slugs (#129)."""
    assert TAG_LABELS.is_file(), "_data/tag_labels.yml is missing"
    return yaml.safe_load(TAG_LABELS.read_text(encoding="utf-8")) or {}


def _canonical_tag_keys(tag_pages_dir):
    """Canonical tag keys served by a tag-page directory (via `tag:`).

    File names are localized URL slugs (#129: `tags/life.md` serves the
    canonical `doi-song` key), so the front matter — not the stem — decides
    which key a page serves.
    """
    keys = set()
    for path in sorted(tag_pages_dir.glob("*.md")):
        match = re.search(r"^tag:\s*(.+?)\s*$", _front_matter(path), re.M)
        if match:
            keys.add(match.group(1))
    return keys


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


def test_post_sidebar_lists_posts_sharing_any_tag():
    html = _read(POST_LAYOUT)
    # #343: the related list is the union over ALL of the post's tags, not
    # the first one — no `primary_tag` / `post_tags.first` may remain.
    assert "primary_tag" not in html
    assert "post_tags.first" not in html
    # Each tag contributes its language's posts; English via `site.tags`,
    # Vietnamese via a nil-safe `site.vi_posts` filter on the loop variable.
    assert "for rel_tag in post_tags" in html
    assert "site.tags[rel_tag]" in html
    assert '"rel_post.tags contains rel_tag"' in html
    assert "rel_union" in html and "concat" in html
    # Ordering rule (#343): newest first across the union, same-date ties
    # broken by URL, de-duplicated so a two-tag post renders once.
    assert 'sort: "url"' in html
    assert 'sort: "date"' in html
    assert "reverse" in html
    assert "push: rel_post" in html
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
    scss = conftest.custom_styles_text()
    # Both grid declarations must guard the track with minmax(0, ...): plain
    # `1fr` means minmax(auto, 1fr), so a long unbreakable run can widen the
    # column (and the document) past a 375px viewport on phones.
    assert "grid-template-columns: minmax(0, 1fr) $post-sidebar-width;" in scss
    assert "$post-sidebar-width: 240px;" in scss
    # Single column below the desktop breakpoint.
    assert "grid-template-columns: minmax(0, 1fr);" in scss
    assert "grid-template-columns: 1fr;" not in scss
    # The extra width belongs to the post content wrapper only; a bare
    # `.layout-post .wrapper` also matches the header/footer wrappers.
    assert ".layout-post main .wrapper" in scss
    assert "$two-column-breakpoint: 960px;" in scss
    assert "min-width: $two-column-breakpoint" in scss


# --- tag chips + tag pages (#46) ------------------------------------------


def test_post_tags_include_links_every_chip_to_its_tag_page():
    html = _read(POST_TAGS_INCLUDE)
    assert "include.tags" in html
    assert "tag-chip" in html
    # One base per language (#93): English chips to `/tags/<slug>/`,
    # Vietnamese chips to `/vi/tags/<slug>/`, via a single variable.
    # Labels and slugs resolve per language through the shared
    # `_includes/tag-label.html` partial (#129, #175), so the chip links the
    # tag page of the current language.
    assert "chips_base | append: chip_slug | append: '/'" in html
    assert "chips_base = '/tags/'" in html
    assert "chips_base = '/vi/tags/'" in html
    assert "include tag-label.html" in html
    assert "key=tag" in html
    assert "lang=chips_lang" in html
    assert "site.data.tag_labels" not in html
    assert "chip_label" in html
    assert "relative_url" in html


def test_tag_layout_lists_posts_for_page_tag():
    html = _read(TAG_LAYOUT)
    assert "tag_name = page.tag" in html
    assert "site.tags[tag_name]" in html
    assert "site.vi_posts" in html
    assert 'class="post-list"' in html
    # The chips and the back link stay inside the page's language (#93).
    assert "tag_base = '/tags/'" in html
    assert "tag_base = '/vi/tags/'" in html
    assert "tag_base | relative_url" in html
    # The heading and the intro chip read the label/slug for the page's
    # language through the shared `_includes/tag-label.html` partial
    # (#129, #175).
    assert "include tag-label.html" in html
    assert "key=tag_name" in html
    assert "lang=tag_lang" in html
    assert "site.data.tag_labels" not in html
    assert "tag_base | append: tag_slug" in html


def test_every_published_post_tag_has_a_tag_page():
    for posts_dir, tag_pages_dir in (
        (POSTS_DIR, TAG_PAGES_DIR),
        (VI_POSTS_DIR, VI_TAG_PAGES_DIR),
    ):
        keys = _canonical_tag_keys(tag_pages_dir)
        for post_name, tags in _published_post_tags(posts_dir):
            for tag in tags:
                assert tag in keys, (
                    f"{post_name} uses tag '{tag}' with no tag page "
                    f"declaring `tag: {tag}` under "
                    f"{tag_pages_dir.relative_to(REPO_ROOT)}/"
                )


def test_published_posts_only_use_the_four_pillars():
    for posts_dir in (POSTS_DIR, VI_POSTS_DIR):
        for post_name, tags in _published_post_tags(posts_dir):
            assert set(tags) <= set(PILLARS), f"{post_name} uses tags outside the pillars: {tags}"


def test_tag_pages_declare_the_matching_tag_and_permalink():
    labels = _tag_labels()
    for tag_pages_dir, slug_key, base in (
        (TAG_PAGES_DIR, "slug_en", "/tags/"),
        (VI_TAG_PAGES_DIR, "slug_vi", "/vi/tags/"),
    ):
        seen = set()
        for stem, front_matter in _tag_pages(tag_pages_dir).items():
            rel = f"{tag_pages_dir.relative_to(REPO_ROOT)}/{stem}.md"
            tag = re.search(r"^tag:\s*(.+?)\s*$", front_matter, re.M)
            assert tag, f"{rel} must declare a canonical `tag:`"
            key = tag.group(1)
            assert key in PILLARS, f"{rel} serves a tag outside the pillars: {key}"
            assert key in labels, f"{rel} serves a tag missing from tag_labels.yml: {key}"
            # The permalink is the *localized* slug (#129: `doi-song` lives
            # at `/tags/life/` in English, `/vi/tags/doi-song/` in Vietnamese).
            expected = f"{base}{labels[key][slug_key]}/"
            assert re.search(
                rf"^permalink:\s*{re.escape(expected)}\s*$",
                front_matter,
                re.M,
            ), f"{rel} must declare `permalink: {expected}`"
            assert re.search(r"^layout:\s*tag\s*$", front_matter, re.M)
            seen.add(key)
        assert seen == set(PILLARS), (
            f"{tag_pages_dir.relative_to(REPO_ROOT)}/ must serve every pillar: "
            f"missing {sorted(set(PILLARS) - seen)}"
        )


def test_tags_index_links_every_tag_page():
    for tags_index, tag_pages_dir, base in (
        (TAGS_INDEX, TAG_PAGES_DIR, "/tags/"),
        (VI_TAGS_INDEX, VI_TAG_PAGES_DIR, "/vi/tags/"),
    ):
        index = _read(tags_index)
        rel_index = tags_index.relative_to(REPO_ROOT)

        listed = re.search(r'assign pillars = "([^"]+)"', index)
        assert listed, f"{rel_index} must list the pillars to build the index"
        assert listed.group(1).split(",") == PILLARS

        # The index builds the chip label and URL from the loop variable via
        # `_data/tag_labels.yml` (#129), so the pillar list carries canonical
        # keys while the rendered links carry localized slugs.
        assert "site.data.tag_labels[pillar]" in index
        assert f"'{base}' | append: pillar_slug | append: '/'" in index
        for key in _canonical_tag_keys(tag_pages_dir):
            assert key in listed.group(1), f"{rel_index} does not link {key}"


def test_permalinks_of_generated_tag_pages_are_unique():
    permalinks = []
    for tag_pages_dir in (TAG_PAGES_DIR, VI_TAG_PAGES_DIR):
        for stem, front_matter in _tag_pages(tag_pages_dir).items():
            match = re.search(r"^permalink:\s*(.+?)\s*$", front_matter, re.M)
            assert match, (
                f"{tag_pages_dir.relative_to(REPO_ROOT)}/{stem}.md "
                "must declare a permalink"
            )
            permalinks.append(match.group(1))
    assert len(permalinks) == len(set(permalinks)) == 2 * len(PILLARS)


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
    # The card lives in the shared include (#293): the home layout only
    # renders it.
    html = _read(HOME_LAYOUT)
    assert "include post-card.html" in html
    # No forked chip markup: the chips come from the shared include.
    assert "include post-tags.html" not in html
    assert 'class="tag-chip"' not in html
    assert "'/tags/' | append" not in html
    card = _read(POST_CARD_INCLUDE)
    assert "include post-tags.html" in card
    assert "tags=include.post.tags" in card
    assert 'class="tag-chip-list--home"' in card


def test_home_list_chips_come_after_the_excerpt_inside_the_item():
    card = _read(POST_CARD_INCLUDE)
    excerpt = card.index("{{ include.post.excerpt }}")
    chips = card.index("include post-tags.html")
    item_end = card.index("</li>")
    # Date/title/excerpt stay where they were; the chips are appended last.
    assert excerpt < chips < item_end
    # The include itself renders nothing without tags, so untagged posts keep
    # the original spacing.
    assert "chips.size > 0" in _read(POST_TAGS_INCLUDE)


def test_custom_styles_keep_the_home_chip_variant_to_spacing():
    scss = conftest.custom_styles_text()
    assert "ul.tag-chip-list--home" in scss
    # The variant may only adjust spacing; the chip look is shared with the
    # post sidebar (#45) and the tag pages (#46).
    assert ".tag-chip--home" not in scss
    assert "flex-wrap: wrap" in scss
