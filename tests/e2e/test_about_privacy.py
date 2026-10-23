"""Privacy-note guard (#284).

Both about pages (`/about/`, `/vi/about/`, shared `ref: about`) carry a
short privacy section disclosing what the site stores and which third
parties see the reader: no first-party trackers, only the `lang`
language-preference cookie (#423), the theme
choice in this browser's `localStorage` (key `theme`), Giscus comments
(GitHub) on post pages, and Cloudflare edge processing (TLS, caching,
email obfuscation).

Static guards (no Ruby) cover the page source contract; build guards (need
Ruby, no browser) cover the rendered pages, including unchanged hreflang
alternates and canonicals.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_URL = "https://mingchen.id.vn"


def _body(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n.*?\n---\s*\n", text, re.S)
    assert match, f"{path} has no front matter"
    return text[match.end():]


# --- static guards (no Ruby, no browser) -------------------------------------


@pytest.mark.static
def test_en_about_source_has_privacy_section():
    body = _body(REPO_ROOT / "about.md")
    assert re.search(r"^##\s+Privacy\s*$", body, re.M), (
        "EN about needs a `## Privacy` section"
    )
    for token in ("localStorage", "`theme`", "Giscus", "Cloudflare", "`lang`"):
        assert token in body, f"EN privacy note must mention {token}"
    assert "cookie" in body.lower(), "EN privacy note must mention cookies"


@pytest.mark.static
def test_vi_about_source_has_privacy_section():
    body = _body(REPO_ROOT / "vi" / "about.md")
    assert re.search(r"^##\s+Quy.n ri.ng t", body, re.M), (
        "VI about needs a `## Quyen rieng tu` section"
    )
    for token in ("localStorage", "`theme`", "Giscus", "Cloudflare", "`lang`"):
        assert token in body, f"VI privacy note must mention {token}"
    assert "cookie" in body.lower(), "VI privacy note must mention cookie"


@pytest.mark.static
def test_about_pages_keep_shared_ref():
    for path in (REPO_ROOT / "about.md", REPO_ROOT / "vi" / "about.md"):
        front_matter = path.read_text(encoding="utf-8").split("---")[1]
        assert re.search(r"^ref:[ \t]*about[ \t]*$", front_matter, re.M), (
            f"{path} must keep `ref: about` so hreflang/switcher are untouched"
        )


# --- build guards (need Ruby; no browser) ------------------------------------


def _privacy_section(html, url):
    sections = [
        (m.group(1), m.group(2))
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2[^>]*>|\Z)", html, re.S | re.I)
    ]
    for heading, section in sections:
        text = re.sub(r"<[^>]+>", "", heading).strip().lower()
        if "privacy" in text or "riêng t" in text:
            return re.sub(r"<[^>]+>", " ", section)
    raise AssertionError(f"{url} renders no privacy section")


def _head_alternates(html):
    return dict(
        (hreflang, href)
        for hreflang, href in re.findall(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html
        )
    )


def _canonical(html):
    match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    assert match, "page renders no canonical link"
    return match.group(1)


def test_en_about_renders_privacy_section(built_site):
    html = (built_site / "about" / "index.html").read_text(encoding="utf-8")
    section = _privacy_section(html, "/about/").lower()
    for token in ("localstorage", "theme", "giscus", "cloudflare", "cookie"):
        assert token in section, f"/about/ privacy section must mention {token}"
    assert re.search(r"\blang\b", section), (
        "/about/ privacy section must name the `lang` preference cookie (#423)"
    )


def test_vi_about_renders_privacy_section(built_site):
    html = (built_site / "vi" / "about" / "index.html").read_text(encoding="utf-8")
    section = _privacy_section(html, "/vi/about/").lower()
    for token in ("localstorage", "theme", "giscus", "cloudflare", "cookie"):
        assert token in section, f"/vi/about/ privacy section must mention {token}"
    assert re.search(r"\blang\b", section), (
        "/vi/about/ privacy section must name the `lang` preference cookie (#423)"
    )


def test_about_hreflang_and_canonicals_unchanged(built_site):
    en_html = (built_site / "about" / "index.html").read_text(encoding="utf-8")
    vi_html = (built_site / "vi" / "about" / "index.html").read_text(encoding="utf-8")
    assert _head_alternates(en_html) == _head_alternates(vi_html), (
        "EN and VI about pages must advertise the same hreflang alternates"
    )
    assert _head_alternates(en_html).get("vi") == f"{SITE_URL}/vi/about/", (
        "EN about hreflang must still point at /vi/about/"
    )
    assert _canonical(en_html) == f"{SITE_URL}/about/", (
        "EN about canonical must stay /about/"
    )
    assert _canonical(vi_html) == f"{SITE_URL}/vi/about/", (
        "VI about canonical must stay /vi/about/"
    )
