"""Per-topic descriptions on the tag index pages (#140).

`_data/tag_labels.yml` carries a one-line `description_en` / `description_vi`
per topic; `/tags/` renders the English lines and `/vi/tags/` the Vietnamese
ones next to the chip/count. The wording reuses the individual tag page bodies
(`tags/*.md`, `vi/tags/*.md`), so the static guards pin the two together and
fail on drift.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) cover the emitted indexes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_LABELS = REPO_ROOT / "_data" / "tag_labels.yml"

PILLARS = ["backend-production", "ai-agent", "linux-tooling", "doi-song"]

# Tag page source per pillar and language: (english page, vietnamese page).
TAG_PAGES = {
    "backend-production": ("tags/backend-production.md", "vi/tags/backend-production.md"),
    "ai-agent": ("tags/ai-agent.md", "vi/tags/ai-agent.md"),
    "linux-tooling": ("tags/linux-tooling.md", "vi/tags/linux-tooling.md"),
    "doi-song": ("tags/life.md", "vi/tags/doi-song.md"),
}

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

# Phrases unique to one language, so a leak of the other language's copy is
# caught even though technical tags keep English words in both (#129).
EN_ONLY_PHRASES = [
    "running real systems",
    "everyday workflow",
    "lean and fast",
    "Everyday life:",
]
VI_ONLY_PHRASES = [
    "vận hành hệ thống thật",
    "luồng làm việc hằng ngày",
    "gọn và nhanh",
    "Đời sống:",
]


def _read(path):
    return path.read_text(encoding="utf-8")


def _tag_labels():
    assert TAG_LABELS.is_file(), "_data/tag_labels.yml is missing"
    return yaml.safe_load(_read(TAG_LABELS)) or {}


def _body(path):
    """Markdown body of a tag page with whitespace normalized to one line."""
    text = _read(REPO_ROOT / path)
    match = FRONT_MATTER_RE.match(text)
    body = text[match.end():] if match else text
    return re.sub(r"\s+", " ", body).strip()


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_every_pillar_has_a_one_line_description_per_language():
    labels = _tag_labels()
    assert set(PILLARS) <= set(labels), (
        f"tag_labels.yml lost a pillar: missing {sorted(set(PILLARS) - set(labels))}"
    )
    for key in PILLARS:
        for field in ("description_en", "description_vi"):
            desc = labels[key].get(field)
            assert isinstance(desc, str) and desc.strip(), (
                f"tag_labels.yml[{key}] is missing `{field}`"
            )
            assert "\n" not in desc.strip(), (
                f"tag_labels.yml[{key}][{field}] must be a one-line summary"
            )


@pytest.mark.static
def test_descriptions_reuse_the_tag_page_copy_without_drift():
    """The index wording must match the per-tag page bodies (#140)."""
    labels = _tag_labels()
    for key, (en_page, vi_page) in TAG_PAGES.items():
        assert labels[key]["description_en"].strip() == _body(en_page), (
            f"description_en for {key} drifted from {en_page}"
        )
        assert labels[key]["description_vi"].strip() == _body(vi_page), (
            f"description_vi for {key} drifted from {vi_page}"
        )


@pytest.mark.static
def test_tag_indexes_render_descriptions_from_tag_labels_yml():
    en_index = _read(REPO_ROOT / "tags.md")
    assert "description_en" in en_index, (
        "tags.md must render description_en from _data/tag_labels.yml"
    )
    assert "description_vi" not in en_index, (
        "tags.md must not touch the Vietnamese descriptions"
    )
    vi_index = _read(REPO_ROOT / "vi" / "tags.md")
    assert "description_vi" in vi_index, (
        "vi/tags.md must render description_vi from _data/tag_labels.yml"
    )
    assert "description_en" not in vi_index, (
        "vi/tags.md must not touch the English descriptions"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def _descriptions(html):
    return [
        text.strip()
        for text in re.findall(
            r'<span class="tag-index__desc">(.*?)</span>', html, re.S
        )
    ]


def _published_tags(posts_dir):
    """Canonical tag keys used by published posts in ``posts_dir``."""
    tags = set()
    for path in sorted(posts_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONT_MATTER_RE.match(text)
        front_matter = match.group(1) if match else ""
        if re.search(r"^published:\s*false\s*$", front_matter, re.M):
            continue
        inline = re.search(r"^tags:\s*\[(.*?)\]", front_matter, re.M)
        if inline:
            tags.update(
                t.strip().strip("'\"")
                for t in inline.group(1).split(",")
                if t.strip()
            )
    return tags


def _expected_descriptions(lang):
    """Descriptions the index must render: one per published tag that
    declares one in `_data/tag_labels.yml` (#344: the index lists tags
    with posts, not a hardcoded pillar count)."""
    posts_dir = REPO_ROOT / "_vi_posts" if lang == "vi" else REPO_ROOT / "_posts"
    labels = _tag_labels()
    return {
        labels[key][f"description_{lang}"]
        for key in _published_tags(posts_dir)
        if key in labels and labels[key].get(f"description_{lang}")
    }


def test_english_index_lists_the_published_descriptions(built_site):
    html = (built_site / "tags" / "index.html").read_text(encoding="utf-8")
    descs = _descriptions(html)
    expected = _expected_descriptions("en")
    assert len(descs) == len(expected), (
        f"/tags/ must list one description per published tag, got {descs}"
    )
    for desc in expected:
        assert desc in descs, f"/tags/ is missing the description {desc!r}"
    for phrase in VI_ONLY_PHRASES:
        assert phrase not in html, (
            f"/tags/ must not leak Vietnamese copy ({phrase!r})"
        )


def test_vietnamese_index_lists_the_published_descriptions(built_site):
    html = (built_site / "vi" / "tags" / "index.html").read_text(encoding="utf-8")
    descs = _descriptions(html)
    expected = _expected_descriptions("vi")
    assert len(descs) == len(expected), (
        f"/vi/tags/ must list one description per published tag, got {descs}"
    )
    labels = _tag_labels()
    for desc in expected:
        assert desc in descs, (
            f"/vi/tags/ is missing the description {desc!r}"
        )
    for phrase in EN_ONLY_PHRASES:
        assert phrase not in html, (
            f"/vi/tags/ must not leak English copy ({phrase!r})"
        )


def test_tag_index_chips_and_urls_are_unchanged(built_site):
    en_html = (built_site / "tags" / "index.html").read_text(encoding="utf-8")
    for href, label in (
        ("/tags/backend-production/", "Backend Production"),
        ("/tags/ai-agent/", "AI Agent"),
        ("/tags/linux-tooling/", "Linux Tooling"),
        ("/tags/life/", "Life"),
    ):
        assert f'href="{href}"' in en_html, f"/tags/ lost its chip link to {href}"
        assert label in en_html, f"/tags/ lost its chip label {label!r}"
    vi_html = (built_site / "vi" / "tags" / "index.html").read_text(encoding="utf-8")
    for href, label in (
        ("/vi/tags/backend-production/", "Backend Production"),
        ("/vi/tags/ai-agent/", "AI Agent"),
        ("/vi/tags/linux-tooling/", "Linux Tooling"),
        ("/vi/tags/doi-song/", "Đời sống"),
    ):
        assert f'href="{href}"' in vi_html, (
            f"/vi/tags/ lost its chip link to {href}"
        )
        assert label in vi_html, f"/vi/tags/ lost its chip label {label!r}"
