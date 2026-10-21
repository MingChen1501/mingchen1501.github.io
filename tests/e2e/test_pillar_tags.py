"""Curated pillar tags with a cap and data-driven tag indexes (#344).

Owner decision: the homepage sidebar tag list shows curated pillars only
(`pillar: true` in `_data/tag_labels.yml`), sorted by `order` and capped at
6 with an "All topics" / "Tất cả chủ đề" link to the tag index; the
`/tags/` and `/vi/tags/` indexes are data-driven — every tag with at least
one published post renders (pillars first by `order`, the rest under
"More topics" / "Chủ đề khác" sorted by the localized label), so new tags
arrive without template edits.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted indexes and sidebar, including two
throwaway-content builds that prove the index grows with a brand-new tag
and the sidebar cap binds at 6 pillars — the cap build additionally opens
at 375px and 320px phone widths to pin the no-overflow acceptance at the
maximum width.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest
import yaml

import test_stylesheet_cache_version as _csv

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_LABELS = REPO_ROOT / "_data" / "tag_labels.yml"
SIDEBAR_INCLUDE = REPO_ROOT / "_includes" / "site-sidebar.html"
TAG_LABEL_PARTIAL = REPO_ROOT / "_includes" / "tag-label.html"
TAGS_INDEX = REPO_ROOT / "tags.md"
VI_TAGS_INDEX = REPO_ROOT / "vi" / "tags.md"

PILLAR_ORDER = {
    "backend-production": 1,
    "ai-agent": 2,
    "linux-tooling": 3,
    "doi-song": 4,
}

SIDEBAR_CAP = 6


def _read(path):
    return path.read_text(encoding="utf-8")


def _tag_labels():
    assert TAG_LABELS.is_file(), "_data/tag_labels.yml is missing"
    return yaml.safe_load(_read(TAG_LABELS)) or {}


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_tag_labels_declares_pillar_and_order_per_tag():
    labels = _tag_labels()
    assert set(PILLAR_ORDER) <= set(labels), (
        f"tag_labels.yml lost a pillar: missing {sorted(set(PILLAR_ORDER) - set(labels))}"
    )
    for key, entry in labels.items():
        assert isinstance(entry.get("pillar"), bool), (
            f"tag_labels.yml[{key}] must declare `pillar: true|false` (#344)"
        )
        assert isinstance(entry.get("order"), int), (
            f"tag_labels.yml[{key}] must declare an integer `order` (#344)"
        )
    # The four existing pillars keep their current presentation order.
    for key, order in PILLAR_ORDER.items():
        assert labels[key]["pillar"] is True, (
            f"tag_labels.yml[{key}] must stay a curated pillar"
        )
        assert labels[key]["order"] == order, (
            f"tag_labels.yml[{key}] must keep order {order}, "
            f"got {labels[key]['order']}"
        )
    # The fields are documented in the file header, not tribal knowledge.
    header = _read(TAG_LABELS).split("backend-production:")[0]
    assert "pillar" in header and "order" in header, (
        "_data/tag_labels.yml must document `pillar`/`order` in its header"
    )


@pytest.mark.static
def test_tag_label_partial_returns_curation_metadata():
    partial = _read(TAG_LABEL_PARTIAL)
    assert "tag_pillar" in partial, (
        "_includes/tag-label.html must return `tag_pillar` for the sidebar (#344)"
    )
    assert "tag_order" in partial, (
        "_includes/tag-label.html must return `tag_order` for the sidebar (#344)"
    )
    # Unknown keys degrade to non-pillar with the fallback order, so they
    # sort after every pillar and fall back to the localized label.
    assert re.search(r"tag_pillar.*\|\s*default:\s*false", partial), (
        "_includes/tag-label.html must default `tag_pillar` to false"
    )
    assert re.search(r"tag_order.*\|\s*default:\s*999", partial), (
        "_includes/tag-label.html must default `tag_order` to 999"
    )


@pytest.mark.static
def test_sidebar_renders_only_pillars_capped_at_six():
    html = _read(SIDEBAR_INCLUDE)
    # Pillar filter + order sort through the shared partial (the include
    # never reads `site.data.tag_labels` itself, #175).
    assert "tag_pillar == true" in html, (
        "the sidebar must keep only `pillar: true` tags (#344)"
    )
    assert "tag_order" in html, "the sidebar must sort pillars by `order` (#344)"
    assert "site.data.tag_labels" not in html
    assert f"limit: {SIDEBAR_CAP}" in html, (
        f"the sidebar pillar list must cap at {SIDEBAR_CAP} (#344)"
    )
    # The capped list always offers the way out to the full index.
    assert "All topics" in html, (
        'the sidebar must link "All topics" to the tag index (#344)'
    )
    assert "Tất cả chủ đề" in html, (
        'the sidebar must link "Tất cả chủ đề" to the tag index (#344)'
    )
    assert "sidebar-tags__all" in html
    assert "sidebar_tag_base | relative_url" in html


@pytest.mark.static
def test_tag_indexes_are_data_driven_with_more_topics_group():
    for index, heading in (
        (TAGS_INDEX, "More topics"),
        (VI_TAGS_INDEX, "Chủ đề khác"),
    ):
        html = _read(index)
        rel = index.relative_to(REPO_ROOT)
        assert "backend-production,ai-agent,linux-tooling,doi-song" not in html, (
            f"{rel} must not hardcode the pillar array (#344)"
        )
        assert 'assign pillars = "' not in html, (
            f"{rel} must not assign a hardcoded pillar list"
        )
        assert "4 topics" not in html and "4 chủ đề" not in html, (
            f"{rel} must not claim a fixed topic count (#344)"
        )
        # Pillars iterate the collections in `order`; the rest follow under
        # the more-topics group sorted by the localized label.
        assert "order" in html
        assert heading in html, (
            f"{rel} must group non-pillar tags under {heading!r} (#344)"
        )
        # The copy promises the curated-first arrangement.
        assert "pillar" in html.lower()


# --- build guards (need Ruby; no browser) -----------------------------------


def _sidebar_tags(html):
    """`(label, href)` of the sidebar tag rows in render order."""
    section = re.search(
        r'<ul class="sidebar-tags">(.*?)</ul>\s*<a class="sidebar-tags__all"',
        html,
        re.S,
    )
    assert section, "the sidebar tag list is missing from the build"
    return re.findall(
        r'<span class="tag-chip">(.*?)</span>.*?'
        r'<a class="sidebar-tag__more" href="([^"]+)"',
        section.group(1),
        re.S,
    )


def _index_groups(html):
    """`(label, href)` per tag-index list in render order, plus headings."""
    lists = re.findall(r'<ul class="tag-index">(.*?)</ul>', html, re.S)
    chips = [
        re.findall(
            r'<a class="tag-chip"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', ul, re.S
        )
        for ul in lists
    ]
    headings = re.findall(
        r'<h2 class="tag-index__subheading">(.*?)</h2>', html, re.S
    )
    return chips, headings


def _expected_pillar_labels(lang):
    labels = _tag_labels()
    field = "vi" if lang == "vi" else "en"
    ordered = sorted(PILLAR_ORDER, key=PILLAR_ORDER.__getitem__)
    return [labels[key][field] for key in ordered]


def test_sidebar_lists_pillars_in_order_with_all_topics_link(built_site):
    for rel, lang, base, all_topics in (
        ("index.html", "en", "/tags/", "All topics"),
        ("vi/index.html", "vi", "/vi/tags/", "Tất cả chủ đề"),
    ):
        html = (built_site / rel).read_text(encoding="utf-8")
        groups = _sidebar_tags(html)
        assert 0 < len(groups) <= SIDEBAR_CAP, (
            f"{rel}: the sidebar must list 1-{SIDEBAR_CAP} pillars, "
            f"got {len(groups)}"
        )
        assert [label for label, _ in groups] == _expected_pillar_labels(lang), (
            f"{rel}: the sidebar must list pillars in `order` "
            f"({[label for label, _ in groups]})"
        )
        for _, href in groups:
            assert href.startswith(base), (
                f"{rel}: sidebar tag link {href} escapes {base}"
            )
        assert f'href="{base}"' in html, (
            f"{rel}: the sidebar must link the tag index at {base}"
        )
        assert all_topics in html, (
            f"{rel}: the sidebar must offer the {all_topics!r} link (#344)"
        )


def test_tag_indexes_list_pillars_in_order_without_more_group(built_site):
    labels = _tag_labels()
    for rel, lang, base in (
        ("tags/index.html", "en", "/tags/"),
        ("vi/tags/index.html", "vi", "/vi/tags/"),
    ):
        field = "vi" if lang == "vi" else "en"
        slug_field = "slug_vi" if lang == "vi" else "slug_en"
        html = (built_site / rel).read_text(encoding="utf-8")
        chips, headings = _index_groups(html)
        assert headings == [], (
            f"{rel}: with no non-pillar tags the more-topics group must stay "
            f"hidden, got {headings}"
        )
        assert len(chips) == 1, f"{rel}: expected a single pillar list"
        ordered = sorted(PILLAR_ORDER, key=PILLAR_ORDER.__getitem__)
        assert [(label, href) for href, label in chips[0]] == [
            (labels[key][field], f"{base}{labels[key][slug_field]}/")
            for key in ordered
        ], f"{rel}: the index must list pillars in `order` (#344)"


# --- throwaway-content builds: the index grows, the cap binds ------------


def _build_mutated_site(tmp_path, name, mutate):
    """Copy the repo, apply ``mutate(source)``, build it, return the dest."""
    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip("`bundle` not found: this guard rebuilds the site with Ruby")
    source = tmp_path / f"{name}-src"
    destination = tmp_path / f"{name}-site"
    for path in (source, destination):
        if path.exists():
            shutil.rmtree(path)
    shutil.copytree(
        REPO_ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", "_site", ".jekyll-cache", ".sass-cache", ".bundle", "vendor",
            "tests", ".ao", ".opencode", "__pycache__", ".pytest_cache",
        ),
    )
    mutate(source)
    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(source),
        env=_csv._bundler_env(source),
        capture_output=True,
        text=True,
        timeout=conftest.BUILD_TIMEOUT_S,
    )
    assert result.returncode == 0, (
        f"{name} build failed ({result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    return destination


_EN_POST = """---
layout: post
lang: en
ref: {ref}
author: Ming Chen
title: "{title}"
tags: [{tags}]
description: "{title} (throwaway #344 fixture)."
---

