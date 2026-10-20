"""Guards for #220: the dark mode theme toggle.

Every page carries an icon-only `.theme-toggle` button in the header row that
flips the whole site between light and dark:

- first visit follows the OS `prefers-color-scheme` (even without JS, via the
  `auto` minima skin); an explicit choice persists in `localStorage` across
  pages and visits;
- an inline bootstrap in `_includes/head.html` sets `html[data-theme]` before
  the stylesheet paints, so there is no flash of the wrong theme;
- the accessible name and tooltip follow the page language (EN/VI), the
  control is a real 44px `<button>` (`aria-pressed`, keyboard-operable,
  visible focus), and the theme transition respects
  `prefers-reduced-motion`;
- contrast stays >= 4.5:1 in both modes (axe `color-contrast`, home + post +
  tag pages, phone + desktop).

Guarded here (static + build + browser, EN + VI).
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

import test_axe_a11y

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_INCLUDE = REPO_ROOT / "_includes" / "header.html"
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
SUB_FOOTER_INCLUDE = REPO_ROOT / "_includes" / "sub-footer.html"
SCRIPT = REPO_ROOT / "assets" / "js" / "theme-toggle.js"

SCRIPT_PATH = "/assets/js/theme-toggle.js"
STORAGE_KEY = "theme"

# Same tiny-script budget as the sibling header scripts (#114, #126).
MAX_SCRIPT_BYTES = 3072
MAX_SCRIPT_CODE_LINES = 80

LABEL_DARK_EN = "Switch to dark mode"
LABEL_LIGHT_EN = "Switch to light mode"
LABEL_DARK_VI = "Chuyển sang giao diện tối"
LABEL_LIGHT_VI = "Chuyển sang giao diện sáng"

EN_POST = "/2022/10/27/brewing-vietnamese-coffee.html"
AXE_PAGES = ("/", "/vi/", EN_POST, "/tags/")
VIEWPORTS = (375, 1280)
VIEWPORT_HEIGHT = 800


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_toggle_script_exists_and_stays_tiny():
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SCRIPT_BYTES, (
        "the theme-toggle script must stay tiny; it is fetched on every page"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SCRIPT_CODE_LINES, (
        f"the theme-toggle script has {len(code)} code lines, expected at "
        f"most {MAX_SCRIPT_CODE_LINES}"
    )
    # No dependency, no build step: the file runs as it is served.
    assert "import " not in text and "require(" not in text, (
        "the theme-toggle script must not depend on anything"
    )


@pytest.mark.static
def test_toggle_script_persists_an_os_default_choice():
    text = _read(SCRIPT)
    assert f'"{STORAGE_KEY}"' in text or f"'{STORAGE_KEY}'" in text, (
        "the script must persist the explicit choice in localStorage (#220)"
    )
    assert "localStorage.getItem" in text and "localStorage.setItem" in text
    assert "prefers-color-scheme" in text, (
        "first visit (no stored choice) must follow the OS preference (#220)"
    )
    assert "data-theme" in text, (
        "the script must flip `html[data-theme]`, the skin override hook"
    )
    assert "aria-pressed" in text and "aria-label" in text, (
        "the button state and accessible name must follow the theme (#220)"
    )
    assert "data-label-dark" in text and "data-label-light" in text, (
        "the localized labels must ride with the button (EN/VI, #220)"
    )


@pytest.mark.static
def test_inline_bootstrap_sets_the_theme_before_the_stylesheet():
    """No flash of the wrong theme: the inline script precedes the CSS link.

    A deferred or end-of-body script would paint first and flip after, so the
    bootstrap lives inline in the head, ahead of `#main-stylesheet`. It only
    reads (first visits leave no `localStorage` trace; the write happens on
    explicit toggle in `theme-toggle.js`).
    """
    head = _read(HEAD_INCLUDE)
    bootstrap = re.search(r"<script>\(function\(\)\{.*?</script>", head, re.S)
    assert bootstrap, "head.html ships no inline theme bootstrap (#220)"
    script = bootstrap.group(0)
    assert "localStorage" in script and "data-theme" in script
    assert "prefers-color-scheme" in script
    assert "setItem" not in script, (
        "the bootstrap must only read the stored choice, never write it"
    )
    stylesheet = head.find('id="main-stylesheet"')
    assert stylesheet != -1, "head.html links no #main-stylesheet to judge"
    assert head.find(bootstrap.group(0)) < stylesheet, (
        "the theme bootstrap must precede the stylesheet link (#220)"
    )


@pytest.mark.static
def test_header_renders_a_localized_icon_only_toggle():
    header = _read(HEADER_INCLUDE)
    assert 'class="theme-toggle"' in header
    button = re.search(r'<button[^>]*class="theme-toggle"[^>]*>', header)
    assert button, "the header renders no `.theme-toggle` button (#220)"
    attrs = button.group(0)
    assert 'type="button"' in attrs
    assert "aria-pressed" in attrs, "the toggle must expose its state (#220)"
    assert "data-label-dark" in attrs and "data-label-light" in attrs
    # Icon-only button: visible SVGs carry no text, so `aria-label` cannot
    # mismatch the visible label (WCAG 2.5.3, #213 pattern).
    assert header.count("theme-toggle__icon--moon") == 1
    assert header.count("theme-toggle__icon--sun") == 1
    assert 'class="theme-toggle__icon' in header
    assert LABEL_DARK_EN in header and LABEL_LIGHT_EN in header
    assert LABEL_DARK_VI in header and LABEL_LIGHT_VI in header
    # The toggle sits in the header row, never in the collapsible panel.
    nav = re.search(r'<nav class="site-nav".*?</nav>', header, re.S)
    assert nav, "the header renders no `.site-nav` to judge"
    assert "theme-toggle" not in nav.group(0), (
        "the toggle must sit in the header row, not inside `.site-nav`"
    )


@pytest.mark.static
def test_sub_footer_links_the_toggle_with_the_build_token():
    text = _read(SUB_FOOTER_INCLUDE)
    match = re.search(
        r'<script src="(/assets/js/theme-toggle\.js\?v=([^"]+))"', text
    )
    assert match, (
        "sub-footer.html must link theme-toggle.js with the `?v=` build "
        "token (#61: a warm browser must never pair new markup with an old "
        "script)"
    )


@pytest.mark.static
def test_theme_partial_defines_the_data_theme_layer():
    """The `auto` skin follows the OS; the partial adds the explicit layer."""
    scss = conftest.custom_styles_text()
    assert "minima/custom/theme-toggle" in _read(
        REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
    ), "the index must import the theme-toggle partial last (#174)"
    assert 'html[data-theme="dark"]' in scss
    assert 'html[data-theme="light"]' in scss
    assert "prefers-color-scheme" in scss, (
        "the no-JS OS-preference fallback needs its media-query branch (#220)"
    )
    assert "color-scheme" in scss, (
        "scrollbars and form controls must match the theme (#220)"
    )
    # Code tokens follow the explicit choice too, but since #275 they live
    # in the conditional `assets/css/syntax.css` companion (same layers,
    # same order) instead of this partial: the structural layer stays here.
    toggle = _read(REPO_ROOT / "_sass" / "minima" / "custom" / "_theme-toggle.scss")
    assert "@include dm-highlight" not in toggle, (
        "dark token rules must ship only in the syntax companion, linked "
        "on code pages (#275)"
    )
    assert "@include lm-highlight" not in toggle, (
        "light token rules must ship only in the syntax companion, linked "
        "on code pages (#275)"
    )
    assert "prefers-reduced-motion" in scss, (
        "the theme transition must respect reduced motion (#220)"
    )
    # 44px control, icon-only, keyboard focus covered by the global
    # `:focus-visible` rule plus a dark-safe outline colour.
    assert ".theme-toggle" in scss
    assert "width: 44px" in scss and "height: 44px" in scss
    assert "outline-color" in scss


@pytest.mark.static
def test_dark_overrides_cover_share_lightbox_and_back_to_top():
    """#241: the newer `$brand-color-dark` uses stay visible in dark mode.

    The share hover/status, lightbox trigger focus ring and back-to-top
    hover reuse the static light `$brand-color-dark` (near-invisible
    `#2b2b2b` on the dark `#181818` background), and the image trigger is
    not in the generic focus-override list. The dark layer must lift all
    four to the same `$dm-brand-color-light` grey family the #220 overrides
    use, while the light partials keep `$brand-color-dark` (light mode
    pixel-identical). The status text must additionally hold 4.5:1 on the
    dark background.
    """
    partial = REPO_ROOT / "_sass" / "minima" / "custom" / "_theme-toggle.scss"
    dark = _read(partial)
    for selector in (
        ".share__link:hover",
        ".share__button:hover",
        ".share__status",
        ".post-content img.lightbox-trigger:focus-visible",
        ".back-to-top:hover",
    ):
        assert selector in dark, (
            f"the dark theme layer covers no {selector} override (#241)"
        )
    assert dark.count("$dm-brand-color-light") >= 5, (
        "the #241 overrides must reuse the $dm-brand-color-light grey family"
    )
    # Light mode stays untouched: the light partials still use the static
    # value, so only the dark-scoped layer changes the paint.
    light_uses = {
        "_share.scss": ("border-color: $brand-color-dark", "color: $brand-color-dark"),
        "_lightbox.scss": ("outline: 3px solid $brand-color-dark",),
        "_reading-progress.scss": ("border-color: $brand-color-dark",),
    }
    for name, needles in light_uses.items():
        text = _read(REPO_ROOT / "_sass" / "minima" / "custom" / name)
        for needle in needles:
            assert needle in text, (
                f"{name} lost its light-mode `{needle}` "
                "(light rendering must stay pixel-identical, #241)"
            )
    # Contrast: lighten(#999999, 5%) is #a6a6a6; pin ~7:1 on #181818.
    skin = _read(REPO_ROOT / "_sass" / "minima" / "skins" / "auto.scss")
    match = re.search(
        r"^\s*\$dm-brand-color:\s*(#[0-9a-fA-F]{6})", skin, re.M
    )
    assert match, "the auto skin defines no dm-brand-color to judge (#241)"
    import colorsys

    base = match.group(1)
    r, g, b = (int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    r2, g2, b2 = colorsys.hls_to_rgb(h, min(1.0, lightness + 0.05), s)
    foreground = "#{:02x}{:02x}{:02x}".format(
        round(r2 * 255), round(g2 * 255), round(b2 * 255)
    )
    assert foreground == "#a6a6a6", (
        f"$dm-brand-color-light resolves to {foreground}, expected #a6a6a6 "
        "(#241)"
    )
    background = re.search(
        r"^\s*\$dm-background-color:\s*(#[0-9a-fA-F]{6})", skin, re.M
    )
    assert background, "the auto skin defines no dm-background-color (#241)"

    def luminance(hex_color):
        channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linearized = [
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linearized[0] + 0.7152 * linearized[1] + 0.0722 * linearized[2]

    peak = max(luminance(background.group(1)), luminance(foreground))
    base_lum = min(luminance(background.group(1)), luminance(foreground))
    ratio = (peak + 0.05) / (base_lum + 0.05)
    assert ratio >= 4.5, (
        f"share status {foreground} on {background.group(1)} is {ratio:.2f}:1 "
        "(needs 4.5:1, #241)"
    )


# --- build guards (need Ruby; no browser) -----------------------------------


def test_toggle_renders_on_pages_in_both_languages(built_site):
    """Home EN/VI plus the switcher-less 404 carry the toggle and bootstrap."""
    for rel, dark_label, light_label in (
        ("index.html", LABEL_DARK_EN, LABEL_LIGHT_EN),
        ("vi/index.html", LABEL_DARK_VI, LABEL_LIGHT_VI),
        ("404.html", LABEL_DARK_EN, LABEL_LIGHT_EN),
    ):
        html = (built_site / rel).read_text(encoding="utf-8")
        button = re.search(
            r'<button[^>]*class="theme-toggle"[^>]*>', html
        )
        assert button, f"/{rel} renders no theme toggle (#220)"
        assert f'aria-label="{dark_label}"' in button.group(0), (
            f"/{rel} toggle has the wrong initial accessible name"
        )
        assert f'data-label-light="{light_label}"' in button.group(0)
        bootstrap = html.find("localStorage.getItem")
        stylesheet = html.find('id="main-stylesheet"')
        assert bootstrap != -1 and stylesheet != -1
        assert bootstrap < stylesheet, (
            f"/{rel} paints the stylesheet before the theme bootstrap (#220)"
        )
        assert re.search(
            r'<script src="/assets/js/theme-toggle\.js\?v=\d+" defer></script>',
            html,
        ), f"/{rel} does not link the versioned toggle script"


# --- browser guards (need Ruby + a browser) ---------------------------------


def _open(context, site_url, path):
    page = context.new_page()
    origin = urlparse(site_url).netloc
    page.route(
        "**/*",
        lambda route: route.continue_()
        if urlparse(route.request.url).netloc == origin
        else route.abort(),
    )
    response = page.goto(f"{site_url}{path}", wait_until="load")
    assert response is not None and response.status == 200, (
        f"{path} did not load (status {response.status if response else 'none'})"
    )
    page.wait_for_selector(".theme-toggle", state="visible", timeout=10_000)
    return page


@pytest.mark.parametrize("path", ["/", "/vi/"])
@pytest.mark.parametrize(
    "color_scheme,expected", [("light", "light"), ("dark", "dark")]
)
def test_first_visit_follows_the_os_preference(
    path, color_scheme, expected, built_site_url, browser
):
    """No stored choice: the painted theme matches the OS (#220)."""
    context = browser.new_context(
        viewport={"width": 1280, "height": VIEWPORT_HEIGHT},
        color_scheme=color_scheme,
    )
    try:
        page = _open(context, built_site_url, path)
        assert page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        ) == expected, (
            f"{path}: first visit with a {color_scheme} OS must paint "
            f"{expected}"
        )
    finally:
        context.close()


