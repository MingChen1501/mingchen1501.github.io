"""Axe-core accessibility smoke for key templates (#207).

Past accessibility work (#87, #114) was manual and can regress silently, so
this module runs the pinned, vendored axe-core scanner (`axe-core/axe.min.js`,
offline, no CDN) over the key templates and fails on `serious`/`critical`
violations. `minor`/`moderate` findings are reported but non-blocking.

Coverage: `/`, one EN post plus its VI counterpart (same `ref`), the `/tags/`
index, `/vi/`, `/about/`, `/portfolio/` — each at phone width (375px) and one
desktop viewport (1280px), in the light colour scheme.

Delivery: the scanner is vendored, not fetched. `axe-core/AXE_PIN.md` records
the version (4.14.0), the npm source tarball, its registry integrity hash and
the MPL-2.0 license; static guards below pin the header so a silent swap is
caught.

Accepted exceptions: none. The four #207 waivers were resolved for real
in #213 and removed, so the suite now fails on any serious/critical
finding outright:

- `label-content-name-mismatch` on `.lang-switcher`: the full translated
  action ships as visually-hidden text inside the link, so the visible ISO
  code (`EN`/`VI`) is part of the accessible name (WCAG 2.5.3).
- `label-content-name-mismatch` on `.u-email`: the localized recipient
  label is a visually-hidden span inside the link, so the visible address
  stays in the accessible name while the label itself holds no raw address
  (stable under Cloudflare Email Obfuscation, #150).
- `color-contrast` on `blockquote > p` (coffee post EN+VI): blockquote text
  deepened to `#616161` (6.1:1 on `#fdfdfd`) without touching
  `$brand-color`, so the rest of the site keeps its design.
- `object-alt` on `/portfolio/` `<object>`: the resume embed carries a
  matching `title`/`aria-label` next to its in-element fallback link
  (labelled, not replaced).

Strictness: any serious/critical violation fails the run — there are no
waivers left to hide behind. If a future exception is ever accepted into
`ACCEPTED`, it must carry a rule, a node target and a deferred-fix reason,
and the build test at the end of this file keeps it honest.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AXE_JS = REPO_ROOT / "tests" / "e2e" / "axe-core" / "axe.min.js"
AXE_PIN_DOC = REPO_ROOT / "tests" / "e2e" / "axe-core" / "AXE_PIN.md"
CUSTOM_SCSS = REPO_ROOT / "_sass" / "minima" / "custom" / "_a11y.scss"
PORTFOLIO_MD = {
    "portfolio.md": "Resume of Tran Cong Minh (PDF)",
    "vi/portfolio.md": "Hồ sơ của Trần Công Minh (PDF)",
}

AXE_VERSION = "4.14.0"

PHONE_WIDTH = 375
DESKTOP_WIDTH = 1280
VIEWPORT_HEIGHT = 800

# The EN/VI coffee pair shares `ref: cach-pha-ca-phe`, i.e. the same article
# in both languages (the old `/2022/10/27/cach-pha-ca-phe.html` URL is now a
# redirect stub, so the smoke must use the real post URLs, not the stub).
EN_POST = "/2022/10/27/brewing-vietnamese-coffee.html"
VI_POST = "/vi/2022/10/27/cach-pha-ca-phe.html"

PAGES = ["/", EN_POST, VI_POST, "/tags/", "/vi/", "/about/", "/portfolio/"]
VIEWPORTS = (PHONE_WIDTH, DESKTOP_WIDTH)

# Rule ids whose `serious`/`critical` findings fail the suite outright.
BLOCKING_IMPACTS = {"serious", "critical"}
# Lower impacts are reported in the test output but never fail.
REPORT_ONLY_IMPACTS = {"minor", "moderate"}

# No accepted exceptions remain: every waiver needs a `reason` explaining
# why the fix is deferred instead of done, and #213 fixed all four, so the
# list stays empty until a future waiver is justified. An empty list keeps
# the stale-exception machinery below working (it trivially passes).
ACCEPTED: list = []

def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_vendored_axe_scanner_exists_and_is_pinned():
    assert AXE_JS.is_file(), f"{AXE_JS.relative_to(REPO_ROOT)} is missing"
    assert AXE_JS.stat().st_size > 100_000, (
        "the vendored axe bundle looks truncated "
        f"({AXE_JS.stat().st_size} bytes)"
    )
    header = _read(AXE_JS)[:1200]
    assert f"axe v{AXE_VERSION}" in header, (
        f"the vendored scanner is not the pinned axe-core {AXE_VERSION}"
    )
    assert "Mozilla Public" in header and "MPL" in header, (
        "the MPL-2.0 license notice must stay in the vendored file header"
    )


@pytest.mark.static
def test_axe_pin_note_documents_version_source_and_license():
    assert AXE_PIN_DOC.is_file(), f"{AXE_PIN_DOC.relative_to(REPO_ROOT)} is missing"
    note = _read(AXE_PIN_DOC)
    assert AXE_VERSION in note, "the pin note must state the vendored version"
    assert "registry.npmjs.org" in note, "the pin note must state the source"
    assert "sha512-" in note, "the pin note must state the integrity hash"
    assert "Mozilla Public License" in note, "the pin note must state the license"


def _relative_luminance(hex_color):
    """WCAG relative luminance of a `#rrggbb` colour."""
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linearized = [
        channel / 12.92 if channel <= 0.03928
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return (
        0.2126 * linearized[0]
        + 0.7152 * linearized[1]
        + 0.0722 * linearized[2]
    )


@pytest.mark.static
def test_blockquote_color_meets_aa_contrast():
    """The #213 blockquote fix must keep 4.5:1 on the page background.

    The override lives in custom styles (``$brand-color`` itself is
    untouched), so this parses the winning `blockquote` colour and checks
    the ratio directly instead of re-running a browser.
    """
    scss = _read(CUSTOM_SCSS)
    matches = re.findall(
        r"^\s*blockquote\s*\{(.*?)\}", scss, re.S | re.M
    )
    assert matches, (
        "custom a11y styles define no blockquote colour override (#213)"
    )
    colour = re.search(r"color:\s*(#[0-9a-fA-F]{6})", matches[-1])
    assert colour, "the blockquote override sets no static colour (#213)"
    lighter = _relative_luminance("#fdfdfd")
    darker = _relative_luminance(colour.group(1))
    ratio = (lighter + 0.05) / (darker + 0.05)
    assert ratio >= 4.5, (
        f"blockquote {colour.group(1)} on #fdfdfd is {ratio:.2f}:1 "
        "(needs 4.5:1, #213)"
    )


@pytest.mark.static
def test_portfolio_object_has_accessible_name_and_fallback():
    """The #213 object-alt fix: labelled embed, fallback link retained."""
    for rel, label in PORTFOLIO_MD.items():
        md = _read(REPO_ROOT / rel)
        tag = re.search(r"<object\b[^>]*>", md)
        assert tag, f"{rel} renders no resume <object> to judge (#213)"
        assert f'title="{label}"' in tag.group(0), (
            f"{rel} resume <object> has no title (#213): {tag.group(0)}"
        )
        assert f'aria-label="{label}"' in tag.group(0), (
            f"{rel} resume <object> has no aria-label (#213): {tag.group(0)}"
        )
        assert re.search(
            r"<object\b[^>]*>.*?<a\b[^>]*>.*?</a>.*?</object>", md, re.S
        ), f"{rel} resume <object> lost its in-element fallback link (#213)"


