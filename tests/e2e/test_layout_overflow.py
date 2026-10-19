"""Layout regression guard for #50: no horizontal scroll on phones.

`img { max-width: 100%; padding: 20px }` used the default content-box sizing,
so a full-width image rendered `100% + 40px` wide and pushed every page that
shows one ~40px past the viewport. The fix is the site-wide `img` rule in
`_sass/minima/_base.scss` (padding now lives inside `max-width: 100%`).

Unlike the comments suite, this guard needs the *real* site, so it uses the
session-wide `built_site`/`built_site_url` fixtures from `conftest.py` (one
`bundle exec jekyll build`, served once over loopback HTTP). The dev
environment is used deliberately: it skips the external giscus embed, keeping
the run hermetic. Requests to third-party origins (only the Font Awesome CDN
stylesheet) are aborted for the same reason - they cannot affect layout, which
is fully defined by the local `style.css`.

Covered page kinds (acceptance from #50): a post page, the home list, the
`/tags/` index, and every `/tags/<tag>/` page present in the build — each in
both languages since #93 (`/`, `/vi/`, `/tags/`, `/vi/tags/`, …). The
per-tag pages are added by PR #48; until they exist in the build the
corresponding case skips with an explicit reason instead of passing silently.
"""

import contextlib
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_SCSS = REPO_ROOT / "_sass" / "minima" / "_base.scss"

PHONE_WIDTH = 375
SCHEMES = ("light", "dark")
PAGE_KINDS = ("post", "home-list", "tags-index", "tag-page")

# Interactive elements of the layout: `document.documentElement` must not be
# wider than the viewport, and no image may overhang it or lose its ratio.
_MEASURE_JS = """
() => {
  const vw = window.innerWidth;
  const images = [];
  for (const el of document.querySelectorAll('img')) {
    const rect = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
    const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
    images.push({
      src: (el.currentSrc || el.src || '').split('/').pop(),
      right: rect.right,
      contentWidth: rect.width - padX,
      contentHeight: rect.height - padY,
      naturalWidth: el.naturalWidth,
      naturalHeight: el.naturalHeight,
    });
  }
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: vw,
    images,
  };
}
"""


@pytest.fixture(scope="session")
def site_pages(built_site):
    """Map each #50 page kind to the built paths that should be checked."""
    pages = {kind: [] for kind in PAGE_KINDS}
    for html in sorted(built_site.rglob("*.html")):
        text = html.read_text(encoding="utf-8", errors="replace")
        # Skip redirect stubs and standalone pages that do not use the site
        # stylesheet; they are not part of the blog layout.
        if 'id="main-stylesheet"' not in text or 'http-equiv="refresh"' in text:
            continue
        rel = "/" + html.relative_to(built_site).as_posix()
        if rel.startswith("/tests/"):
            continue
        if 'class="post h-entry"' in text:
            pages["post"].append(rel)
        elif rel in ("/tags/index.html", "/vi/tags/index.html"):
            pages["tags-index"].append(rel)
        elif rel.startswith("/tags/") or re.fullmatch(r"/vi/tags/[^/]+/index.html", rel):
            pages["tag-page"].append(rel)
        elif (
            rel == "/index.html"
            or re.fullmatch(r"/page\d+/index.html", rel)
            or rel == "/vi/index.html"
        ):
            pages["home-list"].append(rel)
    return pages


@contextlib.contextmanager
def _phone_page(browser, site_url, scheme):
    """A 375px context in the given colour scheme, with CDNs blocked."""
    context = browser.new_context(
        viewport={"width": PHONE_WIDTH, "height": 900}, color_scheme=scheme
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


def _check_page(page, site_url, path, scheme):
    page.goto(f"{site_url}{path}", wait_until="load")
    metrics = page.evaluate(_MEASURE_JS)

    assert metrics["scrollWidth"] <= metrics["innerWidth"], (
        f"{path}: horizontal overflow at {PHONE_WIDTH}px ({scheme} theme): "
        f"scrollWidth={metrics['scrollWidth']} > "
        f"innerWidth={metrics['innerWidth']} (#50)"
    )

    for image in metrics["images"]:
        if not image["naturalWidth"] or not image["naturalHeight"]:
            continue  # broken/undecoded image, covered by other tooling
        assert image["right"] <= metrics["innerWidth"] + 0.5, (
            f"{path}: image {image['src']} overhangs the viewport at "
            f"{PHONE_WIDTH}px ({scheme} theme): right edge "
            f"{image['right']:.1f} > innerWidth {metrics['innerWidth']}"
        )
        natural_ratio = image["naturalWidth"] / image["naturalHeight"]
        rendered_ratio = image["contentWidth"] / image["contentHeight"]
        assert abs(rendered_ratio - natural_ratio) <= 0.01 * natural_ratio, (
            f"{path}: image {image['src']} is distorted ({scheme} theme): "
            f"rendered ratio {rendered_ratio:.3f} != natural {natural_ratio:.3f}"
        )
        assert image["contentWidth"] <= image["naturalWidth"] + 1, (
            f"{path}: image {image['src']} is upscaled ({scheme} theme): "
            f"{image['contentWidth']:.1f}px > {image['naturalWidth']}px"
        )


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("kind", PAGE_KINDS)
def test_no_horizontal_scroll_at_375px(kind, scheme, site_pages, built_site_url, browser):
    paths = site_pages[kind]
    if not paths:
        if kind == "tag-page":
            pytest.skip(
                "no `/tags/<tag>/` page in this build - the per-tag pages are "
                "added by PR #48; this case measures them as soon as they exist"
            )
        pytest.fail(f"no built page found for the {kind!r} #50 acceptance case")

    for path in paths:
        with _phone_page(browser, built_site_url, scheme) as page:
            _check_page(page, built_site_url, path, scheme)


def test_guard_measures_post_pages_that_contain_images(built_site, site_pages):
    """A pass only means something if the measured posts really show images."""
    with_images = [
        path
        for path in site_pages["post"]
        if "<img" in (built_site / path.lstrip("/")).read_text(
            encoding="utf-8", errors="replace"
        )
    ]
    assert with_images, (
        "no built post page contains an <img>, so the #50 overflow guard would "
        "not exercise the image sizing rule"
    )


@pytest.mark.static
def test_img_rule_keeps_padding_inside_max_width():
    """Static backstop for the #50 fix, runnable without Ruby or a browser."""
    scss = BASE_SCSS.read_text(encoding="utf-8")
    rule = re.search(r"^img\s*\{(.*?)\}", scss, re.DOTALL | re.MULTILINE)
    assert rule, f"no site-wide img rule found in {BASE_SCSS}"
    body = rule.group(1)
    assert "max-width: 100%" in body, (
        "the site-wide img rule must still cap images at the content width"
    )
    assert re.search(r"box-sizing:\s*border-box", body), (
        "the site-wide img rule must use border-box sizing so its padding stays "
        "inside `max-width: 100%`; content-box sizing re-introduces the ~40px "
        "horizontal overflow from #50"
    )