def test_toggle_flips_the_theme_and_persists_it(built_site_url, browser):
    """One click flips `data-theme`; the choice survives reload + pages."""
    context = browser.new_context(
        viewport={"width": 1280, "height": VIEWPORT_HEIGHT},
        color_scheme="light",
    )
    try:
        page = _open(context, built_site_url, "/")
        theme = (
            lambda: page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')"
            )
        )
        stored = (
            lambda: page.evaluate(f"() => window.localStorage.getItem('{STORAGE_KEY}')")
        )
        assert theme() == "light"
        page.locator(".theme-toggle").click()
        assert theme() == "dark", "clicking the toggle must paint dark mode"
        assert stored() == "dark", "the choice must persist in localStorage"
        page.reload(wait_until="load")
        page.wait_for_selector(".theme-toggle", state="visible")
        assert theme() == "dark", "a reload must keep the stored theme"
        page.goto(f"{built_site_url}/vi/", wait_until="load")
        page.wait_for_selector(".theme-toggle", state="visible")
        assert theme() == "dark", "the choice must survive navigation"
        page.locator(".theme-toggle").click()
        assert theme() == "light" and stored() == "light"
    finally:
        context.close()


def test_stored_choice_beats_the_os_preference(built_site_url, browser):
    """An explicit light choice stays light on a dark OS (and vice versa)."""
    for color_scheme, stored in (("dark", "light"), ("light", "dark")):
        context = browser.new_context(
            viewport={"width": 1280, "height": VIEWPORT_HEIGHT},
            color_scheme=color_scheme,
        )
        context.add_init_script(
            f'window.localStorage.setItem("{STORAGE_KEY}", "{stored}");'
        )
        try:
            page = _open(context, built_site_url, "/")
            assert page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')"
            ) == stored
        finally:
            context.close()


