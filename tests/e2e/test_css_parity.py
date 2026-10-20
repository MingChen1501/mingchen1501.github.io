"""Guard for #174: the `custom-styles.scss` split must not change shipped CSS.

`_sass/minima/custom-styles.scss` used to be one 803-line partial; it is now
an index over `_sass/minima/custom/_*.scss`, with the repeated dimensions
hoisted into `custom/_variables.scss`. The split is behaviour-preserving by
construction, and these guards keep it that way:

- the index imports every partial in `custom/` exactly once, in the pinned
  cascade order (reordering silently reorders the cascade);
- the index carries no rules of its own — only comments and the import list;
- the hoisted variables keep the exact literals they replaced;
- the built `assets/css/style.css` is byte-identical to the pre-split build
  (pinned SHA-256; bump it only with an intentional visual change, and only
  after diffing the CSS to confirm the change is the intended one).
"""

import hashlib
import re
from pathlib import Path

import pytest

import conftest

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_DIR = REPO_ROOT / "_sass" / "minima" / "custom"

# Cascade order, first to last. The compiled stylesheet concatenates the
# partials in this order, so any reorder is a potential visual change.
EXPECTED_ORDER = (
    "variables",
    "layout",
    "tags",
    "post",
    "share",
    "lightbox",
    "reading-progress",
    "sidebar",
    "a11y",
    "header",
    "toc",
    "utilities",
    "tap-targets",
    "legibility",
    "theme-toggle",
    "list-thumbs",
    "search",
    "print",
)

# The exact literals the variables replaced (#174 evidence).
EXPECTED_VARIABLES = {
    "$two-column-breakpoint": "960px",
    "$wide-content-width": "1080px",
    "$post-sidebar-width": "240px",
    "$site-sidebar-width": "300px",
    "$pinned-sidebar-min-height": "740px",
    "$tap-target-minimum": "24px",
}

# SHA-256 of the built `assets/css/style.css` from the pre-split sources
# (dev and production builds emit identical bytes). See the module docstring
# before updating.
#
# #220 (dark mode): `minima.skin` switched `classic` -> `auto` and the
# `theme-toggle` partial was appended. Diffed old vs new before bumping: the
# only substitutions are static colours -> `var(--minima-*)` resolving to the
# identical light values (the skin's light `:root` confirms each one), so
# light mode renders unchanged; everything else is pure addition (dark
# variables, dark syntax tokens, the `data-theme` layer, toggle styles).
# #226 (list thumbnails): the `list-thumbs` partial was appended. Diffed old
# vs new before bumping: the only change is the additive `.post-list__item` /
# `.post-list__body` / `.post-thumb` block above (fixed 120x90 box with
# `object-fit: cover`); no existing rule moved, so every other page renders
# unchanged.
# #221 (offline search): the `search` partial was appended. Diffed old vs new
# before bumping: the only change is the additive `.search` / `.search__*`
# block at the end (form, input, results list, language badge); no existing
# rule moved, so every other page renders unchanged.
# #223 (image lightbox): the `lightbox` partial was inserted after `post`.
# Diffed old vs new before bumping: the only change is the additive
# `.lightbox*` overlay block plus the `.post-content img.lightbox-trigger`
# cursor/focus hints; no existing rule moved, so every other page renders
# unchanged. It sits before (not after) the legibility partial because the
# #148 guard scans everything past its own marker for height budgets, and
# the dialog image needs `max-height` to fit the viewport.
# #222 (share row): the `share` partial was inserted after `post` (the row
# lives at the end of the post column). Diffed old vs new before bumping:
# the only change is the additive `.share` / `.share__*` block (heading,
# wrapping control list, 44px pill buttons/links, `hidden`-wins rule for the
# native-share row, reserved-height status line); no existing rule moved,
# so every other page renders unchanged.
# #224 (reading progress): the `reading-progress` partial was inserted after
# `lightbox` (post-page enhancement cluster). Diffed old vs new before
# bumping: the only change is the additive `.reading-progress` /
# `.reading-progress__bar` / `.back-to-top` block (fixed 4px bar with a
# transparent track, fixed 44px pill, `hidden`-wins rules, reduced-motion
# pin); no existing rule moved, so every other page renders unchanged.
# #225 (print stylesheet): the `print` partial was appended last. Diffed old
# vs new before bumping: the only change is the additive `@media print`
# block (chrome hidden, single-column article, print typography, outbound
# link URLs, break-inside avoid, bounded images); no existing rule moved
# and screen media is untouched, so every screen render stays identical.
# #241 (dark contrast): three additive rules in the `theme-toggle` dark
# layer (lightbox-trigger focus outline, share/back-to-top hover border,
# share status color, all `$dm-brand-color-light`). Diffed old vs new
# before bumping: pure addition in both dark layers (`data-theme` and the
# no-JS fallback), no existing rule moved, so light mode is pixel-identical.
# #242 (dark-mode print legibility): additive rules inside the existing
# `@media print` block only (`color-scheme: light`, black plain code text,
# every Rouge token repinned to its readable light colour). Diffed old vs
# new before bumping: the only change is that additive print hunk; no
# existing rule moved and screen media is untouched, so every screen render
# stays identical.
# #244 (copy-link no-JS gating): additive `.share__fallback` /
# `.share__fallback-link` rules in the `share` partial only (the `noscript`
# plain-URL link). Diffed old vs new before bumping: the only change is
# that additive hunk; no existing rule moved, so every render stays
# identical.
# #245 (dark-aware placeholder): the pair-swap rules in the `list-thumbs`
# partial became single-tile rules (`.post-thumb__placeholder` with the
# light tile inlined, plus the `html[data-theme="dark"]` and
# `prefers-color-scheme` repaints with the dark tile inlined).
# Diffed old vs new before bumping: the only change is that hunk (the hidden
# twin is gone with its `display` rules); no other rule moved. Light mode is
# pixel-identical (the light tile inlines the exact old SVG bytes), and the
# placeholder stays out of `document.images`, so the visual-regression
# settle check goes green.
EXPECTED_CSS_SHA256 = "defc38c9eb9afe56551531a1e7260f9372377c40f430c0599037643c131eca34"


