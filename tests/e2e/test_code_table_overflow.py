"""Guards for #151: code blocks and tables must not overflow the page at 360px.

Follow-up of #112 (reader-UX audit). The code-heavy 2016 post and Markdown
tables were never checked at real-device widths (~360px): Minima styles wide
code/table blocks with ``pre { overflow-x: auto }`` and, at phone widths,
``table { display: block; overflow-x: auto }``, so a wide block should scroll
*inside* its own container instead of pushing the page sideways. The
``figure.highlight table`` negative-margin rule (line-number tables) must stay
contained the same way.

Verification for #151 (360px and 320px, with the real ``copy-code.js``
enhancement active) found no page-level overflow, so there is deliberately no
CSS change here: these guards pin the containment so a future style edit
cannot reintroduce page-level scrolling, and prove wide content stays
reachable through inner scroll (scroll container is acceptable, clipped
content is not).

Guarded here:

- static (no Ruby, no browser): ``pre`` keeps ``overflow-x: auto`` and the
  phone-width ``table`` rule keeps ``display: block`` + ``overflow-x: auto``
  in ``_sass/minima/_base.scss``;
- browser (needs Ruby + a browser): a fixture with a wide fenced block, a
  rouge line-number (``figure.highlight`` + ``rouge-table``) block and a wide
  Markdown table, injected into a real built page with the real copy-code
  script running, keeps ``documentElement.scrollWidth <= innerWidth`` at
  360px and 320px while every wide block keeps an active inner scroller;
- the copy button keeps working (present, 44px target) without adding page
  overflow, and the wide code text stays fully reachable (readability).
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_SCSS = REPO_ROOT / "_sass" / "minima" / "_base.scss"
COPY_SCRIPT = REPO_ROOT / "assets" / "js" / "copy-code.js"
HELPER_SCRIPT = REPO_ROOT / "assets" / "js" / "site-utils.js"

PHONE_WIDTHS = (360, 320)

LONG_LINE = (
    "averylongunbreakablemethodname_chained_with_more_names_and_arguments"
    "_to_force_overflow_on_360px_viewport = some_function_call"
    "(with_long_argument, another_argument)"
)

# Fixture mirrors what the site really renders: a rouge fenced block
# (``div.highlight > pre.highlight > code``), a rouge line-number block
# (``figure.highlight > pre > code > table.rouge-table``, as produced by
# ``{% highlight ruby linenos %}``), and a kramdown Markdown table.
_FIXTURE_HTML = f"""
<div class="post-content" id="overflow-151-fixture">
  <div class="highlight"><pre class="highlight"><code>{LONG_LINE}</code></pre></div>
  <figure class="highlight"><pre><code class="language-ruby" data-lang="ruby"><table class="rouge-table"><tbody><tr><td class="gutter gl"><pre class="lineno">1
</pre></td><td class="code"><pre>{LONG_LINE}
</pre></td></tr></tbody></table></code></pre></figure>
  <table>
    <thead><tr><th>Header One</th><th>Header Two</th><th>Header Three</th><th>Header Four</th><th>Header Five</th></tr></thead>
    <tbody><tr><td>cell one with some longer text</td><td>cell two</td><td>cell three</td><td>cell four</td><td>cell five</td></tr></tbody>
  </table>
