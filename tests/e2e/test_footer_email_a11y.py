"""Guards for #150 (accessible name) and #213 (WCAG 2.5.3 fix).

The footer contact email in `_includes/footer.html` was a bare `mailto:`
link whose text is the raw address. Under Cloudflare Email Obfuscation the
visible text can become "[email protected]", which is what assistive
technology announces — the link had no stable accessible name. The link now
names the recipient in plain text ("Email <name>" /
"Gửi email cho <name>", no raw address in the label so obfuscation cannot
rewrite it) while the visible text stays the plain address (works with JS
off) and the `mailto:` href is unchanged.

The label ships as a visually-hidden span *inside* the link (#213), not as
an `aria-label`: `aria-label` would override the contents and reintroduce
the WCAG 2.5.3 Label-in-Name mismatch (the visible address would no longer
be part of the accessible name). With the in-link span the accessible name
is "<address> (<label>)", which contains the visible text and still names
the recipient when obfuscation rewrites the address.

Static guards (no Ruby) cover the source contract; build guards (need Ruby,
no browser) assert the rendered footer on the EN and VI homes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FOOTER_INCLUDE = REPO_ROOT / "_includes" / "footer.html"


def _email_link(page_html, url):
    """The rendered `<a class="u-email" ...>...</a>` of a page."""
    match = re.search(r'<a class="u-email"[^>]*>(.*?)</a>', page_html, re.S)
    assert match, f"{url} renders no footer email link"
    return match.group(0), match.group(1)


# --- static guards (no Ruby, no browser) ------------------------------------


@pytest.mark.static
def test_email_link_names_recipient_in_link_text_not_aria_label():
    """No `aria-label`: the name must come from the link contents (#213)."""
    html = FOOTER_INCLUDE.read_text(encoding="utf-8")
    anchor = re.search(r'<a class="u-email"[^>]*>', html)
    assert anchor, "footer.html renders no u-email link to judge"
    assert "aria-label" not in anchor.group(0), (
        "footer email link must not carry aria-label: it would hide the "
        "visible address from the accessible name (WCAG 2.5.3, #213)"
    )
    assert re.search(
        r'<span class="visually-hidden">\s*\(\{\{\s*email_label\s*\}\}\)\s*</span>',
        html,
    ), "footer email link must name the recipient in a visually-hidden "
    "span inside the link (#150, #213)"


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
    assert ">{{ site.author.email }}<span" in html, (
        "the visible footer text must stay the plain address (#150)"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def _assert_named_email(page_html, url, address, label):
    anchor, inner = _email_link(page_html, url)
    assert f'href="mailto:{address}"' in anchor, (
        f"{url} footer email link must keep its mailto href (#150)"
    )
    assert "aria-label" not in anchor, (
        f"{url} footer email link must not carry aria-label "
        f"(WCAG 2.5.3, #213): {anchor}"
    )
    assert "@" not in label, (
        f"{url} footer email label must not depend on the address "
        f"text (#150): {label!r}"
    )
    assert inner.startswith(address), (
        f"{url} visible footer email must stay the plain address (#150): "
        f"{inner!r}"
    )
    rest = inner[len(address):]
    assert re.fullmatch(
        r'\s*<span class="visually-hidden">\s*\('
        + re.escape(label)
        + r'\)\s*</span>\s*',
        rest,
    ), (
        f"{url} footer email link must name the recipient {label!r} in a "
        f"hidden span after the address (#150, #213): {inner!r}"
    )


def test_footer_email_link_has_accessible_name(built_site):
    address = "mingchen1501@gmail.com"
    en_home = (built_site / "index.html").read_text(encoding="utf-8")
    _assert_named_email(en_home, "/", address, "Email Tran Cong Minh")

    vi_home = (built_site / "vi" / "index.html").read_text(encoding="utf-8")
    _assert_named_email(
        vi_home, "/vi/", address, "Gửi email cho Trần Công Minh"
    )
