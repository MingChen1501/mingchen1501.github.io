"""Guards for #144 (reader UX): no bare unlinked URLs in post sources.

Background: the Fedora migration post pasted an UbuntuHandbook URL as plain
text — not a link, not tappable on mobile. Both the EN post and its VI
counterpart now link it with human-readable text instead of the raw URL.

Guarded here:

- (static) no ``_posts/`` / ``_vi_posts/`` body contains a bare ``http(s)://``
  URL outside a markdown link/image (``[...](...)``) or an ``<...>`` autolink
  (front matter excluded).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POSTS_DIRS = [REPO_ROOT / "_posts", REPO_ROOT / "_vi_posts"]

LINK_RE = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
AUTOLINK_RE = re.compile(r"<https?://[^>]*>")
BARE_URL_RE = re.compile(r"https?://\S+")


def _body(path):
    """Post source without the YAML front matter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :]
    return text


def _bare_urls(path):
    body = LINK_RE.sub("", _body(path))
    body = AUTOLINK_RE.sub("", body)
    return BARE_URL_RE.findall(body)


@pytest.mark.static
@pytest.mark.parametrize(
    "post", sorted(p for d in POSTS_DIRS for p in d.glob("*.md")), ids=lambda p: p.name
)
def test_post_source_has_no_bare_urls(post):
    assert _bare_urls(post) == [], (
        f"{post.name} contains bare URL(s): {_bare_urls(post)} (#144)"
    )
