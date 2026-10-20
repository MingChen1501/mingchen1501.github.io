"""Guards for #255: every `target="_blank"` anchor must carry `rel="noopener"`.

Two footer anchors in `_includes/social.html` opened in a new tab without
`rel="noopener"`, handing the opened page a `window.opener` reference
(reverse-tabnabbing vector). `rel="me"` does not imply `noopener`, and the
feed subscribe link had no `rel` at all. The share-intent links in
`_includes/share.html` already carried `rel="noopener noreferrer"`.

Guarded here:

- static (no Ruby): every `target="_blank"` anchor in `_includes/`
  and `_layouts/` carries `noopener` in its `rel` token list
  (the tracked standalone `fullmonth/` invitation page was removed
  in #294, so it is no longer guarded here);
- static: the social profile links keep `rel="me"` (combined as
  `rel="me noopener"`) and the feed link keeps opening in a new tab with
  `rel="noopener"` (no `noreferrer`, so no referrer-policy change);
- built (needs Ruby, no browser): the rendered EN/VI homes and a post
  page per language open their blank targets without an opener
  reference, and the footer links still open in a new tab.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCIAL_INCLUDE = REPO_ROOT / "_includes" / "social.html"
SHARE_INCLUDE = REPO_ROOT / "_includes" / "share.html"

SOURCE_HTML_DIRS = (REPO_ROOT / "_includes", REPO_ROOT / "_layouts")

ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE | re.DOTALL)
BLANK_TARGET_RE = re.compile(r"""target\s*=\s*(["']?)_blank\1""", re.IGNORECASE)
REL_RE = re.compile(r"""rel\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")


def _anchors_without_noopener(html):
    """Anchors opening a new tab whose `rel` list lacks `noopener`."""
    offenders = []
    for match in ANCHOR_RE.finditer(html):
        anchor = match.group(0)
        if not BLANK_TARGET_RE.search(anchor):
            continue
        rel = REL_RE.search(anchor)
        tokens = rel.group(2).split() if rel else []
        if "noopener" not in tokens:
            offenders.append(" ".join(anchor.split()))
    return offenders


def _source_html_files():
    files = []
    for directory in SOURCE_HTML_DIRS:
        files.extend(sorted(directory.glob("*.html")))
    return files


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_blank_targets_carry_noopener_in_sources():
    """The `#255` grep stays clean: no bare `target=_blank` in sources."""
    files = _source_html_files()
    assert files, "expected source HTML files to guard"
    for path in files:
        assert path.is_file(), f"{path} is missing"
        offenders = _anchors_without_noopener(
            path.read_text(encoding="utf-8")
        )
        assert not offenders, (
            f"{path.relative_to(REPO_ROOT)} opens a new tab without "
            f"`rel=noopener` (#255): {offenders}"
        )


@pytest.mark.static
def test_social_links_keep_rel_me_with_noopener():
    """Identity signal stays; opener protection is added, not swapped in."""
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    profile = re.search(r"<a\b[^>]*rel=\"([^\"]*)\"[^>]*>", html)
    assert profile, "social.html renders no profile link to judge"
    tokens = profile.group(1).split()
    assert "me" in tokens, (
        f"social profile links must keep `rel=me` (#255): {profile.group(0)}"
    )
    assert "noopener" in tokens, (
        f"social profile links must add `noopener` (#255): {profile.group(0)}"
    )


@pytest.mark.static
def test_feed_link_still_opens_in_a_new_tab_with_noopener_only():
    """Same-origin feed link: opener protection, no referrer-policy change."""
    html = SOCIAL_INCLUDE.read_text(encoding="utf-8")
    anchors = ANCHOR_RE.findall(html)
    feed = [a for a in anchors if "feed" in a.lower() or "absolute_url" in a]
    assert feed, "social.html renders no feed link to judge"
    for anchor in feed:
        assert BLANK_TARGET_RE.search(anchor), (
            f"the feed link must still open in a new tab (#255): {anchor}"
        )
        rel = REL_RE.search(anchor)
        assert rel and "noopener" in rel.group(2).split(), (
            f"the feed link must carry `rel=noopener` (#255): {anchor}"
        )
        assert "noreferrer" not in (rel.group(2).split() if rel else []), (
            f"the feed link must not change referrer policy (#255): {anchor}"
        )


@pytest.mark.static
def test_share_intent_links_stay_unchanged():
    """`share.html` was already correct; the fix must not regress it."""
    html = SHARE_INCLUDE.read_text(encoding="utf-8")
    intents = [
        anchor
        for anchor in ANCHOR_RE.findall(html)
        if BLANK_TARGET_RE.search(anchor)
    ]
    assert len(intents) == 3, (
        f"expected the three share-intent links, found {len(intents)}"
    )
    for anchor in intents:
        rel = REL_RE.search(anchor)
        assert rel and {"noopener", "noreferrer"} <= set(rel.group(2).split()), (
            f"share-intent link must keep `rel=noopener noreferrer`: {anchor}"
        )


# --- build guards (need Ruby; no browser) -----------------------------------


def _assert_blank_targets_have_noopener(page_html, url):
    anchors = ANCHOR_RE.findall(page_html)
    blanks = [a for a in anchors if BLANK_TARGET_RE.search(a)]
    assert blanks, f"{url} renders no new-tab link to judge"
    offenders = _anchors_without_noopener(page_html)
    assert not offenders, (
        f"{url} opens a new tab without `rel=noopener` (#255): {offenders}"
    )
    return blanks


def test_built_pages_open_blank_targets_without_an_opener(built_site):
    pages = {
        "index.html": "/",
        "vi/index.html": "/vi/",
        EN_POST_REL.as_posix(): f"/{EN_POST_REL.as_posix()}",
        VI_POST_REL.as_posix(): f"/{VI_POST_REL.as_posix()}",
    }
    for rel, url in pages.items():
        path = built_site / rel
        assert path.is_file(), f"{rel} is missing from the built site"
        blanks = _assert_blank_targets_have_noopener(
            path.read_text(encoding="utf-8"), url
        )
        assert blanks, f"{url} renders no new-tab link to judge"


def test_built_footer_links_still_open_in_a_new_tab(built_site):
    """The fix adds `rel`, it must not drop `target=_blank` (#255)."""
    for rel, url, feed_label in (
        ("index.html", "/", "Subscribe to syndication feed"),
        ("vi/index.html", "/vi/", "Đăng ký nhận tin RSS"),
    ):
        html = (built_site / rel).read_text(encoding="utf-8")
        match = re.search(
            r'<ul class="social-media-list">.*?</ul>', html, re.S
        )
        assert match, f"{url} renders no footer social list"
        social = match.group(0)
        anchors = [a for a in ANCHOR_RE.findall(social) if "href=" in a]
        assert anchors, f"{url} footer social list holds no links"
        for anchor in anchors:
            assert BLANK_TARGET_RE.search(anchor), (
                f"{url} footer link no longer opens in a new tab (#255): "
                f"{anchor}"
            )
        assert feed_label in social, (
            f"{url} footer feed link must keep its label {feed_label!r}"
        )

