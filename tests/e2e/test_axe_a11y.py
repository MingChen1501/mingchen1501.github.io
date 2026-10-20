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

Accepted exceptions (serious, kept green deliberately — each needs an
owner/UX decision tracked in the follow-up issue instead of a drive-by fix):

- `label-content-name-mismatch` on `.lang-switcher`: the visible label is the
  ISO language code (`EN`/`VI`) while the accessible name is the full
  translated action. The compact pill (icon + code, full name as
  `aria-label`/`title`) is pinned by the #122 guards, so renaming the visible
  text or the accessible name needs an i18n/UX decision.
- `label-content-name-mismatch` on `.u-email`: the visible text is the raw
  address while the accessible name is the localized recipient label. That
  label is pinned by the #150 guards (a stable name that Cloudflare Email
  Obfuscation cannot rewrite), so reconciling WCAG 2.5.3 with #150 needs an
  owner decision.
- `color-contrast` on `blockquote > p` (coffee post EN+VI): blockquote text is
  `$brand-color` (`#818181`) on `#fdfdfd` (3.82:1, needs 4.5:1) from the minima
  auto skin. Changing the brand colour restyles the whole site, so it needs a
  design decision.
- `object-alt` on `/portfolio/` `<object>`: the resume PDF embed has no
  title/`aria-label` (it does ship an in-element fallback link). Fixing the
  markup needs an owner decision (label the object vs. replace the embed).
  The waiver is scoped to Chromium/Firefox: axe's `object-is-loaded`
  matcher only applies when the fallback renders zero boxes, and headless
  WebKit (no PDF plugin intercept) renders the fallback inline, so the
  rule never fires there (#209).

Strictness: an unexpected serious/critical violation fails the run, and an
accepted exception that no longer reproduces *also* fails (stale exceptions
must be removed, not carried forever).
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest

import conftest

REPO_ROOT = Path(__file__).resolve().parents[2]
AXE_JS = REPO_ROOT / "tests" / "e2e" / "axe-core" / "axe.min.js"
AXE_PIN_DOC = REPO_ROOT / "tests" / "e2e" / "axe-core" / "AXE_PIN.md"

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

# Every accepted exception: the axe rule, a substring of the node's CSS
# target selector, and why the fix is deferred instead of done here.
ACCEPTED = [
    {
        "rule": "label-content-name-mismatch",
        "target": ".lang-switcher",
        "reason": (
            "visible label is the ISO language code (EN/VI) while the "
            "accessible name is the full translated action; the compact "
            "pill is pinned by the #122 guards, renaming needs an "
            "i18n/UX decision"
        ),
    },
    {
        "rule": "label-content-name-mismatch",
        "target": ".u-email",
        "reason": (
            "visible raw address vs. localized recipient aria-label; the "
            "label is pinned by the #150 guards (Cloudflare obfuscation "
            "stability), reconciling WCAG 2.5.3 with #150 needs an owner "
            "decision"
        ),
    },
    {
        "rule": "color-contrast",
        "target": "blockquote",
        "reason": (
            "blockquote $brand-color #818181 on #fdfdfd is 3.82:1 (needs "
            "4.5:1) from the minima auto skin; changing the brand colour "
            "restyles the whole site, needs a design decision"
        ),
    },
    {
        "rule": "object-alt",
        "target": "object",
        # No "engines" key means every engine; this waiver is scoped because
        # axe's `object-is-loaded` matcher only applies when the <object>
        # fallback renders zero boxes. Chromium/Firefox hide the fallback
        # behind the PDF plugin area (the rule fires); headless WebKit has
        # no PDF plugin intercept, so it renders the in-element fallback
        # link inline and the rule never applies there (#209).
        "engines": ("chromium", "firefox"),
        "reason": (
            "the /portfolio/ resume PDF <object> has no title/aria-label "
            "(it ships an in-element fallback link); labelling vs. "
            "replacing the embed needs an owner decision"
        ),
    },
]

# (rule, target-substring) pairs observed during this module's browser run, and
# how many page x viewport cases executed. The build test at the end of this
# file fails on accepted exceptions that no longer reproduce anywhere, so
# fixed issues cannot linger as blanket waivers. Both live in module globals
# (not a module-scoped fixture): `conftest.py` reorders the suite static-first,
# which finalizes module-scoped fixtures before the browser group runs.
_OBSERVED: set[tuple[str, str]] = set()
_CASES_RUN = 0
_EXPECTED_CASES = len(VIEWPORTS) * len(PAGES)


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
    """Fail on serious/critical findings outside the documented exceptions."""
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

        global _CASES_RUN
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
                    else:
                        _OBSERVED.add((match["rule"], match["target"]))
                elif violation["impact"] in REPORT_ONLY_IMPACTS:
                    advisory.append(line)
                else:
                    unexpected.append(f"{line} (unknown impact)")
        _CASES_RUN += 1
        if advisory:
            print(f"\naxe advisory (non-blocking) for {width}px {path}:")
            for line in advisory:
                print(f"  {line}")
        assert not unexpected, (
            f"axe serious/critical violations at {width}px {path} outside the "
            f"accepted exceptions:\n" + "\n".join(f"  {line}" for line in unexpected)
        )
    finally:
        context.close()


def test_accepted_exceptions_match_this_build(built_site, browser_name):
    """The waiver list above must describe the real build (no silent drift).

    Without Ruby there is no build to judge, so this needs the session build;
    it re-reads the rendered pages and asserts every accepted (rule, target)
    pair occurs at least once somewhere, catching include changes that move
    or rename the waived nodes without touching axe. On a full module run it
    additionally fails on accepted exceptions the browser cases never
    observed, so fixed issues cannot linger as waivers (partial `-k` runs
    skip that half: not every case executed). Waivers scoped to a subset of
    engines (the ``engines`` key, #209) are only required on those engines.
    """
    selector_snippets = {
        (entry["rule"], entry["target"]): False for entry in ACCEPTED
    }
    targets = {
        ".lang-switcher": 'class="lang-switcher"',
        ".u-email": 'class="u-email"',
        "blockquote": "<blockquote",
        "object": "<object",
    }
    portfolio_only = {"object"}
    checked = 0
    for path in PAGES:
        html = _read(built_site / path.lstrip("/").rstrip("/") / "index.html") \
            if (built_site / path.lstrip("/").rstrip("/") / "index.html").is_file() \
            else _read(built_site / path.lstrip("/"))
        checked += 1
        for (rule, target), _ in selector_snippets.items():
            if target in portfolio_only and path != "/portfolio/":
                continue
            if targets[target] in html:
                selector_snippets[(rule, target)] = True
    missing = [key for key, seen in selector_snippets.items() if not seen]
    assert checked == len(PAGES)
    assert not missing, (
        "accepted axe exception targets missing from the build — the markup "
        f"moved, update ACCEPTED in {Path(__file__).name}: {missing}"
    )
    # The suite pins the vendored scanner version (see the static guard); the
    # rule ids themselves ship in that bundle, so a scanner swap that drops a
    # waived rule is caught here rather than silently passing.
    bundle = _read(AXE_JS)
    for rule in {entry["rule"] for entry in ACCEPTED}:
        assert rule in bundle, f"vendored axe bundle has no {rule} rule"

    if _CASES_RUN != _EXPECTED_CASES:
        print(
            f"\nskipping the stale-exception check: {_CASES_RUN}/"
            f"{_EXPECTED_CASES} browser cases ran (partial selection?)"
        )
        return
    stale = [
        entry
        for entry in ACCEPTED
        if browser_name in entry.get("engines", conftest.BROWSER_NAMES)
        and (entry["rule"], entry["target"]) not in _OBSERVED
    ]
    assert not stale, (
        "accepted axe exceptions that no longer reproduce — remove them "
        f"from ACCEPTED in {Path(__file__).name}: "
        + "; ".join(f"{entry['rule']} ({entry['target']})" for entry in stale)
    )
