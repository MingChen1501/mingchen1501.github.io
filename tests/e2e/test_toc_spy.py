"""ToC nested disclosure with scroll-spy auto-expand (#345).

`_includes/post-toc.html` renders a NESTED list (h2 > h3 > h4, children
`<ul>`s as real descendants of their parent `<li>`) starting fully
expanded with plain anchors, so the ToC works with JS disabled; the
post-only `assets/js/toc-spy.js` progressively enhances it: on load every
branch collapses (default view H2 only), the scroll-spy marks the row
being read (`aria-current="location"` on both copies, styled in
`custom/_toc.scss` with the theme-aware link colour plus a bar and a
semibold weight — never colour-only) and auto-expands the active branch
plus its ancestors, collapsing auto-opened branches on leave unless the
reader pinned them by hand (`data-manual`).

Guarded here:

- static (no Ruby, no browser): the script stays vanilla, small, and
  dependency-free; it observes headings with `IntersectionObserver`,
  falls back to a passive scroll listener, derives the scroll-spy offset
  from the measured header height when sticky/fixed (the header is
  statically pinned non-sticky), marks exactly one row per mount with
  `aria-current="location"`, collapses per-branch lists on load (and, on
  phone layouts only, starts the inline copy as one summary row — #377),
  never moves the viewport (the bounded phone panel only nudges its own
  `scrollTop`), never touches `tabindex`/focus, adds no smooth
  scrolling (so `prefers-reduced-motion` needs no handling); the tag lives
  in the post-only gate after the helper with its build token; the active
  style keys off the attribute with a theme-safe colour plus non-colour
  indicators; indentation follows nested level classes through h4;
- built (needs Ruby, no browser): both mounts render expanded with the
  localized label, EN and VI; the harness page (a scratch Jekyll source
  exercising the REAL include at h2/h3/h4 depth, since no published post
  uses h3 yet) nests children inside their parent branch with
  mount-scoped control ids;
- browser (needs Ruby + a browser): branches start collapsed (H2 only);
  scrolling to an h3/h4 auto-expands its branch chain and marks that row;
  leaving collapses auto-opened branches but keeps manually pinned ones;
  per-branch buttons toggle on Enter/Space without moving focus; an h4
  hides with its collapsed parent; the existing live-scroll
  exactly-one-`aria-current` assertion still holds on the long EN post;
  with JS disabled every level stays visible with working anchors;
- phone (needs Ruby + a browser, #383): at 320/360/375/414px the inline
  copy gives way to a floating button with a reading-progress ring (the
  no-JS fallback keeps the #377/#382 collapsed inline list); the button
  opens a bottom sheet holding the moved nav, scrolled to the marked row;
  the sheet shuts on its button, Esc, the backdrop, or a row tap (which
  jumps and hands focus back); the ring tracks the article range while
  shut; the button never overlaps back-to-top; desktop behaviour is
  unchanged.
"""

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest
from playwright.sync_api import expect

import test_post_only_js

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "js" / "toc-spy.js"
TOC_SCSS = REPO_ROOT / "_sass" / "minima" / "custom" / "_toc.scss"
LAYOUT_SCSS = REPO_ROOT / "_sass" / "minima" / "_layout.scss"
POST_LAYOUT = REPO_ROOT / "_layouts" / "post.html"
SUB_FOOTER = test_post_only_js.SUB_FOOTER

SCRIPT_PATH = "/assets/js/toc-spy.js"
# The scroll-spy ships on post pages only (#345): keep it small. Nested
# disclosure grew the script from ~5KB (flat highlight only) to ~8.6KB;
# the phone FAB + sheet + article-range ring (#383) reuses the same
# observer and rAF tick and grows it to ~14KB.
MAX_SCRIPT_BYTES = 15 * 1024

EN_LONG_POST = "/2022/12/25/explaining-the-internet.html"
VI_LONG_POST = "/vi/2022/12/25/gioi-thieu-ve-internet.html"
BUILD_TIMEOUT_S = 300


def _read(path):
    return Path(path).read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_the_spy_script_exists_and_stays_vanilla():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the ToC scroll-spy ships on post pages only: keep it under "
        f"{MAX_SCRIPT_BYTES} bytes (#345)"
    )
    assert "import " not in text and "require(" not in text, (
        "the scroll-spy must not depend on anything (#345)"
    )
    assert "SiteUtils.onReady" in text, (
        "the scroll-spy must run through the shared DOM-ready helper "
        "after site-utils.js (#246, #345)"
    )


@pytest.mark.static
def test_the_spy_observes_headings_with_a_passive_scroll_fallback():
    text = _read(SCRIPT)
    assert "IntersectionObserver" in text, (
        "the scroll-spy must observe headings instead of polling (#345)"
    )
    assert re.search(
        r"addEventListener\(\s*['\"]scroll['\"].*passive", text, re.S
    ), "the scroll fallback must stay passive (#345)"
    assert "requestAnimationFrame" in text, (
        "scroll handling must be rAF-throttled (#345)"
    )


@pytest.mark.static
def test_the_spy_derives_its_offset_from_the_measured_header():
    text = _read(SCRIPT)
    assert "getBoundingClientRect().height" in text, (
        "the scroll-spy offset must derive from the measured header "
        "height when the header is sticky/fixed (#345)"
    )
    assert "EDGE_PX" in text, (
        "a small slack must remain for the non-sticky header (#345)"
    )
    # The measured branch only matters if the header ever becomes sticky:
    # the stylesheet pins it non-sticky, so the slack branch rules today.
    layout = _read(LAYOUT_SCSS)
    header = re.search(r"\.site-header\s*\{(.*?)\}", layout, re.S)
    assert header, "the `.site-header` block is gone (#345)"
    assert "position: relative;" in header.group(1), (
        "the header must stay non-sticky for the slack offset (#345)"
    )
    assert "sticky" not in header.group(1) and "fixed" not in header.group(1), (
        "a sticky/fixed header would overlap the scrolled-to section "
        "without a matching offset change (#345)"
    )


@pytest.mark.static
def test_the_spy_marks_one_row_per_mount_with_aria_current():
    text = _read(SCRIPT)
    assert 'aria-current", "location"' in text or (
        "'aria-current', 'location'" in text
    ), 'the active row must use aria-current="location" (#345)'
    assert "removeAttribute('aria-current')" in text or (
        'removeAttribute("aria-current")' in text
    ), "a newly active row must unmark the previous one (#345)"
    assert ".post-toc__nav" in text, (
        "both mounts must be marked together (#345)"
    )


