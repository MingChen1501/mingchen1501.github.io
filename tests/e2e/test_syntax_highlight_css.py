"""Guards for #275: Rouge syntax-highlight CSS ships only on code pages.

The live render-blocking stylesheet carried ~12.4KB of Rouge ``.highlight``
token rules (~25% of the file, 319 of the 345 ``.highlight`` rules) on every
page kind, including pages that render zero code blocks. This is the CSS
analogue of #253, which gated the post-only scripts the same way (2 fewer
requests, ~5KB saved on non-post views).

Split (all in the main pipeline, GitHub Pages ``--safe`` compatible):

- the light/dark Rouge token mixins moved verbatim from
  ``_sass/minima/skins/auto.scss`` into ``_sass/minima/_syntax-highlight.scss``
  (definitions only, pure colour literals);
- ``assets/css/syntax.scss`` includes both mixins in the exact old cascade
  order (light, no-JS OS-preference dark, explicit ``data-theme`` dark, its
  no-JS fallback, explicit light), so code pages that load both sheets
  render identically to the old single stylesheet;
- the structural ``div.highlight`` / ``code.highlighter-rouge`` rules stay
  in the main stylesheet (inline code needs them, no token colours), and
  the ``@media print`` repins stay in ``minima/custom/_print.scss``;
- ``_includes/head.html`` links ``syntax.css`` with the same ``?v=``
  build token only when the rendered page contains Rouge output
  (``class="highlight"``, exactly what Rouge/kramdown emit for fenced
  code blocks), so code-free pages skip the second download.

Guarded here:

- static (no Ruby, no browser): the head gate shape (conditional, same
  token, after the main sheet), the Sass split (token emission lives only
  in the syntax entry, print repins untouched), and the marker/link
  invariant the gate implements;
- built (needs Ruby, no browser): every built page either carries the
  Rouge marker and links both sheets, or carries neither; the code-free
  main stylesheet holds no token rules and is >= 20% smaller than the old
  single file; the syntax sheet carries the token layers;
- fixture rebuild (needs Ruby): a copied tree with a real fenced-code
  post proves a code-bearing page links both sheets with one token while
  its code-free home still skips the second sheet (no published post
  ships highlighted code today, so the real build cannot exercise this).
"""

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest

import conftest
import test_stylesheet_cache_version

REPO_ROOT = Path(__file__).resolve().parents[2]
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
SYNTAX_ENTRY = REPO_ROOT / "assets" / "css" / "syntax.scss"
SYNTAX_PARTIAL = REPO_ROOT / "_sass" / "minima" / "_syntax-highlight.scss"
SKIN = REPO_ROOT / "_sass" / "minima" / "skins" / "auto.scss"
THEME_TOGGLE_PARTIAL = REPO_ROOT / "_sass" / "minima" / "custom" / "_theme-toggle.scss"
PRINT_PARTIAL = REPO_ROOT / "_sass" / "minima" / "custom" / "_print.scss"

MAIN_PATH = "/assets/css/style.css"
SYNTAX_PATH = "/assets/css/syntax.css"

#: The Rouge wrapper every fenced/`highlight`-tag block renders: the gate
#: marker. Inline code (`` `code` ``) renders `highlighter-rouge` on the
#: `<code>` itself with no such wrapper, and needs no token rules.
MARKER = 'class="highlight'

#: At least this much smaller the code-free main stylesheet must be than
#: the old single file (the issue target: 49.9KB -> ~37KB, i.e. >= 20%).
MIN_SAVINGS_RATIO = 0.20


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _syntax_link(html):
    """The conditional syntax-stylesheet href of a rendered page, if any."""
    match = re.search(
        r'<link[^>]*\bid="syntax-stylesheet"[^>]*\bhref="([^"]+)"[^>]*>',
        html,
    )
    return match.group(1) if match else None