@pytest.mark.parametrize(
    "path,dark_label,light_label",
    [("/", LABEL_DARK_EN, LABEL_LIGHT_EN), ("/vi/", LABEL_DARK_VI, LABEL_LIGHT_VI)],
)
def test_toggle_is_keyboard_operable_with_a_stable_name(
    path, dark_label, light_label, built_site_url, browser
):
    """Real button, localized name, `aria-pressed`, Enter flips it (#220)."""
    context = browser.new_context(
        viewport={"width": 1280, "height": VIEWPORT_HEIGHT},
        color_scheme="light",
    )
    try:
        page = _open(context, built_site_url, path)
        toggle = page.locator(".theme-toggle")
        assert toggle.get_attribute("aria-label") == dark_label, (
            f"{path}: expected the accessible name {dark_label!r}"
        )
        assert toggle.get_attribute("aria-pressed") == "false"
        toggle.focus()
        assert toggle.evaluate(
            "(el) => getComputedStyle(el).outlineStyle"
        ) == "solid", f"{path}: the toggle shows no keyboard focus ring"
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-pressed") == "true"
        assert toggle.get_attribute("aria-label") == light_label, (
            f"{path}: the accessible name must follow the theme"
        )
        assert page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        ) == "dark"
    finally:
        context.close()