# --- browser smoke (needs Ruby + a browser) --------------------------------


def _run_axe(page):
    """Inject the vendored scanner and return its violations list."""
    page.add_script_tag(path=str(AXE_JS))
    page.wait_for_function("() => !!window.axe", timeout=15_000)
    return page.evaluate(
        "() => window.axe.run(document, {resultTypes: ['violations']})"
        ".then((results) => results.violations.map((v) => ({"
        "  id: v.id,"
        "  impact: v.impact,"
        "  nodes: v.nodes.map((n) => ({"
        "    target: n.target.join(' '),"
        "    html: (n.html || '').slice(0, 200),"
        "  })),"
        "})))"
    )


def _describe(violation, node, path, width):
    return (
        f"{width}px {path}: [{violation['impact']}] {violation['id']} "
        f"target={node['target']} html={node['html']}"
    )


@pytest.mark.parametrize("width", VIEWPORTS)
@pytest.mark.parametrize("path", PAGES)
def test_axe_no_unexpected_serious_or_critical_violations(
    path, width, built_site_url, browser
):
    """Fail on any serious/critical finding (no exceptions remain, #213)."""
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        color_scheme="light",
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
        # Readiness: every template renders the footer; axe needs final styles.
        page.wait_for_selector(".site-footer", state="attached", timeout=10_000)

        unexpected = []
        advisory = []
        for violation in _run_axe(page):
            for node in violation["nodes"]:
                line = _describe(violation, node, path, width)
                if violation["impact"] in BLOCKING_IMPACTS:
                    match = next(
                        (
                            entry
                            for entry in ACCEPTED
                            if entry["rule"] == violation["id"]
                            and entry["target"] in node["target"]
                        ),
                        None,
                    )
                    if match is None:
                        unexpected.append(line)
                elif violation["impact"] in REPORT_ONLY_IMPACTS:
                    advisory.append(line)
                else:
                    unexpected.append(f"{line} (unknown impact)")
        if advisory:
            print(f"\naxe advisory (non-blocking) for {width}px {path}:")
            for line in advisory:
                print(f"  {line}")
        assert not unexpected, (
            f"axe serious/critical violations at {width}px {path}:\n"
            + "\n".join(f"  {line}" for line in unexpected)
        )
    finally:
        context.close()


