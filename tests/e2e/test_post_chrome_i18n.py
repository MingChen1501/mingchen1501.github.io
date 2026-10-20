"""Localized post chrome headings (#142).

Vietnamese post pages rendered two English chrome labels: the post sidebar
tags heading (hardcoded `Tags` in `_layouts/post.html`) and the comments
heading (hardcoded `Comments` in both the giscus and disqus branches of
`_includes/comments.html`). Both labels now follow the page language using
the existing `post_lang`-style detection (`page.lang | default: site.lang`):

- tags sidebar heading: `Chủ đề` on VI pages (the project's existing
  Vietnamese wording for tag topics, matching `sidebar_topics_heading` and
  `vi/tags.md`), `Tags` on EN pages;
- comments heading: `Bình luận` on VI pages (matching the already-localized
  disabled-comments message `Đã tắt bình luận cho bài này.`), `Comments` on
  EN pages.

Static guards (no Ruby) cover the template contract; the tags build guard
(needs Ruby, no browser) reuses the shared dev build. The comments heading
production render lives in `test_giscus_comments.py`
(`test_production_build_localizes_comments_heading`), which already owns a
production build — one shared build instead of two (#297).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
COMMENTS_INCLUDE = REPO_ROOT / "_includes" / "comments.html"

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _read(path):
    return path.read_text(encoding="utf-8")


def _sidebar_headings(html):
    return re.findall(r'class="post-sidebar__heading">(.*?)</h2>', html)


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_post_sidebar_tags_heading_is_localized():
    html = _read(POST_LAYOUT)
    match = re.search(
        r'class="post-sidebar__heading">\{% if post_lang == \'vi\' %\}'
        r"(.*?)"
        r"\{% else %\}(.*?)\{% endif %\}</h2>",
        html,
    )
    assert match, "the tags sidebar heading must branch on `post_lang == 'vi'`"
    assert match.group(1) == "Chủ đề", (
        "the VI tags sidebar heading must read `Chủ đề`, "
        f"got {match.group(1)!r}"
    )
    assert match.group(2) == "Tags", (
        "the EN tags sidebar heading must stay byte-identical (`Tags`), "
        f"got {match.group(2)!r}"
    )


@pytest.mark.static
def test_comments_include_detects_the_page_language():
    html = _read(COMMENTS_INCLUDE)
    assert re.search(
        r"assign comments_lang = page\.lang \| default: site\.lang \| default: 'en'",
        html,
    ), "comments.html must detect the page language like `post_lang` does"


@pytest.mark.static
def test_comments_headings_are_localized_in_both_branches():
    html = _read(COMMENTS_INCLUDE)
    headings = re.findall(
        r'class="comments__title"[^>]*>\{% if comments_lang == \'vi\' %\}'
        r"(.*?)"
        r"\{% else %\}(.*?)\{% endif %\}</h2>",
        html,
    )
    assert len(headings) == 2, (
        "both comments branches (giscus and disqus) must render a "
        f"language-aware heading, found {len(headings)}"
    )
    for vi_label, en_label in headings:
        assert vi_label == "Bình luận", (
            "the VI comments heading must read `Bình luận`, "
            f"got {vi_label!r}"
        )
        assert en_label == "Comments", (
            "the EN comments heading must stay byte-identical "
            f"(`Comments`), got {en_label!r}"
        )


# --- build guards (need Ruby; no browser) -----------------------------------

# The comments heading production render
# (`test_production_build_localizes_comments_heading`) lives in
# `test_giscus_comments.py`, which already owns a production build (#297).


def test_post_sidebar_tags_heading_matches_the_page_language(built_site):
    en_html = (built_site / EN_POST_REL).read_text(encoding="utf-8")
    assert "Chủ đề" not in _sidebar_headings(en_html), (
        "the English post sidebar must not carry the Vietnamese heading"
    )
    assert "Tags" in _sidebar_headings(en_html), (
        "the English post sidebar heading must stay `Tags`"
    )

    vi_html = (built_site / VI_POST_REL).read_text(encoding="utf-8")
    assert "Tags" not in _sidebar_headings(vi_html), (
        "the Vietnamese post sidebar must not carry the English heading"
    )
    assert "Chủ đề" in _sidebar_headings(vi_html), (
        "the Vietnamese post sidebar heading must read `Chủ đề`"
    )