@pytest.mark.parametrize("width", (320, 375, 1280))
@pytest.mark.parametrize("path", ["/", "/vi/"])
def test_toggle_hit_area_without_overflow(
    path, width, built_site_url, browser
):
    """44px target beside the pill, no horizontal overflow down to 320px."""
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT}
    )
    try:
        page = _open(context, built_site_url, path)
        toggle = page.locator(".theme-toggle")
        box = toggle.bounding_box()
        assert box is not None, f"{path}: the toggle has no box at {width}px"
        assert box["width"] >= 44, f"{path}: too narrow ({box['width']})"
        assert box["height"] >= 44, f"{path}: too short ({box['height']})"
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 1, f"{path}: horizontal overflow of {overflow}px"
    finally:
        context.close()


def _run_axe_color_contrast(page):
    """Vendored axe-core, `color-contrast` rule only (offline, #207 pin)."""
    page.add_script_tag(path=str(test_axe_a11y.AXE_JS))
    page.wait_for_function("() => !!window.axe", timeout=15_000)
    return page.evaluate(
        "() => window.axe.run(document, {runOnly: ['color-contrast'], "
        "resultTypes: ['violations']}).then((results) => results.violations"
        ".map((v) => ({id: v.id, impact: v.impact, nodes: v.nodes.map((n) => "
        "({target: n.target.join(' '), html: (n.html || '').slice(0, 200)}))})))"
    )