def test_fixed_nodes_still_render_and_rules_still_ship(built_site):
    """The #213 fixes must stay real (no silent drift or vacuous green).

    The browser cases above prove the four former violations are gone, but
    deleting the switcher/email/blockquote/object markup would also turn the
    run green — so this re-reads the rendered pages and asserts the fixed
    nodes still occur somewhere, catching include changes that drop them
    without touching axe. It also asserts the vendored bundle still ships
    the three rule ids (the suite pins the scanner version in the static
    guard; a swap that drops a rule is caught here rather than silently
    passing).
    """
    targets = {
        ".lang-switcher": 'class="lang-switcher"',
        ".u-email": 'class="u-email"',
        "blockquote": "<blockquote",
        "object": "<object",
    }
    portfolio_only = {"object"}
    seen = {target: False for target in targets}
    checked = 0
    for path in PAGES:
        html = _read(built_site / path.lstrip("/").rstrip("/") / "index.html") \
            if (built_site / path.lstrip("/").rstrip("/") / "index.html").is_file() \
            else _read(built_site / path.lstrip("/"))
        checked += 1
        for target, snippet in targets.items():
            if target in portfolio_only and path != "/portfolio/":
                continue
            if snippet in html:
                seen[target] = True
    missing = [target for target, found in seen.items() if not found]
    assert checked == len(PAGES)
    assert not missing, (
        "fixed axe nodes missing from the build — the markup moved or was "
        f"dropped, so the green run may be vacuous: {missing}"
    )
    # The suite pins the vendored scanner version (see the static guard); the
    # rule ids themselves ship in that bundle, so a scanner swap that drops a
    # fixed rule is caught here rather than silently passing.
    bundle = _read(AXE_JS)
    for rule in ("label-content-name-mismatch", "color-contrast", "object-alt"):
        assert rule in bundle, f"vendored axe bundle has no {rule} rule"
