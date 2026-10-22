"""Same-day post ordering guards (#398).

Owner bug report (2026-10-22): posts published on the same calendar day
rendered in title order instead of true publish-time order, because every
post's effective timestamp was midnight of its day — English posts carry the
date in the filename only (`YYYY-MM-DD-<slug>.md`, no front-matter `date:`)
and Vietnamese collection docs declare a day-only `date: YYYY-MM-DD` — so
same-day pairs shared identical timestamps and every `sort: "date"` surface
(home, tag pages, sidebar Latest fallback, both feeds, sitemap) fell back
to filename/collection order.

Convention (Option A from #398): same-day posts declare an explicit
front-matter `date: YYYY-MM-DD HH:MM +0700` matching true publish time
(merge time). The time is ordering metadata only — the UI keeps the
day-only display (`%b %-d, %Y`), so no template logic changes.

Guarded here:

- (static) no two published posts in the same language share an effective
  timestamp (day + declared time, midnight when no time is declared), so
  the next same-day pair cannot silently regress to title order;
- (static) the #398 pairs carry distinct in-day times in true publish
  order (merge history: #372 10:40 < #373 11:00 on 2026-10-20;
  #381 13:22 < #394 15:40 on 2026-10-22, +0700);
- (built) the newer post of each pair renders first on the affected
  surfaces: both homes, the shared `ai-agent` tag pages (the 2026-10-22
  pair shares no tag — different pillars), both feeds, and the sitemap
  emission order.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POSTS_DIR = REPO_ROOT / "_posts"
VI_POSTS_DIR = REPO_ROOT / "_vi_posts"

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
EN_NAME_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")
DATE_RE = re.compile(r"^date:\s*(\d{4}-\d{2}-\d{2})(?:[ \t]+(\d{2}:\d{2}))?", re.M)

# Newest-first expected order per same-day pair (slug stems), from the merge
# history in #398: the later merge is the newer publish.
EN_OCT20_NEWEST_FIRST = [
    "2026-10-20-lessons-opencode-subscription-multiple-coding-agents",
    "2026-10-20-two-weeks-running-ai-agent-team-blog",
]
EN_OCT22_NEWEST_FIRST = [
    "2026-10-22-back-to-linux-fundamentals",
    "2026-10-22-life-around-a-shrimp-pond",
]
VI_OCT20_NEWEST_FIRST = [
    "bai-hoc-mua-opencode-subscription-chay-nhieu-coding-agent",
    "hai-tuan-van-hanh-blog-cung-ai-agent-team",
]
VI_OCT22_NEWEST_FIRST = [
    "quay-lai-linux-can-ban",
    "cuoc-song-quanh-ao-tom",
]


def _read(path):
    return path.read_text(encoding="utf-8")


def _front_matter(path):
    match = FRONT_MATTER_RE.match(_read(path))
    return match.group(1) if match else ""


def _published(path):
    return not re.search(r"^published:\s*false", _front_matter(path), re.M)


def _effective_timestamp(posts_dir, path):
    """(day, time) effective timestamp; undeclared time means midnight.

    English posts default to the filename day at 00:00; an explicit
    front-matter `date:` (day + optional `HH:MM`) overrides it. Vietnamese
    collection docs always declare `date:`. The site is single-timezone
    (all explicit times are +0700), so the zone suffix is not part of the
    comparison key.
    """
    front_matter = _front_matter(path)
    match = DATE_RE.search(front_matter)
    if match:
        return (match.group(1), match.group(2) or "00:00")
    if posts_dir == POSTS_DIR:
        name_match = EN_NAME_RE.match(path.name)
        assert name_match, f"{path.name} carries no date in its filename"
        return (f"{name_match.group(1)}-{name_match.group(2)}-{name_match.group(3)}", "00:00")
    raise AssertionError(f"{path.name} declares no `date:` for its permalink")


def _timestamps(posts_dir):
    return {
        path.stem: _effective_timestamp(posts_dir, path)
        for path in sorted(posts_dir.glob("*.md"))
        if _published(path)
    }


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_no_duplicate_effective_timestamps_within_a_language():
    """Two published posts in one language must never share an effective
    timestamp — identical timestamps are what collapsed same-day order to
    title order (#398)."""
    for posts_dir, lang in ((POSTS_DIR, "en"), (VI_POSTS_DIR, "vi")):
        seen = {}
        for stem, stamp in sorted(_timestamps(posts_dir).items()):
            assert stamp not in seen, (
                f"{lang}: `{stem}` and `{seen[stamp]}` share the effective "
                f"timestamp {stamp[0]} {stamp[1]} — declare distinct "
                f"`date: YYYY-MM-DD HH:MM +0700` times so same-day posts "
                f"sort by true publish time (#398)"
            )
            seen[stamp] = stem


@pytest.mark.static
def test_same_day_pairs_follow_true_publish_order():
    """The #398 pairs pin distinct in-day times matching merge history."""
    en = _timestamps(POSTS_DIR)
    vi = _timestamps(VI_POSTS_DIR)
    for newest_first, stamps in (
        (EN_OCT20_NEWEST_FIRST, en),
        (EN_OCT22_NEWEST_FIRST, en),
        (VI_OCT20_NEWEST_FIRST, vi),
        (VI_OCT22_NEWEST_FIRST, vi),
    ):
        newer, older = newest_first
        assert stamps[newer] > stamps[older], (
            f"`{newer}` {stamps[newer]} must be newer than `{older}` "
            f"{stamps[older]} so it sorts first (#398)"
        )
        assert stamps[newer][0] == stamps[older][0], (
            f"`{newer}` and `{older}` must stay on the same calendar day "
            f"(the time is ordering metadata; the UI shows the day only)"
        )


# --- built guards (need Ruby) ----------------------------------------------


def _en_url(stem):
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    return f"/{stem[:10].replace('-', '/')}/{slug}.html"


def _vi_url(stem, day):
    return f"/vi/{day.replace('-', '/')}/{stem}.html"


def _assert_newer_first(html, newer_url, older_url, surface):
    newer_at = html.find(f'href="{newer_url}"')
    if newer_at == -1:
        newer_at = html.find(newer_url)
    older_at = html.find(f'href="{older_url}"')
    if older_at == -1:
        older_at = html.find(older_url)
    assert newer_at != -1, f"{surface} is missing the newer post {newer_url}"
    assert older_at != -1, f"{surface} is missing the older post {older_url}"
    assert newer_at < older_at, (
        f"{surface} lists the older same-day post first "
        f"({older_url} before {newer_url}); same-day posts must sort by "
        f"true publish time, newest first (#398)"
    )


def test_built_home_lists_newer_same_day_post_first(built_site):
    """`/` and `/vi/` (page 1 holds both pairs) render newest-first."""
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    for newer, older in (
        (EN_OCT22_NEWEST_FIRST[0], EN_OCT22_NEWEST_FIRST[1]),
        (EN_OCT20_NEWEST_FIRST[0], EN_OCT20_NEWEST_FIRST[1]),
    ):
        _assert_newer_first(en_home, _en_url(newer), _en_url(older), "`/`")
    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    for newer, older, day in (
        (VI_OCT22_NEWEST_FIRST[0], VI_OCT22_NEWEST_FIRST[1], "2026-10-22"),
        (VI_OCT20_NEWEST_FIRST[0], VI_OCT20_NEWEST_FIRST[1], "2026-10-20"),
    ):
        _assert_newer_first(
            vi_home, _vi_url(newer, day), _vi_url(older, day), "`/vi/`"
        )


def test_built_tag_pages_list_newer_same_day_post_first(built_site):
    """Tag pages sharing a same-day pair render newest-first.

    Only the 2026-10-20 pair shares a tag (`ai-agent`, both languages):
    the 2026-10-22 posts sit in different pillars (`linux-tooling` vs
    `doi-song`), so no tag page holds both — their order is covered by
    the home, feed, and sitemap guards.
    """
    cases = (
        (Path("tags") / "ai-agent" / "index.html",
         _en_url(EN_OCT20_NEWEST_FIRST[0]),
         _en_url(EN_OCT20_NEWEST_FIRST[1])),
        (Path("vi") / "tags" / "ai-agent" / "index.html",
         _vi_url(VI_OCT20_NEWEST_FIRST[0], "2026-10-20"),
         _vi_url(VI_OCT20_NEWEST_FIRST[1], "2026-10-20")),
    )
    for relative, newer_url, older_url in cases:
        html = (built_site / relative).read_text(encoding="utf-8")
        _assert_newer_first(html, newer_url, older_url, f"`/{relative.parent}/`")


def test_built_feeds_emit_newer_same_day_entry_first(built_site):
    """`feed.xml` (jekyll-feed) and `vi/feed.xml` emit newest-first."""
    en_feed = (built_site / "feed.xml").read_text(encoding="utf-8")
    for newer, older in (
        (EN_OCT22_NEWEST_FIRST[0], EN_OCT22_NEWEST_FIRST[1]),
        (EN_OCT20_NEWEST_FIRST[0], EN_OCT20_NEWEST_FIRST[1]),
    ):
        _assert_newer_first(en_feed, _en_url(newer), _en_url(older), "`/feed.xml`")
    vi_feed = (built_site / "vi" / "feed.xml").read_text(encoding="utf-8")
    for newer, older, day in (
        (VI_OCT22_NEWEST_FIRST[0], VI_OCT22_NEWEST_FIRST[1], "2026-10-22"),
        (VI_OCT20_NEWEST_FIRST[0], VI_OCT20_NEWEST_FIRST[1], "2026-10-20"),
    ):
        _assert_newer_first(
            vi_feed, _vi_url(newer, day), _vi_url(older, day), "`/vi/feed.xml`"
        )


def test_built_sitemap_emits_newer_same_day_post_first(built_site):
    """`sitemap.xml` emits the newer same-day post before the older one."""
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    for newer, older in (
        (EN_OCT22_NEWEST_FIRST[0], EN_OCT22_NEWEST_FIRST[1]),
        (EN_OCT20_NEWEST_FIRST[0], EN_OCT20_NEWEST_FIRST[1]),
    ):
        _assert_newer_first(
            sitemap, _en_url(newer), _en_url(older), "`sitemap.xml`"
        )
    for newer, older, day in (
        (VI_OCT22_NEWEST_FIRST[0], VI_OCT22_NEWEST_FIRST[1], "2026-10-22"),
        (VI_OCT20_NEWEST_FIRST[0], VI_OCT20_NEWEST_FIRST[1], "2026-10-20"),
    ):
        _assert_newer_first(
            sitemap, _vi_url(newer, day), _vi_url(older, day), "`sitemap.xml`"
        )