@pytest.mark.static
def test_the_spy_collapses_branches_and_hides_the_phone_inline_for_the_fab():
    text = _read(SCRIPT)
    # Strip the header comment: the assertions below pin runtime behaviour,
    # while the comment is allowed to narrate the design.
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    # Collapsing is per-branch runtime state: the script hides children
    # lists and flips their toggles (#345). On phone layouts the INLINE
    # copy goes away entirely (#383: the open list fills most of the first
    # viewport): the script flags `html.toc-fab-on` (a JS-only class, so
    # no-JS readers keep the inline collapsed ToC from #382), moves that
    # mount's nav node into the sheet slot — the same nodes, so the spy
    # keeps marking them with the same observer and tick — and reveals the
    # floating button. The desktop copy stays open.
    assert ".post-toc__toggle" in code, (
        "collapsing must drive the per-branch disclosure toggles (#345)"
    )
    assert ".hidden" in code or "hidden =" in code, (
        "collapsed branches must hide their children list (#345)"
    )
    assert ".post-toc-mount--inline" in code, (
        "only the inline (phone) copy may give way to the button (#383)"
    )
    assert "toc-fab-on" in code, (
        "the inline mount must hide behind a JS-only class so the no-JS "
        "fallback keeps rendering (#383)"
    )
    assert "appendChild" in code, (
        "the sheet must reuse the inline nav node, not a second copy "
        "with its own subscription (#383)"
    )
    assert "getComputedStyle" in code and "=== 'none'" in code, (
        "the phone handoff must key off the visible mount, not a "
        "hardcoded breakpoint (#377, #383)"
    )
    # The default anchor jump is instant; nothing animated is ever added
    # here, so prefers-reduced-motion needs no handling in this script
    # (the ring transition is pinned in CSS instead, #383).
    assert "smooth" not in code, (
        "the scroll-spy must not animate scrolling (reduced motion, #345)"
    )
    # The page itself never moves: no viewport-scrolling calls. The one
    # exception is the sheet panel, which nudges its own moved nav's
    # `scrollTop` so the active row stays inside it (#377, #383).
    assert "scrollIntoView" not in code, (
        "the scroll-spy must never scroll anything into view (#345)"
    )
    assert re.search(r"scrollTo\s*\(", code) is None, (
        "the scroll-spy must never move the viewport itself (#345)"
    )
    assert "nav.scrollTop" in code, (
        "the active row must be kept inside the sheet via the moved nav's "
        "own scrollTop (#383)"
    )
    # Keyboard stays native: real buttons toggle on Enter/Space and links
    # stay plain anchors. Focus moves only across the dialog handoff (open
    # puts focus on the close button, close returns it to the button);
    # marking and auto-expansion never move focus.
    assert "tabindex" not in code.lower() and "tabIndex" not in code, (
        "the scroll-spy must leave the ToC tab order alone (#345)"
    )
    assert ".focus()" in code, (
        "the sheet open/close handoff must move focus (#383)"
    )
    assert "activeElement" not in code, (
        "focus tracking must not sniff the active element (#383)"
    )
    for name in (
        "function mark(",
        "function syncBranches(",
        "function apply(",
        "function fabProgress(",
    ):
        start = code.index(name)
        nxt = code.find("\n    function ", start + 1)
        body = code[start:nxt if nxt != -1 else len(code)]
        assert ".focus(" not in body, (
            f"{name} must never move focus: only the sheet open/close "
            "handoff may (#345, #383)"
        )


@pytest.mark.static
def test_the_fab_ring_tracks_the_article_range_not_the_document():
    """Progress reads 0% above the body and 100% at its end (#383)."""
    text = _read(SCRIPT)
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    assert ".post-content" in code, (
        "the ring must range over the article body, not the document (#383)"
    )
    assert "offsetHeight" in code, (
        "the range must derive from the article's own height (#383)"
    )
    assert "innerHeight" in code, (
        "the range must discount the viewport like any scrollable range "
        "(#383)"
    )
    assert "data-toc-ring" in code, (
        "the ring node must be addressed through its data hook (#383)"
    )
    assert "strokeDashoffset" in code, (
        "the ring must publish progress as a circle dash offset (#383)"
    )
    assert "data-toc-fab-label" in code and "data-toc-fab-base" in code, (
        "the same value must reach AT as label text in the page language "
        "(#383)"
    )
    assert "Math.round" in code, (
        "the text equivalent must report whole percent points (#383)"
    )
    # The ring is decorative: the svg ships `aria-hidden` in the layout
    # (asserted with the markup below), so the script must not add a
    # second live name of its own.
    assert "aria-label" not in code or "data-label-show" in code, (
        "the ring update must go through label text, not a redundant "
        "aria-label (#383)"
    )


@pytest.mark.static
def test_the_spy_keeps_a_single_observer_with_a_passive_schedule():
    """The sheet reuses the one observer and tick: no second cost (#383)."""
    text = _read(SCRIPT)
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    assert code.count("new IntersectionObserver") == 1, (
        "exactly one observer may watch the headings: the sheet reuses it "
        "(#383)"
    )
    assert "data-toc-slot" in code, (
        "the sheet must take the moved inline nav, never a second list "
        "(#383)"
    )


@pytest.mark.static
def test_the_sheet_handoff_is_keyboard_and_pointer_complete():
    """Button, Esc, backdrop and close button; expanded state exposed."""
    text = _read(SCRIPT)
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    assert "aria-expanded" in code, (
        "the button must expose the sheet state (#383)"
    )
    assert "aria-controls" in code or "data-toc-fab" in code, (
        "the button must own the sheet (#383)"
    )
    assert "'Escape'" in code or '"Escape"' in code, (
        "Esc must shut the sheet (#383)"
    )
    assert "data-toc-backdrop" in code, (
        "a backdrop tap must shut the sheet (#383)"
    )
    assert "data-toc-close" in code, (
        "a close button must shut the sheet (#383)"
    )


@pytest.mark.static
def test_the_fab_markup_lives_in_the_post_layout_only():
    """Hidden button + sheet, localized, post pages with a ToC only (#383)."""
    layout = _read(POST_LAYOUT)
    assert "show_toc" in layout and "data-toc-fab" in layout, (
        "the button must render only where the ToC renders (#383)"
    )
    for needle in (
        'class="toc-fab" hidden',
        'data-toc-fab aria-expanded="false" aria-controls="toc-sheet"',
        'class="toc-sheet" hidden',
        'data-toc-sheet id="toc-sheet"',
        'role="dialog" aria-modal="true"',
        'data-toc-slot',
        'data-toc-backdrop',
        'data-toc-close',
        'data-toc-ring',
        "toc-fab__ring",
        'aria-hidden="true"',
        "visually-hidden",
        "data-toc-fab-base",
        "On this page",
        "Trong bài này",
    ):
        assert needle in layout, (
            f"the post layout must ship `{needle}` (#383)"
        )
    for template in sorted((REPO_ROOT / "_layouts").glob("*.html")):
        if template.name == "post.html":
            continue
        assert "toc-fab" not in _read(template), (
            f"{template.relative_to(REPO_ROOT)} must not render the phone "
            "ToC button: post pages only (#383)"
        )


@pytest.mark.static
def test_the_fab_styles_float_bottom_left_with_safe_area():
    """48px target bottom-left (back-to-top owns right), sheet + ring (#383)."""
    scss = _read(TOC_SCSS)
    assert ".toc-fab[hidden]" in scss and ".toc-sheet[hidden]" in scss, (
        "the `hidden` attribute must win so no-JS readers see neither "
        "control (#383)"
    )
    assert "position: fixed" in scss, (
        "both controls must float above the page (#383)"
    )
    assert "env(safe-area-inset-" in scss, (
        "the button and sheet must clear phone safe areas (#383)"
    )
    assert "width: 48px" in scss and "height: 48px" in scss, (
        "the button must clear 44px with margin (#383)"
    )
    assert "left:" in scss and "z-index: 950" in scss, (
        "the button sits bottom-left above content but below the sheet "
        "(back-to-top keeps bottom-right, #383)"
    )
    assert "z-index: 1000" in scss, (
        "the sheet must layer above the button (#383)"
    )
    assert "max-height: 75vh" in scss, (
        "the sheet panel must never fill the viewport (#383)"
    )
    assert ".toc-sheet .post-toc__nav" in scss, (
        "the moved nav keeps its own bounded scroll inside the sheet (#383)"
    )
    assert "stroke-dasharray: 125.66" in scss, (
        "the ring geometry must match the script constant (#383)"
    )
    assert scss.count("prefers-reduced-motion") >= 2, (
        "the ring transition needs its own reduced-motion pin next to the "
        "chevron one (#383)"
    )


