"""Guards for #402: motion polish for the FAB and interactive controls.

The FAB (#383) and the other controls felt static, so #402 adds one shared
motion system plus per-control polish: duration/easing tokens used by the
ToC FAB (press/hover) and sheet (open), the progress ring/bar (value
transitions), back-to-top (appear), theme toggle (icon crossfade), nav
toggle (icon morph), copy-code (success pop), lightbox (open + image fade),
share buttons (press), tag chips (hover/press), and pagination/post-card
hover. Motion is transient paint only: final states are unchanged.

Guarded here:

- static (no Ruby, no browser): the tokens live once in
  `custom-variables.scss` (fast 120ms, base 180ms, slow 240ms, a standard
  ease-out, a FAB-only spring); the `custom/_motion.scss` partial leads the
  cascade with the shared keyframes, the documented when-NOT-to-animate
  rules, and one global reduced-motion guard; every control
  transition/animation references the tokens (no ad-hoc durations/easings);
  only transform/opacity animate (progress values + the theme flip are the
  documented exceptions); focus rings stay instant; print kills motion;
  nothing loops or runs slower than the slow token;
- built (needs Ruby, no browser): the compiled stylesheet ships the
  keyframes and the guard;
- browser (needs Ruby + a browser): the sheet still opens/closes within a
  bounded time under reduced motion with instant state changes, and the
  header/FAB boxes never shift (CLS-style: hover/press/open/close move no
  layout).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOM_DIR = REPO_ROOT / "_sass" / "minima" / "custom"
SASS_DIR = REPO_ROOT / "_sass"
TOKENS_FILE = REPO_ROOT / "_sass" / "minima" / "custom-variables.scss"
MOTION_PARTIAL = CUSTOM_DIR / "_motion.scss"
PRINT_PARTIAL = CUSTOM_DIR / "_print.scss"
STYLES_INDEX = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"

EXPECTED_TOKENS = {
    "$motion-fast": "120ms",
    "$motion-base": "180ms",
    "$motion-slow": "240ms",
}

EXPECTED_KEYFRAMES = (
    "motion-fade-in",
    "motion-rise-in",
    "motion-sheet-in",
    "motion-pop",
    "motion-icon-in",
)

# Every animated control and the partial carrying its motion rules (#402
# scope). The guard test below pins both directions: each selector must
# animate through the tokens, and each must sit inside the global
# reduced-motion guard in `_motion.scss`.
EXPECTED_ANIMATED = {
    ".toc-fab": "_toc.scss",
    ".toc-fab__value": "_toc.scss",
    ".toc-sheet__backdrop": "_toc.scss",
    ".toc-sheet__panel": "_toc.scss",
    ".toc-sheet__close": "_toc.scss",
    ".post-toc__chevron": "_toc.scss",
    ".reading-progress__bar": "_reading-progress.scss",
    ".back-to-top": "_reading-progress.scss",
    "body": "_theme-toggle.scss",
    # The sun/moon crossfade (`&__icon` nesting): the guard pins the
    # expanded `.theme-toggle__icon`, the partial carries `.theme-toggle`.
    ".theme-toggle": "_theme-toggle.scss",
    ".nav-toggle": "_layout.scss",
    ".menu-icon": "_layout.scss",
    ".copy-code__button": "_utilities.scss",
    ".share__button": "_share.scss",
    ".share__link": "_share.scss",
    ".tag-chip": "_tags.scss",
    ".pagination": "_layout.scss",
    ".post-thumb img": "_list-thumbs.scss",
    ".lightbox__backdrop": "_lightbox.scss",
    ".lightbox__dialog": "_lightbox.scss",
    ".lightbox__image--fresh": "_lightbox.scss",
    ".lightbox__close": "_lightbox.scss",
    ".lightbox__prev": "_lightbox.scss",
    ".lightbox__next": "_lightbox.scss",
}

EN_LONG_POST = "/2022/12/25/explaining-the-internet.html"


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

    def _strip_line_comment(line):
        in_single = in_double = False
        index = 0
        while index < len(line) - 1:
            char = line[index]
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif char == "/" and line[index + 1] == "/" and not (
                in_single or in_double
            ):
                return line[:index]
            index += 1
        return line

    return "\n".join(_strip_line_comment(line) for line in text.splitlines())


def _all_scss():
    return sorted(SASS_DIR.rglob("*.scss"))


def _guard_spans(text):
    """Offsets inside `prefers-reduced-motion: reduce`/`print` blocks."""
    spans = []
    for match in re.finditer(
        r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)"
        r"|@media\s+print\b",
        text,
    ):
        depth = 0
        start = match.start()
        pos = text.index("{", match.end())
        for index in range(pos, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((start, index + 1))
                    break
    return spans


def _motion_declarations(path):
    """`(kind, value, guarded)` for each transition/animation declaration."""
    text = _strip_comments(_read(path))
    spans = _guard_spans(text)
    found = []
    for match in re.finditer(
        r"(?P<kind>transition|animation)\s*:\s*(?P<value>[^;{}]+);", text
    ):
        guarded = any(
            start <= match.start() <= end for start, end in spans
        )
        found.append((match.group("kind"), match.group("value"), guarded))
    return found


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_motion_tokens_are_defined_once_with_the_pinned_scale():
    assert TOKENS_FILE.is_file(), (
        f"{TOKENS_FILE.relative_to(REPO_ROOT)} is missing"
    )
    tokens = _read(TOKENS_FILE)
    for name, value in EXPECTED_TOKENS.items():
        assert f"{name}: {value};" in tokens, (
            f"{name} must stay {value} — every control shares this scale"
        )
    assert "$motion-ease-out: cubic-bezier(" in tokens, (
        "the standard ease-out must be a shared token"
    )
    assert "$motion-spring: cubic-bezier(" in tokens, (
        "the FAB-only spring easing must be a shared token"
    )
    definers = [
        path.name
        for path in _all_scss()
        if re.search(r"\$motion-(fast|base|slow|ease-out|spring)\s*:",
                     _strip_comments(_read(path)))
    ]
    assert definers == [TOKENS_FILE.name], (
        f"motion tokens must be defined once, but found definitions in "
        f"{definers}"
    )


@pytest.mark.static
def test_motion_partial_closes_the_cascade_with_keyframes_and_rules():
    assert MOTION_PARTIAL.is_file(), (
        f"{MOTION_PARTIAL.relative_to(REPO_ROOT)} is missing"
    )
    index = _read(STYLES_INDEX)
    assert index.count("minima/custom/motion") == 1, (
        "the index must import the motion partial exactly once"
    )
    names = []
    for block in re.finditer(r"@import\s+(.*?);", index, re.S):
        for item in block.group(1).split(","):
            name = item.strip().strip("\"'")
            if name.startswith("minima/custom/"):
                names.append(name[len("minima/custom/"):])
    assert names[-2] == "motion" and names[-1] == "print", (
        "the motion partial must sit just before print: after the #148 "
        "legibility pass (whose guards scan the head for desktop base "
        "rules), with only the print kill-switch after it"
    )
    scss = _read(MOTION_PARTIAL)
    for frame in EXPECTED_KEYFRAMES:
        assert f"@keyframes {frame}" in scss, (
            f"the shared keyframes must define `{frame}`"
        )
    # The when-NOT-to-animate rules are documented in this partial.
    for needle in (
        "transform/opacity only",
        "Never delay interaction",
        "focus rings instant",
        "focus trap",
        "Print styles unaffected",
        "3Hz",
        "never required to understand",
    ):
        assert needle in scss, (
            f"the motion partial must document the rule `{needle}`"
        )
    assert "@media (prefers-reduced-motion: reduce)" in scss, (
        "the motion partial must hold the global reduced-motion guard"
    )


@pytest.mark.static
def test_every_control_transition_uses_the_shared_tokens():
    """No ad-hoc durations/easings on controls: tokens or a guard, nothing
    else. `transition: none` / `animation: none` pins are always fine."""
    offenders = []
    for path in _all_scss():
        for kind, value, guarded in _motion_declarations(path):
            if "none" in value and not re.search(r"\d", value):
                continue
            if "$motion-" in value or guarded:
                continue
            offenders.append(f"{path.name}: {kind}: {value.strip()}")
    assert not offenders, (
        "ad-hoc motion outside the tokens/guard: "
        + "; ".join(offenders)
    )


@pytest.mark.static
def test_no_raw_durations_or_easings_outside_the_token_definitions():
    """Durations (`120ms`, `0.2s`) and bezier easings appear only where the
    tokens are defined; controls reference them as `$motion-*`."""
    offenders = []
    for path in _all_scss():
        if path == TOKENS_FILE:
            continue
        text = _strip_comments(_read(path))
        for match in re.finditer(
            r"(transition|animation)\s*:[^;{}]+;", text
        ):
            declaration = match.group(0)
            if re.search(r"\b\d+(\.\d+)?(ms|s)\b", declaration):
                offenders.append(f"{path.name}: {declaration.strip()}")
            if "cubic-bezier(" in declaration:
                offenders.append(f"{path.name}: {declaration.strip()}")
    assert not offenders, (
        "raw durations/easings on controls (use the `$motion-*` tokens): "
        + "; ".join(offenders)
    )


@pytest.mark.static
def test_transitions_stay_off_layout_properties():
    """Transform/opacity only. The documented exceptions: the progress bar
    width, the FAB ring dash offset, and the body theme-flip colours."""
    offenders = []
    for path in _all_scss():
        text = _strip_comments(_read(path))
        for match in re.finditer(r"transition\s*:\s*([^;{}]+);", text):
            value = match.group(1)
            if "none" in value and not re.search(r"\d", value):
                continue
            props = [part.strip().split()[0] for part in value.split(",")]
            for prop in props:
                if prop in (
                    "height", "margin", "padding", "top", "left",
                    "right", "bottom", "inset",
                ) or prop.startswith(("margin-", "padding-")):
                    offenders.append(f"{path.name}: {value.strip()}")
                if prop == "width" and "reading-progress__bar" not in text[
                    max(0, match.start() - 2000):match.start()
                ]:
                    offenders.append(f"{path.name}: {value.strip()}")
                if prop in ("background-color", "color") and path.name != (
                    "_theme-toggle.scss"
                ):
                    offenders.append(f"{path.name}: {value.strip()}")
    assert not offenders, (
        "layout-affecting transitions (animate transform/opacity only): "
        + "; ".join(offenders)
    )


@pytest.mark.static
def test_every_animated_control_sits_inside_the_reduced_motion_guard():
    """State changes must work instantly with no motion: each animated
    selector below appears in the global guard, and each carries a real
    tokenized transition/animation in its own partial."""
    guard = _read(MOTION_PARTIAL)
    guard_block = guard.split(
        "@media (prefers-reduced-motion: reduce)", 1
    )[1]
    for selector, partial in EXPECTED_ANIMATED.items():
        assert selector in guard_block, (
            f"`{selector}` animates but sits outside the global "
            "reduced-motion guard"
        )
        # `_layout.scss` is vendored at `minima/` level, the rest are
        # custom partials.
        source = (
            REPO_ROOT / "_sass" / "minima" / partial
            if partial == "_layout.scss"
            else CUSTOM_DIR / partial
        )
        partial_text = _read(source)
        assert selector in partial_text, (
            f"`{selector}` is missing from {source.name}"
        )
        declarations = [
            value
            for kind, value, _ in _motion_declarations(source)
            if kind in ("transition", "animation")
        ]
        assert any("$motion-" in value for value in declarations), (
            f"`{selector}` in {source.name} must animate through the "
            "shared tokens"
        )


@pytest.mark.static
def test_focus_rings_stay_instant():
    """No transition on `:focus`/`:focus-visible` rules, and `outline`
    never appears in a transition list (per the #399 intent)."""
    offenders = []
    for path in _all_scss():
        text = _strip_comments(_read(path))
        for match in re.finditer(r"transition\s*:\s*([^;{}]+);", text):
            if "outline" in match.group(1):
                offenders.append(f"{path.name}: {match.group(0).strip()}")
        for match in re.finditer(
            r"(?P<selector>[^{}@]+)\{(?P<body>[^{}]*)\}", text
        ):
            if ":focus" in match.group("selector") and "transition" in (
                match.group("body")
            ):
                offenders.append(
                    f"{path.name}: {match.group('selector').strip()}"
                )
    assert not offenders, (
        "focus indication must appear immediately (no fade-in): "
        + "; ".join(offenders)
    )


@pytest.mark.static
def test_nothing_loops_or_runs_slower_than_the_slow_token():
    assert "infinite" not in _strip_comments(
        "\n".join(_read(path) for path in _all_scss())
    ), "motion must never loop (`infinite` would risk flashing above 3Hz)"
    tokens = _read(TOKENS_FILE)
    for name in ("$motion-fast", "$motion-base", "$motion-slow"):
        match = re.search(re.escape(name) + r"\s*:\s*(\d+)ms", tokens)
        assert match and int(match.group(1)) <= 240, (
            f"{name} must not exceed the 240ms cap without justification"
        )


@pytest.mark.static
def test_print_kills_motion():
    scss = _read(PRINT_PARTIAL)
    assert "@media print" in scss
    block = scss.split("@media print", 1)[1]
    assert "transition: none" in block, (
        "print output must not carry transitions"
    )
    assert "animation: none" in block, (
        "print output must not carry animations"
    )


# --- built guards (need Ruby; no browser) ----------------------------------


def test_the_built_stylesheet_ships_the_motion_system(built_site):
    css = (built_site / "assets" / "css" / "style.css").read_text(
        encoding="utf-8"
    )
    for frame in EXPECTED_KEYFRAMES:
        assert f"@keyframes {frame}" in css, (
            f"the built stylesheet ships no `@{frame}` keyframes"
        )
    assert "prefers-reduced-motion" in css, (
        "the built stylesheet ships no reduced-motion guard"
    )
    assert "cubic-bezier(0.2, 0, 0, 1)" in css, (
        "the built stylesheet ships no shared easing (tokens unused?)"
    )


# --- browser guards (need Ruby + a browser) ---------------------------------


def _phone_page(browser, site_url, width=375, reduced=False):
    context = browser.new_context(
        viewport={"width": width, "height": 700},
        reduced_motion="reduce" if reduced else "no-preference",
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


def _boxes(page, selectors):
    return page.evaluate(
        """(sels) => Object.fromEntries(sels.map(s => {
          const el = document.querySelector(s);
          if (!el) return [s, null];
          const r = el.getBoundingClientRect();
          return [s, [r.x, r.y, r.width, r.height]];
        }))""",
        selectors,
    )


def test_sheet_opens_and_closes_within_a_bound_under_reduced_motion(
    built_site_url, browser
):
    """State over motion: open/close stay fast with zero transition."""
    context, phone = _phone_page(browser, built_site_url, reduced=True)
    try:
        fab = phone.get_by_role("button", name="On this page")
        sheet = phone.locator(".toc-sheet")
        fab.first.click()
        phone.wait_for_selector(
            ".toc-sheet:not([hidden])", timeout=2_000
        )
        assert sheet.is_visible()
        for selector in (".toc-sheet__panel", ".toc-fab"):
            durations = phone.evaluate(
                """(s) => { const cs = getComputedStyle(
                  document.querySelector(s));
                  return { transition: cs.transitionDuration,
                    animation: cs.animationName }; }""",
                selector,
            )
            assert durations["transition"] in ("0s", "0s, 0s"), (
                f"{selector} still transitions under reduced motion: "
                f"{durations}"
            )
            assert durations["animation"] == "none", (
                f"{selector} still animates under reduced motion: "
                f"{durations}"
            )
        phone.keyboard.press("Escape")
        phone.wait_for_selector(".toc-sheet", state="hidden", timeout=2_000)
        assert sheet.is_hidden()
        assert phone.evaluate(
            "document.activeElement.classList.contains('toc-fab')"
        ), "the focus handoff must survive reduced motion"
    finally:
        context.close()


def test_header_and_fab_boxes_never_shift(built_site_url, browser):
    """CLS-style: hover, press, open and close move no layout."""
    context, phone = _phone_page(browser, built_site_url)
    try:
        selectors = [
            ".site-title",
            ".site-nav",
            ".lang-switcher",
            ".theme-toggle",
            ".toc-fab",
        ]
        before = _boxes(phone, selectors)
        assert all(before[s] is not None for s in selectors)
        scrolled = phone.evaluate("window.scrollY")

        # Hovering the FAB may paint a 1px lift, but nothing else moves.
        phone.locator(".toc-fab").hover()
        phone.wait_for_timeout(300)
        hovered = _boxes(phone, selectors)
        for selector in (
            ".site-title",
            ".site-nav",
            ".lang-switcher",
            ".theme-toggle",
        ):
            assert hovered[selector] == before[selector], (
                f"hovering the FAB shifted {selector}: "
                f"{before[selector]} -> {hovered[selector]}"
            )
        fab_delta = abs(hovered[".toc-fab"][1] - before[".toc-fab"][1])
        assert fab_delta <= 2, (
            f"the FAB hover moved {fab_delta:.1f}px (cap: a 1px lift)"
        )
        # The 1.03 hover scale legitimately grows the painted box; layout
        # is untouched (siblings above are identical), so only bound it.
        for index, base in enumerate(before[".toc-fab"][2:]):
            assert abs(hovered[".toc-fab"][2 + index] - base) <= 0.05 * base, (
                "the FAB hover must stay within a 5% paint change"
            )

        # Open and close: the page and the chrome stay exactly put.
        phone.get_by_role("button", name="On this page").first.click()
        phone.wait_for_selector(
            ".toc-sheet:not([hidden])", timeout=10_000
        )
        phone.keyboard.press("Escape")
        phone.wait_for_selector(".toc-sheet", state="hidden", timeout=10_000)
        phone.mouse.move(10, 10)
        phone.wait_for_timeout(300)
        after = _boxes(phone, selectors)
        assert after == before, (
            f"open/close shifted the chrome: {before} -> {after}"
        )
        assert phone.evaluate("window.scrollY") == scrolled, (
            "open/close must not move the page"
        )
    finally:
        context.close()
