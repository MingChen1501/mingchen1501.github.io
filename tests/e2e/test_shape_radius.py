"""Guards for #389: one shared button shape language (radius tokens).

The audit found one mostly-deliberate system — icon-only floating/header
actions are circles, filter/language controls are pills, every text action
is an 8px rounded rectangle, small nested controls and inline surfaces sit
one step smaller at 4px — with four genuine outliers: square pager and
footer-social links (no radius at all), the 5px nav panel, and the 6px
copy-code/post-ToC boxes. The fix hoists the scale into `:root` custom
properties (`_sass/minima/custom/_variables.scss`) and points every
button-like class at them.

Guarded here (static, no build needed):

- the five tokens exist with the pinned literals;
- every `border-radius` in the custom partials and the vendored layout uses
  a token, except the three documented non-controls: the 3px code blocks
  (`_base.scss`, not button-like), the 1px ToC chevron segments
  (decorative), and the `0` reset on the thumbnail `img` (the 4px box above
  it clips the corners);
- each token is actually referenced by at least one button class, so dead
  tokens cannot linger;
- the previously-square pager and footer-social links now carry the text-
  action radius.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VARIABLES = REPO_ROOT / "_sass" / "minima" / "custom" / "_variables.scss"
CUSTOM_DIR = REPO_ROOT / "_sass" / "minima" / "custom"
LAYOUT = REPO_ROOT / "_sass" / "minima" / "_layout.scss"

EXPECTED_TOKENS = {
    "--radius-sm": "4px",
    "--radius-md": "8px",
    "--radius-lg": "12px",
    "--radius-pill": "999px",
    "--radius-circle": "50%",
}

# Non-token radii that are deliberately out of scope: value -> reason.
ALLOWED_LITERAL_RADII = {
    "3px": "code blocks in _base.scss are surfaces, not button-like controls",
    "1px": "ToC chevron bar segments are decorative, not controls",
    "0": "thumbnail img reset: the 4px .post-thumb box above clips the corners",
}


def _radius_values(text):
    return [value.strip() for value in re.findall(r"border-radius\s*:\s*([^;]+);", text)]


def _is_token(value):
    parts = value.split()
    return bool(parts) and all(
        part == "0" or re.fullmatch(r"var\(--radius-[a-z]+\)", part) for part in parts
    )


def test_radius_tokens_are_defined_with_pinned_literals():
    text = VARIABLES.read_text(encoding="utf-8")
    for token, literal in EXPECTED_TOKENS.items():
        assert f"{token}: {literal};" in text, (
            f"{token} must stay {literal} — it replaced that literal everywhere"
        )


def test_every_button_radius_uses_a_token():
    offenders = []
    sources = sorted(CUSTOM_DIR.glob("_*.scss")) + [LAYOUT]
    for path in sources:
        for value in _radius_values(path.read_text(encoding="utf-8")):
            if _is_token(value) or value in ALLOWED_LITERAL_RADII:
                continue
            offenders.append(f"{path.name}: border-radius: {value}")
    assert not offenders, (
        "ad-hoc radii cannot creep back — point these at the --radius-* "
        f"tokens in _variables.scss: {offenders}"
    )


def test_every_token_is_used_by_a_button_class():
    haystack = "\n".join(
        [path.read_text(encoding="utf-8") for path in CUSTOM_DIR.glob("_*.scss")]
        + [LAYOUT.read_text(encoding="utf-8")]
    )
    unused = [token for token in EXPECTED_TOKENS if f"var({token})" not in haystack]
    assert not unused, f"dead radius tokens (no button class uses them): {unused}"


@pytest.mark.static
def test_pager_and_footer_social_links_carry_the_text_action_radius():
    """The #389 square-link fix: pager and social links use --radius-md."""
    layout = LAYOUT.read_text(encoding="utf-8")
    assert layout.count("border-radius: var(--radius-md);") >= 3, (
        "the nav panel, the pager row and the footer social links must all "
        "use the text-action radius token"
    )