@pytest.mark.static
def test_the_spy_pins_manual_branches_against_auto_collapse():
    text = _read(SCRIPT)
    assert "data-manual" in text, (
        "an explicit toggle must pin its branch until the next explicit "
        "toggle, so auto-collapse leaves it alone (#345)"
    )
    assert "data-auto" in text, (
        "only auto-opened branches may auto-collapse on leave (#345)"
    )


@pytest.mark.static
def test_the_spy_script_is_gated_to_post_pages():
    """The tag lives in the post-layout conditional with its token (#345)."""
    html = _read(SUB_FOOTER)
    gate = re.search(r"\{%-?\s*if page\.layout == 'post'\s*-?%\}", html)
    assert gate, "the post-layout gate in sub-footer.html is gone (#345)"
    gated = html[gate.end():html.index("endif", gate.end())]
    assert f"{SCRIPT_PATH}?v=" in gated, (
        "the toc-spy script tag must live inside the post-layout "
        "conditional (#345)"
    )
    assert gated.index("/assets/js/reading-progress.js?v=") < gated.index(
        f"{SCRIPT_PATH}?v="
    ), "toc-spy must load after reading-progress in document order (#345)"
    assert html.index("/assets/js/site-utils.js?v=") < html.index(
        f"{SCRIPT_PATH}?v="
    ), "toc-spy must load after the shared helper (#246, #345)"


@pytest.mark.static
def test_the_active_style_is_visible_in_both_themes_without_colour_only():
    scss = _read(TOC_SCSS)
    rule = re.search(
        r'\.post-toc__item a\[aria-current="location"\]\s*\{(.*?)\}',
        scss,
        re.S,
    )
    assert rule, (
        "the active style must key off the aria-current attribute (#345)"
    )
    body = rule.group(1)
    # `$link-base-color` compiles to `var(--minima-link-base-color)`, which
    # the skin swaps per theme: ~5.1:1 on the light background, ~5.4:1 on
    # the dark one (both over the 4.5:1 bar, measured 2026-10-21).
    assert "color: $link-base-color" in body, (
        "the active row must use the theme-aware link colour (#345)"
    )
    assert "border-left-color: $link-base-color" in body, (
        "the active row needs a non-colour indicator next to the colour "
        "(#345)"
    )
    # The refined spec pairs the colour with a semibold weight; the bar
    # costs no layout (the transparent border above reserves its space),
    # so activating a row never shifts its siblings.
    assert "font-weight: 600" in body, (
        "the active row must pair colour and bar with weight (#345)"
    )


@pytest.mark.static
def test_phone_inline_mount_uses_the_compact_bounded_row_model():
    """Phone row model (#377): audit 2026-10-22 proved the open inline
    list costs 510px / 73% of a 700px viewport on the 16-h2 EN post, wraps
    2 of 16 titles, and leaves the marked row above the viewport."""
    scss = _read(TOC_SCSS)
    phone = re.search(
        r"@include media-query\(\$two-column-breakpoint - 1px\)\s*\{(.*)",
        scss,
        re.S,
    )
    assert phone, (
        "the phone ToC rules must scope below the two-column breakpoint "
        "(#377)"
    )
    block = phone.group(1)
    # The expanded list is bounded with its own scroll, so the article
    # body starts higher and the panel never fills the viewport.
    assert "max-height: 50vh;" in block, (
        "the phone inline list must cap at half the viewport (#377)"
    )
    assert "overflow-y: auto;" in block, (
        "the capped phone list must scroll internally (#377)"
    )
    # One 44px summary row by default; rows truncate instead of wrapping.
    assert "min-height: 44px;" in block, (
        "the phone summary must clear 44px (#377)"
    )
    assert "text-overflow: ellipsis;" in block, (
        "phone rows must truncate with an ellipsis, not wrap (#377)"
    )
    assert "white-space: nowrap;" in block, (
        "single-line truncation needs no-wrap rows (#377)"
    )
    # Disclosure toggles clear 32px; indentation tightens to two steps.
    assert "min-width: 32px;" in block and "min-height: 32px;" in block, (
        "phone toggles must clear 32px (#377)"
    )
    assert "padding-left: 12px;" in block, (
        "phone h3 rows must indent one tight step (#377)"
    )
    assert "padding-left: 20px;" in block, (
        "phone h4 rows must indent a second tight step (#377)"
    )
    # Anchor arrivals need no guard: the header is static, so jumps land
    # fully visible (audit 2026-10-22: heading top 0 at every phone
    # width). A scroll-margin was prototyped and reverted: reserving
    # exactly the spy's 24px slack parks the heading on the marking
    # boundary, and sub-pixel rounding then marks the previous row.
    assert "scroll-margin" not in scss, (
        "no scroll margin on post headings: it would park jumps on the "
        "scroll-spy boundary (#377)"
    )


@pytest.mark.static
def test_nested_indentation_is_css_driven_per_level_class():
    scss = _read(TOC_SCSS)
    h3 = re.search(r"\.post-toc__item--h3\s*\{(.*?)\}", scss, re.S)
    assert h3 and "padding-left" in h3.group(1), (
        "h3 rows must indent one step via their level class (#345)"
    )
    h4 = re.search(r"\.post-toc__item--h4\s*\{(.*?)\}", scss, re.S)
    assert h4 and "padding-left" in h4.group(1), (
        "h4 rows must indent a second step: any level present nests "
        "correctly (#345)"
    )
    assert "overflow-wrap" in scss, (
        "long ToC titles must wrap instead of overflowing small phones "
        "(#345)"
    )


# --- harness: the real include at h2/h3/h4 depth (needs Ruby) ---------------


# No published post uses h3/h4 headings (checked 2026-10-21), so the
# nesting contract cannot be exercised on the real corpus. This scratch
# source renders the REAL `_includes/post-toc.html` over a fixed
# h2/h3/h4 sample (including an h4 directly under an h2 and a childless
# h2), with room to scroll between sections.
HARNESS_SECTIONS = (
    ("h2", "a-first", "First"),
    ("h3", "a-one", "One"),
    ("h4", "a-one-x", "Ex"),
    ("h3", "a-two", "Two"),
    ("h2", "b-second", "Second"),
    ("h2", "c-third", "Third"),
    ("h4", "c-orphan", "Orphan"),
)