def _syntax_version(url):
    """The cache-busting token of a syntax-stylesheet URL, or None."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.path != SYNTAX_PATH:
        return None
    if not parsed.query.startswith("v=") or len(parsed.query) < 3:
        return None
    return parsed.query[2:]


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_head_gates_the_syntax_stylesheet_on_rouge_output():
    """The second sheet loads only where Rouge output exists (#275)."""
    html = _read(HEAD_INCLUDE)
    gate = re.search(
        r"\{%-?\s*if content contains 'class=\"highlight'\s*-?%\}", html
    )
    assert gate, (
        "head.html must gate the syntax stylesheet on "
        "`{% if content contains 'class=\"highlight' %}`: the Rouge "
        "wrapper only fenced code blocks render (#275)"
    )
    endif = html.find("endif", gate.end())
    assert endif != -1, "the Rouge-output conditional must be closed"
    gated = html[gate.end():endif]
    assert "/assets/css/syntax.css" in gated and "?v=" in gated, (
        "the syntax stylesheet tag must live inside the Rouge-output "
        "conditional (#275)"
    )
    assert 'id="syntax-stylesheet"' in gated, (
        "the syntax link needs its own id (the cache-version guard "
        "addresses the main sheet by `id=\"main-stylesheet\"`)"
    )


@pytest.mark.static
def test_the_syntax_sheet_uses_the_same_build_token_after_the_main_sheet():
    """Cache versioning and order survive the split (#275, #61)."""
    html = _read(HEAD_INCLUDE)
    token = re.search(
        r'<link(?=[^>]*\bid="main-stylesheet")[^>]*\?v=\{\{ ([^}]+) \}\}',
        html,
    )
    assert token, "the main stylesheet link lost its build token"
    token_var = token.group(1).strip()
    assert re.search(r"\bsite\.time\b", html), (
        "the version token must still be derived from the build"
    )
    syntax = re.search(
        r'<link(?=[^>]*\bid="syntax-stylesheet")[^>]*\bhref="([^"]+)"',
        html,
    )
    assert syntax, "the syntax stylesheet link is missing from head.html"
    assert syntax.group(1).endswith(f"?v={{{{ {token_var} }}}}"), (
        "the syntax sheet must carry the same build token as the main "
        f"sheet, got {syntax.group(1)!r} (#61)"
    )
    assert html.index('id="main-stylesheet"') < html.index(
        'id="syntax-stylesheet"'
    ), "the token layers must load after the main stylesheet (#275)"


@pytest.mark.static
def test_token_emission_lives_only_in_the_syntax_entry():
    """The split moved the token rules, not just copied them (#275)."""
    for path, name in (
        (SKIN, "the auto skin"),
        (THEME_TOGGLE_PARTIAL, "the theme-toggle partial"),
    ):
        text = _read(path)
        assert "@include lm-highlight" not in text, (
            f"{name} still emits light token rules into the main "
            "stylesheet (#275)"
        )
        assert "@include dm-highlight" not in text, (
            f"{name} still emits dark token rules into the main "
            "stylesheet (#275)"
        )
    partial = _read(SYNTAX_PARTIAL)
    assert "@mixin lm-highlight" in partial and "@mixin dm-highlight" in partial, (
        "the token mixins must live in the shared partial "
        f"({SYNTAX_PARTIAL.relative_to(REPO_ROOT)}) (#275)"
    )
    entry = _read(SYNTAX_ENTRY)
    assert '"minima/syntax-highlight"' in entry, (
        "the syntax entry must import the token-mixin partial (#275)"
    )
    # The old single-file cascade order, pinned: light, no-JS OS dark,
    # explicit data-theme dark, its no-JS fallback, explicit light.
    order = [
        entry.index("@include lm-highlight;"),
        entry.index("@media (prefers-color-scheme: dark)"),
        entry.index('html[data-theme="dark"]'),
        entry.index('html:not([data-theme="light"])'),
        entry.index('html[data-theme="light"]'),
    ]
    assert order == sorted(order), (
        "the syntax entry must emit the token layers in the old cascade "
        "order (light, OS dark, data-theme dark, its fallback, light) (#275)"
    )
    assert entry.count("@include lm-highlight;") == 2, (
        "the syntax entry must emit the light set twice (base + stored "
        "light choice, mirroring the old file) (#275)"
    )
    assert entry.count("@include dm-highlight;") == 3, (
        "the syntax entry must emit the dark set three times (OS media + "
        "stored dark choice + its no-JS fallback, mirroring the old file) "
        "(#275)"
    )


@pytest.mark.static
def test_print_repins_stay_out_of_the_syntax_split():
    """The print-only repins are untouched by the screen split (#275)."""
    assert ".highlight" in _read(PRINT_PARTIAL), (
        "the print repins must stay in the main stylesheet (#275)"
    )
    for path in (SYNTAX_ENTRY, SYNTAX_PARTIAL):
        code = "\n".join(
            line
            for line in _read(path).splitlines()
            if line.strip() and not line.strip().startswith("//")
        )
        assert "@media print" not in code, (
            f"{path} must not take over print rules: the print partial "
            "stays the single `@media print` block, imported last (#225)"
        )


# --- built guards (need Ruby; no browser) ----------------------------------


def _representative_pages(built_site):
    """One built page per kind, both languages where shipped."""
    pages = [
        "index.html",
        "page2/index.html",
        "tags/index.html",
        "about/index.html",
        "portfolio/index.html",
        "search/index.html",
        "vi/index.html",
        "vi/tags/index.html",
        "vi/tim-kiem/index.html",
    ]
    tag_pages = sorted(built_site.glob("tags/*/index.html"))
    assert tag_pages, "no tag pages in the build"
    pages.append(tag_pages[0].relative_to(built_site).as_posix())
    vi_tag_pages = sorted(built_site.glob("vi/tags/*/index.html"))
    assert vi_tag_pages, "no Vietnamese tag pages in the build"
    pages.append(vi_tag_pages[0].relative_to(built_site).as_posix())
    home = _read(built_site / "index.html")
    for match in re.finditer(r'class="post-link" href="([^"]+)"', home):
        pages.append(match.group(1).lstrip("/"))
    vi_home = _read(built_site / "vi" / "index.html")
    for match in re.finditer(r'class="post-link" href="([^"]+)"', vi_home):
        pages.append(match.group(1).lstrip("/"))
    for page in pages:
        assert (built_site / page).is_file(), f"{page} is missing"
    return pages


def test_marker_and_syntax_link_agree_on_every_built_page(built_site):
    """A page links the syntax sheet iff it renders Rouge output (#275).

    The gate is content-based, not layout-based, so the invariant holds for
    every page kind — including future code-bearing posts and list pages
    whose excerpts embed a code block.
    """
    checked = 0
    for path in sorted(built_site.rglob("*.html")):
        html = _read(path)
        has_marker = MARKER in html
        has_link = _syntax_link(html) is not None
        assert has_marker == has_link, (
            f"{path.relative_to(built_site)} renders Rouge output but "
            f"{'skips' if has_marker else 'links'} the syntax stylesheet "
            "(#275)"
        )
        checked += 1
    assert checked > 20, "the crawl found suspiciously few pages"


def test_code_free_pages_skip_the_second_stylesheet(built_site):
    """Home, tag, about, portfolio, search, prose posts: one sheet (#275)."""
    for page in _representative_pages(built_site):
        html = _read(built_site / page)
        assert _syntax_link(html) is None, (
            f"{page} renders no Rouge output but still links the syntax "
            "stylesheet (#275)"
        )


def test_main_stylesheet_carries_no_token_rules(built_site):
    """The code-free sheet keeps structure, drops token colours (#275)."""
    css = _read(built_site / "assets" / "css" / "style.css")
    screen, _, _ = css.partition("@media print")
    # The one structural exception: the line-number alignment nested in
    # the `div.highlight`/`figure.highlight` container rule in
    # `_sass/minima/_base.scss` (`text-align`, not token colours).
    structural = (
        "div.highlight .lineno, div.highlight .gl, "
        "figure.highlight .lineno, figure.highlight .gl"
    )
    assert structural in screen, (
        "the code-block container lost its line-number alignment (#275)"
    )
    assert ".highlight ." not in screen.replace(structural, ""), (
        "the main stylesheet still ships Rouge token-descendant rules "
        "outside the print block (#275)"
    )
    assert "code.highlighter-rouge" in screen, (
        "inline-code structure must stay in the main stylesheet (#275)"
    )
    assert "div.highlight" in screen, (
        "the code-block container structure must stay in the main "
        "stylesheet (#275)"
    )


def test_built_syntax_stylesheet_carries_the_token_layers(built_site):
    """The companion sheet really is the moved token CSS (#275)."""
    css = _read(built_site / "assets" / "css" / "syntax.css")
    assert len(css.encode("utf-8")) > 12_000, (
        f"the syntax stylesheet is only {len(css)} chars: the token "
        "layers look gutted (#275)"
    )
    for selector in (".highlight .k", ".highlight .c", ".highlight .err"):
        assert selector in css, (
            f"the syntax stylesheet never defines {selector} (#275)"
        )
    assert "@media (prefers-color-scheme: dark)" in css, (
        "the syntax stylesheet lost the no-JS OS-preference dark layer"
    )
    # (Sass compiles the quoted attribute selectors unquoted.)
    assert "html[data-theme=dark]" in css, (
        "the syntax stylesheet lost the stored-dark-choice layer (#220)"
    )
    assert "html[data-theme=light]" in css, (
        "the syntax stylesheet lost the stored-light-choice layer (#220)"
    )
    assert "@media print" not in css, (
        "print rules must stay in the main stylesheet (#225)"
    )


def test_main_stylesheet_hits_the_savings_target(built_site):
    """Code-free pages download >= 20% less render-blocking CSS (#275)."""
    main = (built_site / "assets" / "css" / "style.css").stat().st_size
    syntax = (built_site / "assets" / "css" / "syntax.css").stat().st_size
    old_single = main + syntax
    assert main <= (1 - MIN_SAVINGS_RATIO) * old_single, (
        f"the code-free stylesheet is {main} bytes of a former "
        f"{old_single}-byte single file: savings below the 20% target "
        "(#275)"
    )


def _build_with_fixture_post(tmp_path):
    """Rebuild a copy of the repo plus one real fenced-code post (#275).

    No published post ships highlighted code today, so the real build
    cannot exercise the gate: the copy proves a code-bearing page links
    both sheets with one token while its code-free home still skips the
    second sheet.
    """
    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip("`bundle` not found: this guard rebuilds the site")
    lockfile = REPO_ROOT / "Gemfile.lock"
    if not lockfile.is_file():
        pytest.skip("no Gemfile.lock for the copied build (`bundle install`)")

    source = tmp_path / "syntax-fixture-src"
    shutil.copytree(
        REPO_ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", "_site", ".jekyll-cache", ".sass-cache", ".bundle",
            "vendor", "tests", ".ao", ".opencode", "__pycache__",
            ".pytest_cache",
        ),
        symlinks=False,
    )
    shutil.copy2(lockfile, source / "Gemfile.lock")
    (source / "_posts" / "2026-01-02-syntax-fixture-275.md").write_text(
        "---\n"
        "layout: post\n"
        "title: \"Syntax fixture 275\"\n"
        "tags: [backend-production]\n"
        "description: \"Temporary fixture proving the syntax.css gate.\"\n"
        "---\n"
        "\n"
        "A fenced block:\n"
        "\n"
        "```ruby\n"
        "def hello\n"
        '  puts "world"\n'
        "end\n"
        "```\n",
        encoding="utf-8",
    )
    destination = tmp_path / "syntax-fixture-site"
    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(source),
        env=test_stylesheet_cache_version._bundler_env(source),
        capture_output=True,
        text=True,
        timeout=conftest.BUILD_TIMEOUT_S,
    )
    assert result.returncode == 0, (
        f"fixture build failed ({result.returncode})\n"
        f"{result.stdout}\n{result.stderr}"
    )
    return destination


def test_code_page_loads_both_sheets_with_one_token(built_site, tmp_path):
    """A code-bearing post links both sheets with the same token (#275)."""
    del built_site  # the fixture rebuild is self-contained (see below).
    destination = _build_with_fixture_post(tmp_path)
    code_rel = Path("2026/01/02/syntax-fixture-275.html")
    assert (destination / code_rel).is_file(), "the fixture post did not build"
    html = _read(destination / code_rel)
    assert MARKER in html, "the fixture post renders no Rouge output"
    main = re.search(
        r'<link(?=[^>]*\bid="main-stylesheet")[^>]*\bhref="([^"]+)"',
        html,
    )
    syntax_href = _syntax_link(html)
    assert main and syntax_href, (
        "a code-bearing post must link both stylesheets (#275)"
    )
    main_token = test_stylesheet_cache_version._version(main.group(1))
    syntax_token = _syntax_version(syntax_href)
    assert main_token and main_token == syntax_token, (
        "both sheets must share one build token, got "
        f"{main.group(1)!r} vs {syntax_href!r} (#61)"
    )
    home = _read(destination / "index.html")
    assert _syntax_link(home) is None, (
        "the fixture build's code-free home must still skip the syntax "
        "stylesheet (#275)"
    )