Throwaway fixture post for #344: a brand-new tag must reach the tag index
without template edits.
"""

_VI_POST = """---
layout: post
lang: vi
ref: {ref}
date: {date}
author: Ming Chen
title: "{title}"
tags: [{tags}]
description: "{title} (fixture tạm cho #344)."
---

Bài fixture tạm cho #344: tag mới phải xuất hiện trên trang index mà không
cần sửa template.
"""


def _mutate_new_more_tags(source):
    """Two non-pillar tags whose raw keys sort opposite their labels, plus
    one tag with no data-file entry at all (label/slug fall back to the
    canonical key)."""
    labels_path = source / "_data" / "tag_labels.yml"
    labels = yaml.safe_load(labels_path.read_text(encoding="utf-8"))
    labels["zz-apple"] = {
        "en": "Apple Picking",
        "vi": "Ăn sáng",
        "slug_en": "zz-apple",
        "slug_vi": "zz-apple",
        "description_en": "Apple picking: a non-pillar topic fixture (#344).",
        "description_vi": "Hái táo: fixture chủ đề ngoài pillar (#344).",
        "pillar": False,
        "order": 50,
    }
    labels["aa-zebra"] = {
        "en": "Zebra Crossing",
        "vi": "Đêm muộn",
        "slug_en": "aa-zebra",
        "slug_vi": "aa-zebra",
        "description_en": "Zebra crossings: a non-pillar topic fixture (#344).",
        "description_vi": "Vạch ngựa vằn: fixture chủ đề ngoài pillar (#344).",
        "pillar": False,
        "order": 51,
    }
    labels_path.write_text(
        yaml.safe_dump(labels, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (source / "_posts" / "2026-10-20-pillar-fixture-more-topics.md").write_text(
        _EN_POST.format(
            ref="pillar-fixture-more-topics",
            title="Pillar fixture: more topics",
            tags="zz-apple, aa-zebra, mystery-topic",
        ),
        encoding="utf-8",
    )
    (source / "_vi_posts" / "pillar-fixture-more-topics.md").write_text(
        _VI_POST.format(
            ref="pillar-fixture-more-topics",
            date="2026-10-20",
            title="Fixture pillar: chủ đề khác",
            tags="zz-apple, aa-zebra, mystery-topic",
        ),
        encoding="utf-8",
    )


def test_brand_new_tags_reach_the_more_topics_group(tmp_path):
    """A brand-new tag appears on both indexes immediately — under
    "More topics" / "Chủ đề khác", sorted by the localized label (never the
    raw key) — while the sidebar stays pillars-only."""
    destination = _build_mutated_site(tmp_path, "pillar-more", _mutate_new_more_tags)

    en_html = (destination / "tags" / "index.html").read_text(encoding="utf-8")
    en_chips, en_headings = _index_groups(en_html)
    assert en_headings == ["More topics"], (
        f"/tags/ must gain exactly the More topics group, got {en_headings}"
    )
    assert [label for _, label in en_chips[1]] == [
        "Apple Picking",
        "Zebra Crossing",
        "mystery-topic",
    ], "the More topics group must sort by the English label, not the raw key"
    assert "/tags/zz-apple/" in en_html and "/tags/aa-zebra/" in en_html
    assert "/tags/mystery-topic/" in en_html, (
        "a tag with no data-file entry must still render (key fallback)"
    )

    vi_html = (destination / "vi" / "tags" / "index.html").read_text(encoding="utf-8")
    vi_chips, vi_headings = _index_groups(vi_html)
    assert vi_headings == ["Chủ đề khác"], (
        f"/vi/tags/ must gain exactly the Chủ đề khác group, got {vi_headings}"
    )
    vi_labels = [label for _, label in vi_chips[1]]
    assert set(vi_labels) == {"Ăn sáng", "Đêm muộn", "mystery-topic"}, (
        f"the Chủ đề khác group must list the new tags, got {vi_labels}"
    )
    # Label sort, never raw-key sort: `zz-apple` ("Ăn sáng") precedes
    # `aa-zebra` ("Đêm muộn") although the raw key `aa-zebra` sorts first —
    # and Ă < Đ agrees with Vietnamese collation. (Liquid sorts bytes, so
    # the ASCII key fallback lists before the diacritic labels; real topic
    # labels are curated in the data file, where this edge does not arise.)
    assert vi_labels.index("Ăn sáng") < vi_labels.index("Đêm muộn")

    # The sidebar stays pillars-only at the same width.
    for rel, lang in (("index.html", "en"), ("vi/index.html", "vi")):
        groups = _sidebar_tags((destination / rel).read_text(encoding="utf-8"))
        assert [label for label, _ in groups] == _expected_pillar_labels(lang)


def _mutate_seven_pillars(source):
    """Grow the curated list to 7 pillars (orders 5-7), each with a post."""
    labels_path = source / "_data" / "tag_labels.yml"
    labels = yaml.safe_load(labels_path.read_text(encoding="utf-8"))
    for order, key in enumerate(
        ["cap-five", "cap-six", "cap-seven"], start=5
    ):
        labels[key] = {
            "en": f"Cap Fixture {order}",
            "vi": f"Cap Fixture {order}",
            "slug_en": key,
            "slug_vi": key,
            "description_en": f"Cap fixture pillar {order} (#344).",
            "description_vi": f"Pillar fixture giới hạn {order} (#344).",
            "pillar": True,
            "order": order,
        }
    labels_path.write_text(
        yaml.safe_dump(labels, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (source / "_posts" / "2026-10-20-pillar-fixture-cap.md").write_text(
        _EN_POST.format(
            ref="pillar-fixture-cap",
            title="Pillar fixture: cap",
            tags="cap-five, cap-six, cap-seven",
        ),
        encoding="utf-8",
    )
    (source / "_vi_posts" / "pillar-fixture-cap.md").write_text(
        _VI_POST.format(
            ref="pillar-fixture-cap",
            date="2026-10-20",
            title="Fixture pillar: giới hạn",
            tags="cap-five, cap-six, cap-seven",
        ),
        encoding="utf-8",
    )


def test_sidebar_cap_binds_at_six_pillars(tmp_path):
    """With 7 curated pillars the sidebar still renders 6 — in `order` —
    while the index lists all 7."""
    destination = _build_mutated_site(tmp_path, "pillar-cap", _mutate_seven_pillars)

    for rel, lang, base in (
        ("index.html", "en", "/tags/"),
        ("vi/index.html", "vi", "/vi/tags/"),
    ):
        groups = _sidebar_tags((destination / rel).read_text(encoding="utf-8"))
        assert len(groups) == SIDEBAR_CAP, (
            f"{rel}: 7 pillars must still render {SIDEBAR_CAP} sidebar rows, "
            f"got {len(groups)}"
        )
        assert "Cap Fixture 7" not in [label for label, _ in groups], (
            f"{rel}: the 7th pillar must not grow the sidebar"
        )
        assert f'href="{base}"' in (destination / rel).read_text(encoding="utf-8")

    en_chips, _ = _index_groups(
        (destination / "tags" / "index.html").read_text(encoding="utf-8")
    )
    assert [label for _, label in en_chips[0]][-3:] == [
        "Cap Fixture 5",
        "Cap Fixture 6",
        "Cap Fixture 7",
    ], "the index must list every pillar in `order`, uncapped"


@pytest.mark.parametrize("width", [375, 320])
def test_capped_sidebar_has_no_overflow_at_phone_widths(tmp_path, browser, width):
    """With 6 sidebar groups neither phone width overflows (#344)."""
    destination = _build_mutated_site(tmp_path, "pillar-overflow", _mutate_seven_pillars)
    with conftest._served(destination) as url:
        origin = urlparse(url).netloc
        context = browser.new_context(viewport={"width": width, "height": 900})
        try:
            page = context.new_page()
            page.route(
                "**/*",
                lambda route: route.continue_()
                if urlparse(route.request.url).netloc == origin
                else route.abort(),
            )
            for path in ("/", "/vi/"):
                response = page.goto(f"{url}{path}", wait_until="load")
                assert response is not None and response.status == 200
                page.wait_for_selector("aside.site-sidebar", state="attached")
                metrics = page.evaluate(
                    "() => ({scrollWidth: document.documentElement.scrollWidth, "
                    "innerWidth: window.innerWidth})"
                )
                assert metrics["scrollWidth"] <= metrics["innerWidth"], (
                    f"{path}: horizontal overflow at {width}px with 6 sidebar "
                    f"groups: {metrics}"
                )
        finally:
            context.close()