def _harness_source(scratch):
    (scratch / "_includes").symlink_to(
        (REPO_ROOT / "_includes").resolve(), target_is_directory=True
    )
    js_dir = scratch / "js"
    js_dir.mkdir()
    for name in ("site-utils.js", "toc-spy.js"):
        shutil.copy(REPO_ROOT / "assets" / "js" / name, js_dir / name)
    sample = "".join(
        f'<{level} id="{hid}">{title}</{level}>'
        for level, hid, title in HARNESS_SECTIONS
    )
    body = "".join(
        f'<{level} id="{hid}">{title}</{level}>'
        '<div style="height:100vh" aria-hidden="true"></div>'
        for level, hid, title in HARNESS_SECTIONS
    )
    (scratch / "toc.html").write_text(
        "---\n---\n"
        '<div class="site-header">Harness</div>\n'
        "{%- capture harness_html -%}"
        + sample
        + "{%- endcapture -%}\n"
        '{%- include post-toc.html html=harness_html lang="en" '
        'mount="inline" -%}\n'
        '<main class="post-content">' + body + "</main>\n"
        '<script src="js/site-utils.js" defer></script>\n'
        '<script src="js/toc-spy.js" defer></script>\n',
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def harness_url(tmp_path_factory):
    """Serve a scratch Jekyll build of the real include at h2/h3/h4 depth."""
    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip(
            "`bundle` not found: the harness needs Ruby + `bundle install` "
            "(CI installs both in .github/workflows/e2e.yml)"
        )
    scratch = tmp_path_factory.mktemp("toc-harness-src")
    _harness_source(scratch)
    destination = tmp_path_factory.mktemp("toc-harness-build")
    result = subprocess.run(
        [bundle, "exec", "jekyll", "build",
         "--source", str(scratch), "--destination", str(destination)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_S,
    )
    if result.returncode != 0:
        pytest.fail(
            "`jekyll build` (harness) failed with exit code "
            f"{result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    with conftest._served(destination) as url:
        yield f"{url}/toc.html"


def test_harness_nests_children_inside_their_parent_branch(harness_url):
    """H4 support with nesting fidelity: real descendants, not a flat list."""
    import urllib.request

    html = urllib.request.urlopen(harness_url, timeout=30).read().decode()
    nav = re.search(
        r'<nav class="post-toc__nav"[^>]*>(.*?)</nav>', html, re.S
    )
    assert nav, "expected the harness ToC nav"
    nav_html = nav.group(1)
    # Nesting fidelity: tags balance, and the branch structure holds in
    # document order — the h3 sits inside the h2's `<li>` + children
    # `<ul>`, the h4 inside the h3's branch, leaves carry no toggle.
    assert nav_html.count("<ul") == nav_html.count("</ul>"), (
        "unbalanced ToC lists (#345)"
    )
    assert nav_html.count("<li") == nav_html.count("</li>"), (
        "unbalanced ToC items (#345)"
    )
    chain = [
        '<li class="post-toc__item post-toc__item--h2" data-level="2">',
        'href="#a-first"',
        'id="toc-inline-a-first-children"',
        'href="#a-one"',
        'id="toc-inline-a-one-children"',
        'href="#a-one-x"',
        "</ul>",
        "</li>",
        'href="#a-two"',
        "</ul>",
        "</li>",
        'href="#b-second"',
        "</li>",
        'id="toc-inline-c-third-children"',
        'href="#c-orphan"',
    ]
    pos = -1
    for token in chain:
        nxt = nav_html.find(token, pos + 1)
        assert nxt > pos, (
            f"ToC nesting broken at {token!r}: children must be real "
            f"descendants of their parent branch (#345)"
        )
        pos = nxt
    # An h4 directly under an h2 lands in that h2's children list.
    assert nav_html.index('href="#c-orphan"') > nav_html.index(
        'id="toc-inline-c-third-children"'
    ), "an h4 under an h2 must nest in that h2 branch (#345)"
    # Leaves carry no disclosure control; branches do, with mount-scoped
    # ids so the two mounts never share an element id.
    assert 'href="#b-second"' in nav_html
    leaf = re.search(
        r'<li class="post-toc__item post-toc__item--h2" data-level="2">'
        r'<div class="post-toc__row"><a href="#b-second">.*?</div></li>',
        nav_html,
        re.S,
    )
    assert leaf and "<button" not in leaf.group(0), (
        "a childless h2 must render no toggle (#345)"
    )
    controls = re.findall(r'aria-controls="(toc-inline-[^"]+)"', nav_html)
    assert controls, "expected branch toggles in the harness ToC (#345)"
    assert len(set(controls)) == len(controls), (
        "toggle control ids must be unique per mount (#345)"
    )
    for control in controls:
        assert f'id="{control}"' in nav_html, (
            f"toggle target {control} must exist (#345)"
        )


# --- emitted site (needs Ruby, no browser) ---------------------------------


@pytest.mark.parametrize(
    ("rel", "label"),
    [
        ("2022/12/25/explaining-the-internet.html", "On this page"),
        ("vi/2022/12/25/gioi-thieu-ve-internet.html", "Trong bài này"),
    ],
)
def test_long_posts_render_both_mounts_expanded(built_site, rel, label):
    page = built_site / rel
    assert page.is_file(), f"expected a built page at {rel}"
    html = page.read_text(encoding="utf-8")
    assert html.count('<details class="post-toc" open>') == 2, (
        f"{rel}: both ToC mounts render expanded on load (#345)"
    )
    assert '<details class="post-toc">' not in html.replace(
        '<details class="post-toc" open>', ""
    ), f"{rel}: no collapsed ToC copy may remain (#345)"
    # The static markup never hides anything: collapsing is runtime state
    # owned by toc-spy.js (no-JS contract).
    for mount in re.findall(
        r'<nav class="post-toc__nav"[^>]*>.*?</nav>', html, re.S
    ):
        # (`aria-hidden` on the chevrons is static decoration, not a
        # hidden subtree: match the attribute, not the substring.)
        assert re.search(r"\shidden(?:[\s=/>])", mount) is None, (
            f"{rel}: static ToC must not hide any level (#345)"
        )
        assert 'aria-expanded="true"' in mount or "<button" not in mount, (
            f"{rel}: static toggles start expanded (#345)"
        )
        # Every toggle target exists; every children list nests in a branch.
        for control in re.findall(r'aria-controls="([^"]+)"', mount):
            assert f'id="{control}"' in html, (
                f"{rel}: toggle target {control} is missing (#345)"
            )


# --- browser behaviour (needs Ruby + a browser) ------------------------------


@pytest.fixture()
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    browser_page = context.new_page()
    # Only the site's own files are fetched: third-party requests are aborted
    # so the run stays offline-safe.
    browser_page.route(
        "**/*",
        lambda route: (
            route.continue_()
            if urlparse(route.request.url).hostname in ("127.0.0.1", "localhost")
            else route.abort()
        ),
    )
    try:
        yield browser_page
    finally:
        context.close()


def _scroll_to_heading(page, heading_id, offset_px=10):
    """Put a heading just below the viewport top, instantly.

    The spy counts a heading as current once its top reaches the
    viewport top (plus a small slack), so the target must land
    within that band — not 100px down the viewport.
    """
    page.evaluate(
        "const h = document.getElementById("
        f"{heading_id!r});"
        " window.scrollTo(0, h.getBoundingClientRect().top"
        " + window.scrollY - " + str(offset_px) + ");"
    )


def _settle_layout(page):
    """Wait out late image boxes before measuring heading positions.

    Aborted or slow images resize their boxes after load; any scroll
    measured before that goes stale when the headings move. Waiting for
    every image to finish keeps the scroll targets fresh.
    """
    page.wait_for_function(
        "() => Array.from(document.images).every(i => i.complete)",
        timeout=15_000,
    )


def _js_click(page, selector):
    """Click without moving the viewport.

    Playwright's `locator.click()` scrolls the target into view first,
    which would move the scroll-spy off the section under test; a scripted
    click exercises the same toggle handler without the scroll.
    """
    page.evaluate(
        f"document.querySelector({selector!r}).click()"
    )


def test_branches_start_collapsed_with_h2_only_visible(harness_url, page):
    """Default view: H2 only; deeper levels start collapsed (#345)."""
    page.goto(harness_url, wait_until="load")
    toggles = page.locator(".post-toc__toggle")
    assert toggles.count() == 3
    for index in range(toggles.count()):
        expect(toggles.nth(index)).to_have_attribute(
            "aria-expanded", "false"
        )
    h2_links = page.locator(".post-toc__item--h2 > .post-toc__row > a")
    for index in range(h2_links.count()):
        expect(h2_links.nth(index)).to_be_visible()
    for href in ("#a-one", "#a-one-x", "#a-two", "#c-orphan"):
        expect(page.locator(f'.post-toc__item a[href="{href}"]')).to_be_hidden()


def test_scroll_auto_expands_the_active_branch_and_ancestors(
    harness_url, page
):
    """Scrolling to an h4 opens its h2+h3 chain and marks that row (#345)."""
    page.goto(harness_url, wait_until="load")
    _scroll_to_heading(page, "a-one-x")
    page.wait_for_function(
        """() => document.querySelector(
          '.post-toc__nav a[aria-current="location"]'
        )?.getAttribute('href') === '#a-one-x'""",
        timeout=10_000,
    )
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )
    expect(page.locator('[aria-controls="toc-inline-a-one-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )
    expect(page.locator('.post-toc__item a[href="#a-one-x"]')).to_be_visible()
    marked = page.locator(
        ".post-toc__nav a[aria-current='location']"
    ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
    assert marked == ["#a-one-x"], (
        f"exactly one row must be marked, got {marked} (#345)"
    )


def test_leaving_collapses_auto_branches_but_keeps_pinned_ones(
    harness_url, page
):
    """Pin-vs-auto: manual intent wins until the next explicit toggle."""
    page.goto(harness_url, wait_until="load")
    # Pin the first branch open by hand, then scroll far away.
    _js_click(page, '[aria-controls="toc-inline-a-first-children"]')
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )
    _scroll_to_heading(page, "c-orphan")
    page.wait_for_function(
        """() => document.querySelector(
          '.post-toc__nav a[aria-current="location"]'
        )?.getAttribute('href') === '#c-orphan'""",
        timeout=10_000,
    )
    # The untouched c branch auto-opened; the pinned a branch stayed open.
    expect(page.locator('[aria-controls="toc-inline-c-third-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )
    # The auto-opened c branch collapses again on leave; the pinned one
    # does not.
    _scroll_to_heading(page, "b-second")
    page.wait_for_function(
        """() => document.querySelector(
          '.post-toc__nav a[aria-current="location"]'
        )?.getAttribute('href') === '#b-second'""",
        timeout=10_000,
    )
    expect(page.locator('[aria-controls="toc-inline-c-third-children"]')).to_have_attribute(
        "aria-expanded", "false"
    )
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "true"
    )


def test_manually_closing_the_active_branch_sticks(harness_url, page):
    """Closing the active branch by hand keeps it closed while active."""
    page.goto(harness_url, wait_until="load")
    _scroll_to_heading(page, "a-one")
    page.wait_for_function(
        """() => document.querySelector(
          '[aria-controls="toc-inline-a-first-children"]'
        ).getAttribute('aria-expanded') === 'true'""",
        timeout=10_000,
    )
    _js_click(page, '[aria-controls="toc-inline-a-first-children"]')
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "false"
    )
    # The active row is still marked (one row, whatever the depth), but its
    # branch stays shut: manual intent beats auto-expansion.
    marked = page.locator(
        ".post-toc__nav a[aria-current='location']"
    ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
    assert marked == ["#a-one"], (
        f"exactly one row must stay marked, got {marked} (#345)"
    )
    expect(page.locator('[aria-controls="toc-inline-a-first-children"]')).to_have_attribute(
        "aria-expanded", "false"
    )


def test_keyboard_enter_and_space_toggle_branches_without_focus_jumps(
    harness_url, page
):
    """Real buttons: Enter/Space toggle; auto-expand never moves focus."""
    page.goto(harness_url, wait_until="load")
    toggle = '[aria-controls="toc-inline-a-first-children"]'
    page.evaluate(
        f"document.querySelector({toggle!r}).focus({{preventScroll: true}})"
    )
    page.keyboard.press("Enter")
    expect(page.locator(toggle)).to_have_attribute("aria-expanded", "true")
    page.keyboard.press(" ")
    expect(page.locator(toggle)).to_have_attribute("aria-expanded", "false")
    assert page.evaluate("document.activeElement.matches('.post-toc__toggle')"), (
        "toggling must keep focus on the toggle (#345)"
    )
    # Auto-expansion must not steal focus either: focus a row, scroll to a
    # far section, and the focused row keeps focus while the far branch
    # opens around the new active row.
    page.evaluate(
        "document.querySelector('.post-toc__item--h2 a').focus("
        "{preventScroll: true})"
    )
    _scroll_to_heading(page, "c-orphan")
    page.wait_for_function(
        """() => document.querySelector(
          '[aria-controls="toc-inline-c-third-children"]'
        ).getAttribute('aria-expanded') === 'true'""",
        timeout=10_000,
    )
    assert page.evaluate(
        "document.activeElement.getAttribute('href') === '#a-first'"
    ), "auto-expand must never move focus (#345)"


def test_h4_hides_with_its_collapsed_parent(harness_url, page):
    """Nesting fidelity at runtime: hiding the parent hides the h4."""
    page.goto(harness_url, wait_until="load")
    h4 = page.locator('.post-toc__item a[href="#a-one-x"]')
    expect(h4).to_be_hidden()
    _scroll_to_heading(page, "a-one-x")
    expect(h4).to_be_visible()
    _js_click(page, '[aria-controls="toc-inline-a-one-children"]')
    expect(h4).to_be_hidden()
    _js_click(page, '[aria-controls="toc-inline-a-one-children"]')
    expect(h4).to_be_visible()


def _visible_mount(page):
    displays = page.evaluate(
        """() => ({
          inline: getComputedStyle(document.querySelector('.post-toc-mount--inline')).display,
          sidebar: getComputedStyle(document.querySelector('.post-toc-mount--sidebar')).display,
        })"""
    )
    return ".post-toc-mount--sidebar" if displays["sidebar"] != "none" else (
        ".post-toc-mount--inline"
    )


def _heading_ids(page):
    return page.evaluate(
        """() => Array.from(
          document.querySelectorAll('.post-content h2[id], .post-content h3[id]')
        ).map(h => h.id)"""
    )


def _expect_active(page, mount, heading_id):
    page.wait_for_function(
        f"""() => {{
          const marked = Array.from(document.querySelectorAll(
            '{mount} a[aria-current="location"]'
          )).map(a => a.getAttribute('href'));
          return marked.length === 1 && marked[0] === '#{heading_id}';
        }}""",
        timeout=10_000,
    )


def test_both_copies_mark_the_same_row_on_a_long_post(
    built_site_url, page
):
    """Live scroll keeps exactly one marked row per mount (#345)."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    assert page.locator('details.post-toc[open]').count() == 2
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    assert len(ids) >= 16, f"expected a long post, got {len(ids)} headings"
    for index in (0, 5):
        _scroll_to_heading(page, ids[index])
        _expect_active(page, mount, ids[index])
    # The last heading cannot scroll fully to the viewport top when the
    # article tail is short: reaching the page end must still mark it.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    _expect_active(page, mount, ids[-1])
    # Both copies mark the same row.
    marked = page.locator(
        ".post-toc__nav a[aria-current='location']"
    ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
    assert marked == [f"#{ids[-1]}", f"#{ids[-1]}"], (
        f"both ToC copies must mark the same row, got {marked} (#345)"
    )


def test_the_last_heading_stays_active_at_the_end(built_site_url, page):
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    _expect_active(page, mount, ids[-1])


def test_clicking_a_row_marks_it_immediately(built_site_url, page):
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    _settle_layout(page)
    mount = _visible_mount(page)
    ids = _heading_ids(page)
    page.locator(f"{mount} a[href='#{ids[7]}']").click()
    # The default anchor jump fires after the click handler: poll until the
    # scroll settles on the clicked section instead of asserting mid-flight.
    expect(page.locator(f"{mount} a[href='#{ids[7]}']")).to_have_attribute(
        "aria-current", "location", timeout=10_000
    )
    assert page.url.split("#")[-1] == ids[7], (
        "the ToC link must still jump to its section (#345)"
    )


def test_keyboard_users_can_reach_every_row(built_site_url, page):
    """Rows stay plain anchors in tab order; toggles are real buttons."""
    page.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    mount = _visible_mount(page)
    links = page.locator(f"{mount} .post-toc__list a")
    assert links.count() >= 16
    assert page.evaluate(
        f"""() => Array.from(
          document.querySelectorAll('{mount} .post-toc__list a')
        ).every(a => a.tabIndex >= 0 && a.getAttribute('tabindex') === null)"""
    ), "every ToC row must stay keyboard-reachable (#345)"
    links.first.focus()
    assert page.evaluate(
        "document.activeElement.classList.contains('post-toc__list')"
        " || document.activeElement.tagName === 'A'"
    ), "a ToC row must be focusable (#345)"


def _active_contrast(page):
    return page.evaluate(
        """() => {
          const lum = (s) => {
            const c = s.match(/[\\d.]+/g).map(Number).slice(0, 3)
              .map(v => v / 255).map(v => v <= 0.03928 ? v / 12.92
                : Math.pow((v + 0.055) / 1.055, 2.4));
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
          };
          const link = document.querySelector(
            ".post-toc__nav a[aria-current='location']"
          );
          const fg = lum(getComputedStyle(link).color);
          const bg = lum(getComputedStyle(document.body).backgroundColor);
          const hi = Math.max(fg, bg), lo = Math.min(fg, bg);
          return (hi + 0.05) / (lo + 0.05);
        }"""
    )


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_active_row_passes_contrast_in_both_themes(
    built_site_url, browser, scheme
):
    """The active style is a theme-aware link colour: >= 4.5:1 either way."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 900}, color_scheme=scheme
    )
    try:
        themed = context.new_page()
        themed.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
        _settle_layout(themed)
        ids = themed.evaluate(
            """() => Array.from(
              document.querySelectorAll('.post-content h2[id]')
            ).map(h => h.id)"""
        )
        _scroll_to_heading(themed, ids[3])
        themed.wait_for_function(
            "() => document.querySelector"
            "(\"a[aria-current='location']\") !== null",
            timeout=10_000,
        )
        ratio = _active_contrast(themed)
        assert ratio >= 4.5, (
            f"the active ToC row is {ratio:.2f}:1 in {scheme} mode, "
            "below the 4.5:1 bar (#345)"
        )
    finally:
        context.close()


def test_three_open_levels_hold_without_overflow_on_small_phones(
    harness_url, browser
):
    """Three open levels must not overflow a 320px viewport (#345)."""
    context = browser.new_context(viewport={"width": 320, "height": 700})
    try:
        narrow = context.new_page()
        narrow.goto(harness_url, wait_until="load")
        # Force every branch open: the widest the ToC can ever get.
        narrow.evaluate(
            """() => document.querySelectorAll('.post-toc__toggle').forEach(
              t => { t.setAttribute('aria-expanded', 'true');
                document.getElementById(
                  t.getAttribute('aria-controls')).hidden = false; })"""
        )
        assert narrow.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "the nested ToC must not overflow a 320px viewport (#345)"
        lefts = narrow.evaluate(
            """() => [2, 3, 4].map(l => document.querySelector(
              `.post-toc__item--h${l} a`).getBoundingClientRect().left)"""
        )
        assert lefts[0] < lefts[1] < lefts[2], (
            f"levels must indent with depth, got {lefts} (#345)"
        )
    finally:
        context.close()


def _phone_page(browser, site_url, width, scheme="light"):
    """A phone-width page on the long EN post with third parties blocked."""
    context = browser.new_context(
        viewport={"width": width, "height": 700}, color_scheme=scheme
    )
    page = context.new_page()
    origin = urlparse(site_url).netloc
    page.route(
        "**/*",
        lambda route: route.continue_()
        if urlparse(route.request.url).netloc == origin
        else route.abort(),
    )
    page.goto(site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
    page.wait_for_function(
        "() => Array.from(document.images).every(i => i.complete)",
        timeout=15_000,
    )
    return context, page


@pytest.mark.parametrize("width", [320, 360, 375, 414])
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_phone_fab_replaces_the_inline_mount(
    built_site_url, browser, width, scheme
):
    """Phones get a reachable FAB; the inline mount goes away (JS path).

    Audit 2026-10-22: the open 16-row list cost 510px / 73% of a 700px
    viewport before the first paragraph; #383 replaces it with one
    floating button (the no-JS fallback keeps the inline list).
    """
    context, phone = _phone_page(browser, built_site_url, width, scheme)
    try:
        assert phone.evaluate(
            "document.documentElement.classList.contains('toc-fab-on')"
        ), "the JS path must flag the FAB handoff (#383)"
        assert phone.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--inline')).display"
        ) == "none"
        assert phone.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--sidebar')).display"
        ) == "none"
        fab = phone.get_by_role("button", name=re.compile("On this page"))
        assert fab.count() == 1
        box = fab.first.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, (
            "the FAB must clear 44px, got "
            f"{box['width']:.0f}x{box['height']:.0f} at {width}px (#383)"
        )
        # Bottom-left within the viewport: back-to-top owns bottom-right.
        assert box["x"] < width / 2, (
            f"the FAB must sit left of centre at {width}px, got x={box['x']:.0f}"
        )
        assert box["x"] >= 0 and box["y"] + box["height"] <= 700, (
            "the FAB must stay inside the viewport (#383)"
        )
        assert phone.locator(".toc-sheet").is_hidden(), (
            "the sheet starts shut (#383)"
        )
        assert phone.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), f"the FAB must not overflow a {width}px viewport (#383)"
    finally:
        context.close()


@pytest.mark.parametrize("width", [360, 375])
def test_phone_sheet_lists_bounded_single_line_rows(
    built_site_url, browser, width
):
    """Tapping the FAB opens a bounded sheet; rows truncate (#383).

    Audit 2026-10-22: 2 of 16 titles wrapped onto two lines; the inline
    list ran 510px unbounded. The sheet caps the moved nav instead.
    """
    context, phone = _phone_page(browser, built_site_url, width)
    try:
        phone.get_by_role("button", name=re.compile("On this page")).click()
        sheet = phone.locator(".toc-sheet")
        expect(sheet).to_be_visible()
        nav = phone.locator(".toc-sheet .post-toc__nav")
        assert nav.count() == 1, (
            "the inline nav must move into the sheet slot (#383)"
        )
        box = nav.evaluate(
            "el => ({client: el.clientHeight, scroll: el.scrollHeight})"
        )
        assert box["client"] <= 0.6 * 700 + 1, (
            f"the sheet list is {box['client']:.0f}px, over the 60vh cap "
            "(#383)"
        )
        assert box["scroll"] >= box["client"], (
            "the long-post list must scroll inside the sheet (#383)"
        )
        heights = phone.locator(
            ".toc-sheet .post-toc__item a"
        ).evaluate_all("els => els.map(el => el.getBoundingClientRect().height).filter(h => h > 0)")
        assert heights and all(h <= 25 for h in heights), (
            f"sheet rows must stay single-line, got {heights} (#383)"
        )
    finally:
        context.close()


def test_phone_active_row_stays_inside_the_sheet_without_moving_the_page(
    built_site_url, browser
):
    """Scrolling the article keeps the marked row visible in the sheet (#383).

    The sheet nudges only the moved nav's scrollTop; the page itself must
    land exactly where requested.
    """
    context, phone = _phone_page(browser, built_site_url, 375)
    try:
        phone.get_by_role("button", name=re.compile("On this page")).click()
        target = phone.evaluate(
            """() => { const hs = document.querySelectorAll(
              '.post-content h2[id]');
              const h = hs[Math.floor(hs.length / 2)];
              return h.getBoundingClientRect().top + window.scrollY - 10; }"""
        )
        phone.evaluate(f"window.scrollTo(0, {target})")
        phone.wait_for_function(
            """() => document.querySelector(
              '.toc-sheet a[aria-current="location"]'
            ) !== null""",
            timeout=10_000,
        )
        state = phone.evaluate(
            """() => { const nav = document.querySelector(
              '.toc-sheet .post-toc__nav');
              const a = document.querySelector(
              '.toc-sheet a[aria-current="location"]');
              const p = nav.getBoundingClientRect();
              const r = a.getBoundingClientRect();
              return { inPanel: r.top >= p.top - 1 && r.bottom <= p.bottom + 1,
                pageY: window.scrollY }; }"""
        )
        assert state["inPanel"], (
            "the active row must be visible inside the sheet (#383)"
        )
        assert abs(state["pageY"] - target) <= 2, (
            f"the page moved to {state['pageY']:.0f}, expected {target:.0f}: "
            "the panel must never move the page (#383)"
        )
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_phone_sheet_targets_and_no_overlap_at_320px(
    built_site_url, browser, scheme
):
    """Every visible sheet target clears 24px; FAB clears 44px; 320px calm."""
    context = browser.new_context(
        viewport={"width": 320, "height": 700}, color_scheme=scheme
    )
    try:
        page = context.new_page()
        page.goto(
            built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load"
        )
        fab = page.get_by_role("button", name=re.compile("On this page"))
        box = fab.first.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, (
            "the FAB must clear 44px at 320px (#383)"
        )
        fab.first.click()
        expect(page.locator(".toc-sheet")).to_be_visible()
        # Collapsed branches keep their rows out of the a11y tree at 0x0:
        # only laid-out targets count here.
        sizes = page.evaluate(
            """() => Array.from(document.querySelectorAll(
              '.toc-sheet .post-toc__item a,'
              + ' .toc-sheet .toc-sheet__close'
            )).filter(el => el.getBoundingClientRect().height > 0)
              .map(el => { const r = el.getBoundingClientRect();
              return [Math.round(r.width), Math.round(r.height)]; })"""
        )
        assert sizes, "expected visible sheet targets (#383)"
        for w, h in sizes:
            assert w >= 24 and h >= 24, (
                f"sheet target measures {w}x{h}, below 24px (#383)"
            )
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "the sheet must not overflow a 320px viewport (#383)"
    finally:
        context.close()


@pytest.mark.parametrize("width", [320, 360, 375, 414])
def test_phone_fab_never_overlaps_back_to_top(
    built_site_url, browser, width
):
    """Past the threshold both pills show, disjoint, inside the viewport."""
    context, phone = _phone_page(browser, built_site_url, width)
    try:
        phone.evaluate("window.scrollTo(0, 800)")
        phone.wait_for_function(
            "() => !document.querySelector('.back-to-top').hidden",
            timeout=10_000,
        )
        rects = phone.evaluate(
            """() => { const r = (s) => {
              const el = document.querySelector(s);
              const b = el.getBoundingClientRect();
              return {x: b.x, y: b.y, w: b.width, h: b.height}; };
              return { fab: r('.toc-fab'), top: r('.back-to-top') }; }"""
        )
        for name, r in rects.items():
            assert r["x"] >= 0 and r["x"] + r["w"] <= width, (
                f"{name} leaves the viewport at {width}px (#383)"
            )
        overlap = not (
            rects["fab"]["x"] + rects["fab"]["w"] <= rects["top"]["x"]
            or rects["top"]["x"] + rects["top"]["w"] <= rects["fab"]["x"]
            or rects["fab"]["y"] + rects["fab"]["h"] <= rects["top"]["y"]
            or rects["top"]["y"] + rects["top"]["h"] <= rects["fab"]["y"]
        )
        assert not overlap, (
            f"the FAB overlaps back-to-top at {width}px: "
            f"{rects} (#383)"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [360, 375])
def test_phone_sheet_opens_closes_with_focus_handoff(
    built_site_url, browser, width
):
    """Button, Esc, backdrop and close button; focus in and back (#383)."""
    context, phone = _phone_page(browser, built_site_url, width)
    try:
        # Start mid-article: the sheet must preserve the reading position.
        phone.evaluate("window.scrollTo(0, 1200)")
        phone.wait_for_function("() => window.scrollY === 1200", timeout=10_000)
        fab = phone.get_by_role("button", name=re.compile("On this page"))
        sheet = phone.locator(".toc-sheet")
        before = phone.evaluate("window.scrollY")
        fab.first.click()
        expect(sheet).to_be_visible()
        assert fab.first.get_attribute("aria-expanded") == "true"
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-sheet__close')"
        ), "opening must move focus into the sheet (#383)"
        assert phone.evaluate("window.scrollY") == before, (
            "opening the sheet must not move the page (#383)"
        )
        phone.keyboard.press("Escape")
        expect(sheet).to_be_hidden()
        assert fab.first.get_attribute("aria-expanded") == "false"
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-fab')"
        ), "Esc must return focus to the button (#383)"
        assert phone.evaluate("window.scrollY") == before, (
            "closing the sheet must not move the page (#383)"
        )
        fab.first.click()
        expect(sheet).to_be_visible()
        phone.locator(".toc-sheet__backdrop").click(position={"x": 20, "y": 20})
        expect(sheet).to_be_hidden()
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-fab')"
        ), "backdrop close must return focus to the button (#383)"
        fab.first.click()
        expect(sheet).to_be_visible()
        phone.locator(".toc-sheet__close").click()
        expect(sheet).to_be_hidden()
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-fab')"
        ), "close-button close must return focus to the button (#383)"
    finally:
        context.close()