def _imported_partials():
    """Partial names in the order `custom-styles.scss` imports them."""
    index = conftest.CUSTOM_SCSS_INDEX.read_text(encoding="utf-8")
    names = []
    for block in re.finditer(r"@import\s+(.*?);", index, re.S):
        for item in block.group(1).split(","):
            name = item.strip().strip("\"'")
            if name.startswith("minima/custom/"):
                names.append(name[len("minima/custom/"):])
    return names


@pytest.mark.static
def test_index_imports_every_partial_once_in_cascade_order():
    on_disk = sorted(
        path.stem[1:] for path in CUSTOM_DIR.glob("_*.scss")
    )
    assert on_disk == sorted(EXPECTED_ORDER), (
        f"stray or missing partials in {CUSTOM_DIR.name}: {on_disk}"
    )
    assert _imported_partials() == list(EXPECTED_ORDER), (
        "the index must import every partial exactly once, in cascade order"
    )


@pytest.mark.static
def test_index_carries_no_rules_of_its_own():
    """The index is comments plus the import list; rules live in partials."""
    lines = conftest.CUSTOM_SCSS_INDEX.read_text(encoding="utf-8").splitlines()
    code = [
        line
        for line in lines
        if line.strip() and not line.strip().startswith("//")
    ]
    # One `@import` statement, possibly wrapped over several lines.
    assert "".join(code).startswith("@import"), (
        f"unexpected non-comment content in the index: {code[:3]}"
    )
    assert "".join(code).rstrip().endswith(";"), (
        "the index must hold a single @import statement"
    )


@pytest.mark.static
def test_variables_keep_the_original_dimensions():
    variables = (CUSTOM_DIR / "_variables.scss").read_text(encoding="utf-8")
    for name, value in EXPECTED_VARIABLES.items():
        assert f"{name}: {value};" in variables, (
            f"{name} must stay {value} — it replaced that literal everywhere"
        )


def test_built_stylesheet_is_byte_identical_to_the_pre_split_build(built_site):
    css = built_site / "assets" / "css" / "style.css"
    assert css.is_file(), "the build emitted no assets/css/style.css"
    digest = hashlib.sha256(css.read_bytes()).hexdigest()
    assert digest == EXPECTED_CSS_SHA256, (
        "the compiled stylesheet changed — diff it against the pre-split "
        "build before updating this hash"
    )
