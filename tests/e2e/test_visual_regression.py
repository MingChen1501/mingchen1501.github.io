"""Visual regression baselines with Playwright screenshots (#208).

E2E coverage guards markup, layout math and asset URLs, but nothing fails when
a CSS/layout refactor visibly breaks a page (sidebar, tag pages, post layout).
This module screenshots a fixed page set at three viewports and fails when the
fresh capture differs from the committed baseline beyond a small threshold.

Page set (EN plus VI, #208): the home list, one EN post with its VI twin, the
`/tags/` index with its VI twin, one tag page with its VI twin, about with its
VI twin, and portfolio with its VI twin.

Determinism: every capture uses the shared dev build (the external giscus
embed is never fetched, analytics only renders in production), blocks
third-party requests, pins the light colour scheme with reduced motion,
disables animations/transitions/caret blinking via injected CSS, waits for
webfonts (`document.fonts.ready`) and for every image to decode (scrolling
once through the page so lazy-loaded images settle), then screenshots the
full page. Baselines are half-scale JPEG (`SCALE`, `JPEG_QUALITY`) so 36
captures stay under the 2 MB budget; downscaling plus JPEG encode/decode is
deterministic for identical pixels, so the threshold only absorbs
cross-machine rasterization noise, not the format.

Update the baselines after an intentional visual change:

    UPDATE_BASELINES=1 python -m pytest tests/e2e/test_visual_regression.py -q

or `script/update-visual-baselines`. CI never sets `UPDATE_BASELINES`, so an
above-threshold diff fails there; a missing baseline also fails with the
update command in the message instead of passing silently.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from urllib.parse import urlparse

from io import BytesIO

import pytest
from PIL import Image, ImageChops

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = Path(__file__).resolve().parent / "visual" / "baseline"

# Fixed capture geometry (#208): phone, tablet, desktop.
VIEWPORT_WIDTHS = (375, 768, 1280)
VIEWPORT_HEIGHT = 900

# JPEG keeps 36 full-page captures under the 2 MB budget; the static
# `test_baseline_budget` guard below pins that ceiling. Captures are stored at
# half scale (`SCALE`): layout regressions still move thousands of pixels, but
# photographic post images stop dominating the budget.
IMAGE_TYPE = "jpeg"
JPEG_QUALITY = 60
SCALE = 0.5

# A pixel counts as changed when any channel differs by more than this
# (absorbs subpixel font rasterization noise between machines); the capture
# fails when changed pixels exceed this fraction of the image.
CHANNEL_TOLERANCE = 12
MAX_DIFF_FRACTION = 0.01

# 2 MB ceiling from the #208 acceptance criteria.
BASELINE_BUDGET_BYTES = 2 * 1024 * 1024

# (baseline stem, built path). Post pair from test_post_chrome_i18n.py.
CASES = (
    ("home-en", "/index.html"),
    ("home-vi", "/vi/index.html"),
    ("post-en", "/2022/10/27/brewing-vietnamese-coffee.html"),
    ("post-vi", "/vi/2022/10/27/cach-pha-ca-phe.html"),
    ("tags-index-en", "/tags/index.html"),
    ("tags-index-vi", "/vi/tags/index.html"),
    ("tag-page-en", "/tags/doi-song/index.html"),
    ("tag-page-vi", "/vi/tags/doi-song/index.html"),
    ("about-en", "/about/index.html"),
    ("about-vi", "/vi/about/index.html"),
    ("portfolio-en", "/portfolio/index.html"),
    ("portfolio-vi", "/vi/portfolio/index.html"),
)

# Kills animation/transition/caret nondeterminism; the repo ships no keyframe
# animations, but smooth scrolling and blinking carets must not smear a shot.
_FREEZE_CSS = """
*, *::before, *::after {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
  caret-color: transparent !important;
}
"""

_SETTLE_JS = """
async () => {
  await document.fonts.ready;
  const images = Array.from(document.images);
  await Promise.all(images.map((img) => {
    if (img.complete && img.naturalWidth > 0) return Promise.resolve();
    return new Promise((resolve) => {
      img.addEventListener('load', resolve, { once: true });
      img.addEventListener('error', resolve, { once: true });
      setTimeout(resolve, 5000);
    });
  }));
  return {
    imageCount: images.length,
    decoded: images.filter((i) => i.complete && i.naturalWidth > 0).length,
  };
}
"""


def _baseline_path(stem, width):
    return BASELINE_DIR / f"{stem}@{width}.jpg"


def _diff_fraction(baseline_bytes, fresh_bytes):
    """Fraction of pixels whose channels differ beyond CHANNEL_TOLERANCE."""
    baseline = Image.open(BytesIO(baseline_bytes)).convert("RGB")
    fresh = Image.open(BytesIO(fresh_bytes)).convert("RGB")
    if baseline.size != fresh.size:
        return None
    diff = ImageChops.difference(baseline, fresh)
    channels = [
        channel.point(lambda v: 255 if v > CHANNEL_TOLERANCE else 0)
        for channel in diff.split()
    ]
    mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    changed = mask.histogram()[255]
    total = baseline.size[0] * baseline.size[1]
    return changed / total


@contextlib.contextmanager
def _stable_page(browser, site_url, width):
    """A light-scheme, reduced-motion context with third-party requests cut."""
    context = browser.new_context(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        color_scheme="light",
        reduced_motion="reduce",
        device_scale_factor=1,
    )
    try:
        page = context.new_page()
        origin = urlparse(site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        yield page
    finally:
        context.close()


def _process(raw_png):
    """Downscale a full-page capture and encode the stored/compared bytes.

    Identical for baselines and fresh captures (deterministic Lanczos +
    deterministic JPEG settings), so the threshold only sees rendering
    differences, never format noise.
    """
    image = Image.open(BytesIO(raw_png)).convert("RGB")
    width, height = image.size
    image = image.resize((max(1, int(width * SCALE)), max(1, int(height * SCALE))), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, IMAGE_TYPE.upper(), quality=JPEG_QUALITY)
    return buffer.getvalue()


def _capture(page, site_url, path):
    """Load the page, settle time-dependent content, screenshot full page."""
    response = page.goto(f"{site_url}{path}", wait_until="load")
    assert response is not None and response.status == 200, (
        f"{path} did not load (status {response.status if response else 'none'})"
    )
    page.add_style_tag(content=_FREEZE_CSS)
    # Walk the page so lazy-loaded images decode, then settle at the top.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(400)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
    stats = page.evaluate(_SETTLE_JS)
    assert stats["decoded"] == stats["imageCount"], (
        f"{path}: only {stats['decoded']}/{stats['imageCount']} images decoded; "
        "a half-loaded image would make the baseline flaky"
    )
    return _process(page.screenshot(full_page=True))


def _case_ids():
    return [f"{stem}@{width}" for stem, _ in CASES for width in VIEWPORT_WIDTHS]


@pytest.mark.parametrize(
    "stem,path,width",
    [(stem, path, width) for stem, path in CASES for width in VIEWPORT_WIDTHS],
    ids=_case_ids(),
)
def test_visual_baseline(stem, path, width, built_site_url, browser, tmp_path):
    baseline = _baseline_path(stem, width)
    update = os.environ.get("UPDATE_BASELINES") == "1"
    if not baseline.is_file() and not update:
        pytest.fail(
            f"missing baseline {baseline.relative_to(REPO_ROOT)}; regenerate it "
            "with `UPDATE_BASELINES=1 python -m pytest "
            "tests/e2e/test_visual_regression.py -q` (#208)"
        )
    with _stable_page(browser, built_site_url, width) as page:
        fresh = _capture(page, built_site_url, path)
    if update:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes(fresh)
        return
    fraction = _diff_fraction(baseline.read_bytes(), fresh)
    if fraction is None:
        fresh_path = tmp_path / f"{stem}@{width}.jpg"
        fresh_path.write_bytes(fresh)
        pytest.fail(
            f"{stem}@{width}: screenshot size differs from the baseline "
            f"({baseline.relative_to(REPO_ROOT)}); the page height changed, "
            f"which is itself a visual regression. Fresh capture kept at "
            f"{fresh_path}. If the change is intentional, regenerate baselines "
            "with `UPDATE_BASELINES=1 python -m pytest "
            "tests/e2e/test_visual_regression.py -q` (#208)"
        )
    assert fraction <= MAX_DIFF_FRACTION, (
        f"{stem}@{width}: {fraction:.4%} of pixels differ from the baseline "
        f"(>{MAX_DIFF_FRACTION:.2%} allowed, channel tolerance "
        f"{CHANNEL_TOLERANCE}); if the change is intentional, regenerate "
        "baselines with `UPDATE_BASELINES=1 python -m pytest "
        "tests/e2e/test_visual_regression.py -q` (#208)"
    )


@pytest.mark.static
def test_baseline_budget():
    """Baselines must exist for every case and stay under the 2 MB budget."""
    missing = [
        _baseline_path(stem, width).relative_to(REPO_ROOT).as_posix()
        for stem, _ in CASES
        for width in VIEWPORT_WIDTHS
        if not _baseline_path(stem, width).is_file()
    ]
    assert not missing, (
        "missing visual baselines (#208); regenerate them with "
        "`UPDATE_BASELINES=1 python -m pytest "
        "tests/e2e/test_visual_regression.py -q`:\n" + "\n".join(missing)
    )
    total = sum(
        _baseline_path(stem, width).stat().st_size
        for stem, _ in CASES
        for width in VIEWPORT_WIDTHS
    )
    assert total <= BASELINE_BUDGET_BYTES, (
        f"visual baselines use {total / 1024:.0f} KB "
        f"(>{BASELINE_BUDGET_BYTES / 1024 / 1024:.0f} MB budget, #208); lower "
        "`JPEG_QUALITY` in tests/e2e/test_visual_regression.py and regenerate"
    )