def test_phone_ring_tracks_the_article_range(built_site_url, browser):
    """0% at the top, mid-way through, 100% at the end — sheet shut (#383)."""
    context, phone = _phone_page(browser, built_site_url, 375)
    try:
        label = phone.locator("[data-toc-fab-label]")
        ring = phone.locator("[data-toc-ring]")
        assert "0%" in label.inner_text()
        # Engines serialize the same offset differently (Chromium keeps the
        # unitless "125.66", Firefox reports "125.66px"), so compare the
        # number, not the string (#383).
        offset = ring.evaluate("el => el.style.strokeDashoffset")
        assert offset == "" or abs(float(re.match(r"[0-9.]+", offset).group()) - 125.66) < 0.01, (
            f"the ring starts empty at the top, got {offset!r} (#383)"
        )
        halfway = phone.evaluate(
            """() => { const a = document.querySelector('.post-content');
              const top = a.getBoundingClientRect().top + window.scrollY;
              return top + (a.offsetHeight - window.innerHeight) / 2; }"""
        )
        phone.evaluate(f"window.scrollTo(0, {halfway})")
        phone.wait_for_function(
            r"""() => { const t = document.querySelector(
              '[data-toc-fab-label]').textContent;
              const m = t.match(/(\d+)%/);
              return m && +m[1] > 0 && +m[1] < 100; }""",
            timeout=10_000,
        )
        mid_text = label.inner_text()
        mid_pct = int(re.search(r"(\d+)%", mid_text).group(1))
        assert 10 <= mid_pct <= 90, (
            f"halfway through the article the ring reads {mid_text} (#383)"
        )
        phone.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        phone.wait_for_function(
            """() => document.querySelector('[data-toc-fab-label]')
              .textContent.includes('100%')""",
            timeout=10_000,
        )
        assert phone.locator(".toc-sheet").is_hidden(), (
            "the ring must track while the sheet stays shut (#383)"
        )
    finally:
        context.close()


