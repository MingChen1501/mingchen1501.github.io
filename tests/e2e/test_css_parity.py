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
    "motion",
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
# #221 (offline search) then #342 (its removal): the `search` partial was
# appended, then deleted with the whole feature (owner decision 2026-10-21:
# drop the static client-side index). Diffed old vs new before bumping: the
# only change is the removal of the additive `.search` / `.search__*` block
# (form, input, results list, language badge); no existing rule moved, so
# every other page renders unchanged.
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
# #275 (syntax-split): the Rouge token rules left the main stylesheet for
# the conditional `assets/css/syntax.css` companion. Diffed old vs new
# before bumping with a rule-multiset compare (old single-file rules ==
# new main + companion rules, order-insensitive): zero rules lost, zero
# gained — the split moved the 319 screen `.highlight*` token rules
# (light, OS-preference dark, and both `data-theme` layers) verbatim into
# the companion, keeping the structural `div.highlight` /
# `code.highlighter-rouge` rules and the `@media print` repins in the main
# sheet. Code pages load both sheets (same token, same relative order),
# code-free pages load the slimmed main sheet only; every screen render
# stays identical, so no visual baseline changes.
# #335 is gone with the feature (#342 deleted the search page, its
# `<noscript>` fallback, and the `search` partial that carried the
# `.search__noscript` selector).
# #341 (tag index summaries): the `legibility` partial gained one additive
# rule inside the existing `max-width: $on-medium` block (`.tag-index__desc`
# at 15px / 1.5, joining the dimmed count rows per the #148 lift). Diffed
# old vs new before bumping: the only change is that 4-line hunk; no
# existing rule moved, so every other page renders unchanged. The two 375px
# tag-index visual baselines (EN/VI) were refreshed from the CI
# `visual-fresh-chromium` artifact; all other baselines are pixel-identical.
# #344 (curated pillar tags): the `sidebar` partial gained one additive
# rule (`.sidebar-tags__all` footer link below the capped pillar list, in
# a dimmed tone with a hover/focus darkening).
# Diffed old vs new before bumping: the only change is that additive hunk;
# no existing rule moved, so every other page renders unchanged. The
# sidebar/home/tag visual baselines that include the sidebar or the
# data-driven tag index were refreshed from the CI
# `visual-fresh-chromium` artifact; all other baselines are pixel-identical.
# #378 (sidebar tag-index link deduplication): the `sidebar` partial lost the
# now-unused `.sidebar__heading-link` rule (with its hover/focus), the
# `tap-targets` partial lost its minimum for that selector, and the dark
# `theme-toggle` override lost the matching hover/focus lines — the plain
# topics heading keeps no link styling. Diffed old vs new before bumping:
# only those hunks change; the heading itself keeps its row style, so the
# refresh decision follows the same CI-artifact rule as #344.
# #345 (ToC nested disclosure + scroll-spy): the `toc` partial changed with
# the collapsed-default visual contract — branches now render nested `<ul>`s
# inside their parent `<li>` (real descendants, so a collapsed branch hides
# its subtree), each branch row is a link plus a disclosure toggle (24px
# target, CSS chevron rotating on `aria-expanded`, instant under
# reduced-motion), h4 rows indent a second step, and the active-row rule
# gained a semibold weight next to the theme-aware link colour and the
# layout-free 3px bar (the transparent border above still reserves its
# space, so only the marked row itself changes width — siblings never
# shift). Diffed old vs new before bumping: the only changes are those
# additive nested-disclosure rules; no existing rule moved, so every render
# without a marked ToC row stays identical. Post pages with a ToC render
# the outer `<details open>` with all branches collapsed on load (JS
# progressive enhancement — the static markup ships every level expanded),
# which changes post screenshots, but the visual baselines pin ToC-less
# posts only, so no baseline refreshes.
# #377 (phone ToC row model): the `toc` partial gained a phone-only block
# (below the 960px two-column breakpoint). Diffed old vs new before
# bumping: the only hunk is that addition (bounded 50vh scrollable inline
# nav, 44px summary, single-line ellipsis rows, 32px toggles, 12/20px
# h3/h4 indents); no existing rule moved, so desktop and no-JS renders
# stay identical and the ToC-less visual baselines need no refresh. (A
# `scroll-margin-top` guard was prototyped and reverted: it parked anchor
# jumps on the scroll-spy marking boundary.)
# #383 (phone ToC floating button + sheet): the `toc` partial gained the
# additive `.toc-fab` / `.toc-sheet` block (fixed 48px bottom-left button
# with its progress ring, bottom sheet with backdrop + dialog panel, the
# moved nav keeping the bounded single-line row model inside the sheet,
# desktop hide, reduced-motion pin, JS-only `html.toc-fab-on` inline
# hide), and the `print` partial hides both controls. Diffed old vs new
# before bumping: pure addition, no existing rule moved; the button and
# sheet render only on ToC posts (the visual baselines pin ToC-less posts
# only) and stay `hidden`/desktop-none there, so no baseline refresh.
# #395 (phone FAB stuck focus ring): the `toc` partial gained two additive
# `.toc-fab` focus rules (`:focus:not(:focus-visible)` draws no outline so
# taps leave no browser-default ring; `:focus-visible` keeps the 3px/3px
# geometry in the theme-swapping link accent). Diffed old vs new before
# bumping: pure addition, no existing rule moved; the outline only paints
# on keyboard focus, so all baselined renders stay pixel-identical.
# #400 (phone FAB toggle-close ring): the `toc` partial gained one additive
# `.toc-fab.toc-fab--no-focus-ring:focus-visible` rule drawing no outline
# while the script's pointer-close mark is present (some engines match
# `:focus-visible` for the programmatic focus return after a tap). Diffed
# old vs new before bumping: pure addition, no existing rule moved; the
# mark is only ever set on a pointer close, so all baselined renders stay
# pixel-identical.
# #402 (motion polish for the FAB and controls): the `custom-variables`
# hook gained the shared `$motion-*` duration/easing tokens (fast 120ms,
# base 180ms, slow 240ms, ease-out, FAB-only spring), the new `motion`
# partial (imported first) holds the five shared keyframes plus the single
# global reduced-motion guard, and every listed control gained
# transform/opacity-only transitions/enter-animations through those tokens
# (FAB press/hover + sheet open, ring/bar value smoothing, back-to-top
# appear, theme/nav icon swaps, copy-code success pop, lightbox open +
# image fade, share/chip/pager/post-card press/hover), with a print
# kill-switch for all motion. Diffed old vs new before bumping: pure
# addition except four tokenized substitutions (chevron 0.15s, ring/bar
# 0.1s, theme 0.2s -> the matching tokens); no existing rule moved, every
# animation ends at its resting box, and reduced-motion/print render
# instantly — so all baselined renders stay pixel-identical and no baseline
# refresh is needed.
# #401 (draggable FAB experiment): the `toc` partial gained `touch-action`
# plus unselectable label text on `.toc-fab` and two additive rules
# (`.toc-fab--right` snapping the button to the right edge above
# back-to-top, `.toc-fab--dragging` dropping the spring while a drag is
# under way). Diffed old vs new before bumping: pure addition, no
# existing rule moved; the button renders only on ToC posts (the visual
# baselines pin ToC-less posts only) and stays `hidden`/desktop-none
# there, so no baseline refresh is needed.
# #384 (first-paint nav flash): the phone panel's hide moved under `html.js`
# and the show rule gained the `html.no-js` override. Diffed old vs new
# before bumping: pure selector scoping, no declaration moved; settled
# renders stay pixel-identical (the panel was collapsed post-JS before and
# stays collapsed), so no baseline refresh is needed.
# #387 (Resume + full CV split): the `print` partial gained two additive
# rules inside the existing `@media print` block (`.resume-jump` screen
# navigation never prints; the `#cv` section starts on a fresh sheet).
# Diffed old vs new before bumping: the only hunk is that addition; no
# existing rule moved and screen media is untouched, so every screen render
# stays identical and no baseline refresh is needed for this hunk.
EXPECTED_CSS_SHA256 = "8ea4078bb0ae3c1716a280f2e8e2b2dda4409557f3d00d21593a6aae674c2265"

# SHA-256 of the built `assets/css/syntax.css` companion from the same
# sources (dev and production builds emit identical bytes). See the #275
# note above before updating.
EXPECTED_SYNTAX_CSS_SHA256 = "d88cd5ea93eb1012cab1505ffa1f5d6ead7485bd7467e350f98e2f8ed0828370"


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


def test_built_syntax_stylesheet_is_byte_identical_to_the_split_build(built_site):
    """The #275 companion sheet is pinned too: any token drift shows here."""
    css = built_site / "assets" / "css" / "syntax.css"
    assert css.is_file(), "the build emitted no assets/css/syntax.css"
    digest = hashlib.sha256(css.read_bytes()).hexdigest()
    assert digest == EXPECTED_SYNTAX_CSS_SHA256, (
        "the compiled syntax companion changed — diff it against the "
        "split build before updating this hash"
    )