</div>
"""

_MEASURE_JS = """() => {
  const vw = window.innerWidth;
  const scrollers = [];
  for (const sel of ['#overflow-151-fixture pre', '#overflow-151-fixture table']) {
    for (const el of document.querySelectorAll(sel)) {
      const cs = getComputedStyle(el);
      scrollers.push({
        sel: el.tagName + '.' + (typeof el.className === 'string' ? el.className : ''),
        overflowX: cs.overflowX,
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      });
    }
  }
  const uncontained = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let el = walker.currentNode;
  while (el) {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && (rect.right > vw + 0.5 || rect.left < -0.5)
        && !el.classList.contains('skip-link')) {
      let node = el.parentElement, contained = false;
      while (node) {
        const ox = getComputedStyle(node).overflowX;
        if ((ox === 'auto' || ox === 'scroll') && node.scrollWidth > node.clientWidth + 1) {
          contained = true;
          break;
        }
        node = node.parentElement;
      }
      if (!contained) {
        uncontained.push(el.tagName + '.' + el.className + ' [' + rect.left.toFixed(0) + ', ' + rect.right.toFixed(0) + ']');
      }
    }
    el = walker.nextNode();
  }
  const buttons = [];
  for (const btn of document.querySelectorAll('#overflow-151-fixture .copy-code__button')) {
    const rect = btn.getBoundingClientRect();
    buttons.push({width: rect.width, height: rect.height});
  }
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: vw,
    scrollers,
    uncontained,
    buttons,
    codeText: (document.querySelector('#overflow-151-fixture code') || {textContent: ''}).textContent,
  };
}"""


def _read(path):
    return path.read_text(encoding="utf-8")


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_pre_keeps_contained_horizontal_scroll():
    """Fenced code must scroll inside its own box, never push the page."""
    scss = _read(BASE_SCSS)
    rule = re.search(r"^pre\s*\{(.*?)\}", scss, re.DOTALL | re.MULTILINE)
    assert rule, f"no site-wide pre rule found in {BASE_SCSS}"
    assert "overflow-x: auto" in rule.group(1), (
        "the site-wide pre rule must keep `overflow-x: auto` so a wide code "
        "block scrolls inside its container instead of overflowing the page (#151)"
    )


@pytest.mark.static
def test_table_keeps_contained_horizontal_scroll_on_phones():
    """Wide tables (and rouge line-number tables) must scroll, not overflow."""
    scss = _read(BASE_SCSS)
    rule = re.search(r"^table\s*\{(.*?)\n\}", scss, re.DOTALL | re.MULTILINE)
    assert rule, f"no site-wide table rule found in {BASE_SCSS}"
    body = rule.group(1)
    assert "width: 100%" in body, (
        "the site-wide table rule must keep `width: 100%` (desktop rendering untouched)"
    )
    assert "display: block" in body and "overflow-x: auto" in body, (
        "the site-wide table rule must keep the phone-width contained scroll "
        "(`display: block` + `overflow-x: auto`) so a wide table scrolls "
        "inside its container instead of overflowing the page (#151)"
    )


# --- browser guards (need Ruby + a browser) ---------------------------------


@pytest.mark.parametrize("width", PHONE_WIDTHS)
def test_wide_code_and_tables_stay_contained(width, built_site_url, browser):
    """#151: no page-level overflow at 360px/320px; inner scroll stays active.

    The fixture's long line and wide table are wider than the phone column,
    so each scroller must actually scroll (content reachable, not clipped)
    while the document itself never exceeds the viewport. The real
    copy-code script runs, pinning that the button does not change this.
    """
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    try:
        origin = urlparse(built_site_url).netloc
        page.route(
            "**/*",
            lambda route: route.continue_()
            if urlparse(route.request.url).netloc == origin
            else route.abort(),
        )
        page.goto(f"{built_site_url}/", wait_until="load")
        page.evaluate(
            "(html) => { document.body.insertAdjacentHTML('beforeend', html); }",
            _FIXTURE_HTML,
        )
        page.add_script_tag(path=str(HELPER_SCRIPT))
        page.add_script_tag(path=str(COPY_SCRIPT))
        page.wait_for_selector(
            "#overflow-151-fixture .copy-code__button",
            state="attached",
            timeout=10_000,
        )
        metrics = page.evaluate(_MEASURE_JS)

        assert metrics["scrollWidth"] <= metrics["innerWidth"], (
            f"page-level horizontal overflow at {width}px: "
            f"scrollWidth={metrics['scrollWidth']} > "
            f"innerWidth={metrics['innerWidth']} (#151)"
        )
        assert metrics["uncontained"] == [], (
            f"elements wider than the viewport with no scroll container "
            f"at {width}px: {metrics['uncontained']} (#151)"
        )

        # Every wide block scrolls inside its own container: the scroll
        # affordance is active (scrollWidth exceeds the visible box), so the
        # content is reachable instead of clipped.
        scrolled = [s for s in metrics["scrollers"] if s["scrollWidth"] > s["clientWidth"] + 1]
        assert scrolled, (
            f"the fixture must actually overflow its containers at {width}px, "
            f"or this guard proves nothing: {metrics['scrollers']}"
        )
        for scroller in scrolled:
            assert scroller["overflowX"] == "auto", (
                f"{scroller['sel']} scrolls at {width}px but its affordance is "
                f"`overflow-x: {scroller['overflowX']}`, expected `auto` (#151)"
            )

        # Copy-button behaviour is preserved: one button per fenced block,
        # 44px minimum touch target, and the wide code text is fully present.
        assert len(metrics["buttons"]) == 2, (
            f"expected a copy button on each of the 2 code blocks, got "
            f"{len(metrics['buttons'])}"
        )
        for button in metrics["buttons"]:
            assert button["width"] >= 44 and button["height"] >= 44, (
                "the copy button must keep its 44px minimum touch target, got "
                f"{button['width']:.0f}x{button['height']:.0f}"
            )
        assert LONG_LINE in metrics["codeText"], (
            "the wide code line must stay fully reachable through inner scroll"
        )
    finally:
        context.close()