def test_phone_row_tap_navigates_and_closes_the_sheet(
    built_site_url, browser
):
    """A row tap jumps to its section, shuts the sheet, returns focus (#383)."""
    context, phone = _phone_page(browser, built_site_url, 375)
    try:
        ids = phone.evaluate(
            """() => Array.from(
              document.querySelectorAll('.post-content h2[id]')
            ).map(h => h.id)"""
        )
        target = ids[5]
        phone.get_by_role("button", name=re.compile("On this page")).click()
        expect(phone.locator(".toc-sheet")).to_be_visible()
        phone.evaluate(
            f"document.querySelector('.toc-sheet a[href=\"#{target}\"]').click()"
        )
        expect(phone.locator(".toc-sheet")).to_be_hidden()
        phone.wait_for_function(
            f"() => window.location.hash === '#{target}'", timeout=10_000
        )
        top = phone.evaluate(
            f"document.getElementById('{target}')"
            ".getBoundingClientRect().top"
        )
        assert top >= -2, (
            f"the #{target} heading lands {top:.0f}px up: the jump must not "
            "hide it under the header (#383)"
        )
        marked = phone.locator(
            ".toc-sheet a[aria-current='location']"
        ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
        assert marked == [f"#{target}"], (
            f"the tapped row must mark, got {marked} (#383)"
        )
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-fab')"
        ), "closing after a row tap must return focus to the button (#383)"
    finally:
        context.close()


