"""Guards for #150: footer email link needs a stable accessible name.

The footer contact email in `_includes/footer.html` was a bare `mailto:`
link whose text is the raw address. Under Cloudflare Email Obfuscation the
visible text can become "[email protected]", which is what assistive
technology announces — the link had no stable accessible name. The link now
carries a localized `aria-label` naming the recipient ("Email <name>" /
"Gửi email cho <name>"), which contains no raw address so obfuscation cannot
rewrite it, while the visible text stays the plain address (works with JS
off) and the `mailto:` href is unchanged.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) assert the rendered footer on the EN and VI homes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FOOTER_INCLUDE = REPO_ROOT / "_includes" / "footer.html"


def _email_anchor(page_html, url):
    """The rendered `<a class="u-email" ...>` opening tag of a page."""
    match = re.search(r'<a class="u-email"[^>]*>', page_html)
    assert match, f"{url} renders no footer email link"
    return match.group(0)


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_email_link_carries_aria_label_not_text_only():
    html = FOOTER_INCLUDE.read_text(encoding="utf-8")
    anchor = re.search(r'<a class="u-email"[^>]*>', html)
    assert anchor, "footer.html renders no u-email link to judge"
    assert "aria-label=" in anchor.group(0), (
        "footer email link has no stable accessible name (#150): "
        f"{anchor.group(0)}"
    )


@pytest.mark.static
def test_email_label_is_localized_and_address_free():
    """The label must follow the page language and hold no raw address."""
    html = FOOTER_INCLUDE.read_text(encoding="utf-8")
    assert "Gửi email cho " in html, (
        "the Vietnamese email label must survive (#150)"
    )
    assert "page.lang" in html or "footer_lang" in html, (
        "footer.html must pick the email label by page language (#150)"
    )
    label_assigns = re.findall(
        r"{%-? assign email_label = '(.*?)'.*?-?%}", html
    )
    assert label_assigns, "footer.html assigns no email_label (#150)"
    for literal in label_assigns:
        assert "@" not in literal, (
            "the accessible name must not depend on the obfuscated "
            f"address text (#150): {literal!r}"
        )


@pytest.mark.static
def test_email_link_keeps_mailto_and_visible_address():
    """No contact-address change: mailto href and visible text survive."""
    html = FOOTER_INCLUDE.read_text(encoding="utf-8")
    assert "href=\"mailto:{{ site.author.email }}\"" in html, (
        "the email link must keep its mailto href (#150)"
    )
    assert ">{{ site.author.email }}</a>" in html, (
        "the visible footer text must stay the plain address (#150)"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def _assert_named_email(page_html, url, address, label):
    anchor = _email_anchor(page_html, url)
    assert f'href="mailto:{address}"' in anchor, (
        f"{url} footer email link must keep its mailto href (#150)"
    )
    found = re.search(r'aria-label="([^"]+)"', anchor)
    assert found and found.group(1).strip(), (
        f"{url} footer email link has no stable accessible name (#150): "
        f"{anchor}"
    )
    assert found.group(1) == label, (
        f"{url} footer email link must be labelled {label!r} (#150), "
        f"got {found.group(1)!r}"
    )
    assert "@" not in found.group(1), (
        f"{url} footer email label must not depend on the address "
        f"text (#150): {found.group(1)!r}"
    )
    link_text = re.search(
        r'<a class="u-email"[^>]*>(.*?)</a>', page_html, re.S
    )
    assert link_text and link_text.group(1).strip() == address, (
        f"{url} visible footer email must stay the plain address (#150)"
    )


def test_footer_email_link_has_accessible_name(built_site):
    address = "mingchen1501@gmail.com"
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    _assert_named_email(en_home, "/", address, "Email Tran Cong Minh")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    _assert_named_email(
        vi_home, "/vi/", address, "Gửi email cho Trần Công Minh"
    )