@pytest.mark.parametrize("width", VIEWPORTS)
@pytest.mark.parametrize("path", AXE_PAGES)
@pytest.mark.parametrize("theme", ("light", "dark"))
def test_axe_color_contrast_passes_in_both_modes(
    path, width, theme, built_site_url, browser
):
    """Contrast >= 4.5:1 on home, post and tag pages in both modes (#220).

    The stored choice pins the theme independently of the OS emulation, so
    the dark run exercises the `data-theme` layer itself (not the media
    query) on a light OS — the exact path a stored dark choice takes.
    """
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        color_scheme="light",
    )
    context.add_init_script(
        f'window.localStorage.setItem("{STORAGE_KEY}", "{theme}");'
    )
    try:
        page = context.new_page()
        origin = urlparse(built_site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        response = page.goto(f"{built_site_url}{path}", wait_until="load")
        assert response is not None and response.status == 200, (
            f"{path} did not load (status {response.status if response else 'none'})"
        )
        page.wait_for_selector(".site-footer", state="attached", timeout=10_000)
        assert page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        ) == theme
        failures = []
        for violation in _run_axe_color_contrast(page):
            for node in violation["nodes"]:
                if violation["impact"] in ("serious", "critical"):
                    failures.append(
                        f"[{violation['impact']}] {violation['id']} "
                        f"target={node['target']} html={node['html']}"
                    )
        assert not failures, (
            f"axe color-contrast violations in {theme} mode at {width}px "
            f"{path}:\n" + "\n".join(f"  {line}" for line in failures)
        )
        page.close()
    finally:
        context.close()