def test_phone_sheet_marks_the_section_being_read(
    built_site_url, browser
):
    """Opening mid-article shows the current row marked and in view (#383)."""
    context, phone = _phone_page(browser, built_site_url, 375)
    try:
        target = phone.evaluate(
            """() => { const hs = document.querySelectorAll(
              '.post-content h2[id]');
              const h = hs[Math.floor(hs.length / 2)];
              return { y: h.getBoundingClientRect().top + window.scrollY - 10,
                id: h.id }; }"""
        )
        phone.evaluate(f"window.scrollTo(0, {target['y']})")
        phone.wait_for_function(
            f"""() => document.querySelector('.toc-sheet')
              !== null && document.querySelector(
              '.post-toc-mount--sidebar a[aria-current="location"]'
              )?.getAttribute('href') === '#{target["id"]}'""",
            timeout=10_000,
        )
        phone.get_by_role("button", name=re.compile("On this page")).click()
        expect(phone.locator(".toc-sheet")).to_be_visible()
        marked = phone.locator(
            ".toc-sheet a[aria-current='location']"
        ).evaluate_all("links => links.map(a => a.getAttribute('href'))")
        assert marked == [f"#{target['id']}"], (
            f"exactly one sheet row must mark, got {marked} (#383)"
        )
        state = phone.evaluate(
            """() => { const nav = document.querySelector(
              '.toc-sheet .post-toc__nav');
              const a = document.querySelector(
              '.toc-sheet a[aria-current="location"]');
              const p = nav.getBoundingClientRect();
              const r = a.getBoundingClientRect();
              return r.top >= p.top - 1 && r.bottom <= p.bottom + 1; }"""
        )
        assert state, (
            "the sheet must open scrolled to the section being read (#383)"
        )
    finally:
        context.close()


def test_vietnamese_fab_uses_the_local_name(built_site_url, browser):
    """The VI twin names the button 'Trong bài này' with the same flow."""
    context = browser.new_context(viewport={"width": 375, "height": 700})
    try:
        page = context.new_page()
        page.goto(
            built_site_url.rstrip("/") + VI_LONG_POST, wait_until="load"
        )
        fab = page.get_by_role("button", name=re.compile("Trong bài này"))
        assert fab.count() == 1
        fab.first.click()
        expect(page.locator(".toc-sheet")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator(".toc-sheet")).to_be_hidden()
    finally:
        context.close()


def test_desktop_toc_stays_open_beside_the_article(built_site_url, browser):
    """Desktop behaviour is unchanged: the sidebar copy stays open (#377)."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        page.goto(
            built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load"
        )
        assert page.locator("details.post-toc[open]").count() == 2, (
            "desktop must keep both ToC copies open (#377)"
        )
        assert page.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--sidebar')).display"
        ) != "none"
        assert page.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--inline')).display"
        ) == "none"
    finally:
        context.close()


def test_no_js_readers_get_every_level_with_working_anchors(
    harness_url, browser
):
    """No-JS: every level visible, plain anchors, no dead states (#345)."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        plain.goto(harness_url, wait_until="load")
        assert plain.locator('details.post-toc[open]').count() == 1
        assert plain.locator(
            ".post-toc__nav a[aria-current]"
        ).count() == 0
        for href in ("#a-first", "#a-one", "#a-one-x", "#a-two", "#c-orphan"):
            expect(plain.locator(f'.post-toc__nav a[href="{href}"]')).to_be_visible()
        assert plain.locator(".post-toc__toggle[aria-expanded='true']").count() == 3
        plain.locator('.post-toc__nav a[href="#a-one-x"]').click()
        plain.wait_for_function(
            "() => window.location.hash === '#a-one-x'", timeout=10_000
        )
    finally:
        context.close()


def test_no_js_long_post_lists_every_row_with_working_anchors(
    built_site_url, browser
):
    """No-JS on a real post: the list stays usable, anchors jump (#345)."""
    context = browser.new_context(java_script_enabled=False)
    try:
        plain = context.new_page()
        plain.goto(built_site_url.rstrip("/") + EN_LONG_POST, wait_until="load")
        assert plain.locator('details.post-toc[open]').count() == 2
        assert plain.locator(
            ".post-toc__nav a[aria-current]"
        ).count() == 0
        ids = plain.evaluate(
            """() => Array.from(
              document.querySelectorAll('.post-content h2[id]')
            ).map(h => h.id)"""
        )
        inline_visible = plain.evaluate(
            "getComputedStyle(document.querySelector("
            "'.post-toc-mount--inline')).display !== 'none'"
        )
        mount = (
            ".post-toc-mount--inline" if inline_visible
            else ".post-toc-mount--sidebar"
        )
        plain.locator(f"{mount} .post-toc__nav a[href='#{ids[4]}']").click()
        plain.wait_for_function(
            f"() => window.location.hash === '#{ids[4]}'", timeout=10_000
        )
    finally:
        context.close()
