"""Guard for #61: the deployed stylesheet URL must be cache-versioned.

Why this guard exists — the honest answer to "the tests were wrong":

Every other guard in this suite (#47 chips, #50 overflow, #58 sidebar) loads ONE
build's own HTML + CSS pair from the same freshly served directory, so HTML and
CSS always come from the same revision. That is exactly the failure a
*single-build* test cannot see: the deployed stylesheet kept the fixed URL
`/assets/css/style.css` while GitHub Pages serves it with
`cache-control: max-age=14400`, so a returning visitor rendered the post-#58 HTML
with the pre-#58 stylesheet — which defines no `.site-layout` grid — and the
sidebar painted as a full-width block below the whole post list. The old guards
were not wrong about the layout; nothing asserted that the *asset URL* is
cache-safe.

Guarded here:

- `_includes/head.html` links the stylesheet through a Liquid build token
  (`?v=...`), and every fixed-URL asset link in the head carries it too (the
  favicon is served with the same 4-hour `max-age`) — static, no Ruby;
- no template is left with an *unversioned* `/assets/` link, and the matcher
  below rejects the old unversioned markup, so these assertions really are
  sensitive to the regression they guard (static);
- every page of one build carries one and the same versioned URL, that URL
  resolves over HTTP, and the stylesheet it serves defines the #58 grid;
- a client that still holds the OLD stylesheet under the unversioned URL (the
  reported bug, modelled as a browser cache keyed by URL) still gets the
  sidebar, because the HTML now asks for a different URL; the same harness
  provably sees the sidebar disappear when the stale stylesheet *is* served;
- a rebuild with a different build identity (`time:` in the config) publishes a
  different stylesheet URL, so a cached copy cannot pair with newer HTML;
- the owner's proof: change ONE CSS declaration in a copy of the site, rebuild
  it, and the emitted stylesheet URL differs — the token tracks the CSS content.

Trade-off this guard pins down: the token follows the *build*, not the CSS
bytes, so a deploy that does not touch the stylesheet re-fetches it once
(~18KB). A real content hash of the compiled CSS is not reachable here: it needs
a Jekyll plugin, and GitHub Pages runs its `--safe` build with no custom
plugins. A per-build token changes on a strict superset of the cases where the
CSS changes (a CSS change always means a new build), which is why it can never
pair stale CSS with fresh HTML.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import conftest
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HEAD_INCLUDE = REPO_ROOT / "_includes" / "head.html"
SUB_FOOTER_INCLUDE = REPO_ROOT / "_includes" / "sub-footer.html"
ASSET_VERSION_INCLUDE = REPO_ROOT / "_includes" / "asset-version.html"
TEMPLATE_DIRS = ("_includes", "_layouts")

STYLESHEET_PATH = "/assets/css/style.css"
FAVICON_PATH = "/assets/img/favicon.ico"
DESKTOP_WIDTH = 1280

# The two fixed-URL assets the head links; both are served with max-age=14400.
HEAD_ASSETS = (STYLESHEET_PATH, FAVICON_PATH)

# A `--safe` build compiles the site again from this copy; the CSS change has to
# land in the compiled stylesheet, so patch a value the Sass pipeline uses.
CSS_DECLARATION = "gap: $spacing-unit;"
PATCHED_DECLARATION = "gap: $spacing-unit + 7px;"
# One whole second between two builds, so their `site.time` token differs.
BUILD_IDENTITY_INTERVAL_S = 1.1

# The layout rule the #58 sidebar depends on: without it the aside is not a grid
# item and paints below the whole list.
GRID_RULE = "grid-template-columns: minmax(0, 1fr) 300px"
SITE_LAYOUT_RULE = re.compile(r"\.site-layout[^{]*\{[^}]*\}")

# `<link id="main-stylesheet" ... href="/assets/css/style.css?v=<token>">` in the
# rendered head, and the matching Liquid in the include.
_RENDERED_LINK = re.compile(
    r'<link(?=[^>]*\bid="main-stylesheet")[^>]*\bhref="([^"]+)"[^>]*>'
)
_INCLUDE_LINK = re.compile(
    r'<link(?=[^>]*\bid="main-stylesheet")[^>]*\bhref="\{\{ '
    r"'/assets/css/style\.css' \| relative_url \}\}\?v=\{\{ (?P<token>[^}]+) \}\}\"[^>]*>"
)

_MEASURE_JS = """
() => {
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            width: r.width, height: r.height};
  };
  const aside = document.querySelector('aside.site-sidebar');
  const main = document.querySelector('.site-main');
  return {
    main: box(main),
    aside: box(aside),
    asidePosition: aside ? getComputedStyle(aside).position : null,
    stylesheets: Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
      .map((l) => l.href),
  };
}
"""


def _read(path):
    return path.read_text(encoding="utf-8")


def _stylesheet_url(html):
    """Return the stylesheet href of a rendered page, or None when absent."""
    match = _RENDERED_LINK.search(html)
    return match.group(1) if match else None


def _version(url):
    """Return the cache-busting token of a stylesheet URL, or None."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.path != STYLESHEET_PATH:
        return None
    if not parsed.query.startswith("v=") or len(parsed.query) < 3:
        return None
    return parsed.query[2:]


def _stale_css(css):
    """The served CSS with every `.site-layout` rule removed.

    A stand-in for any pre-#58 stylesheet: same file, no sidebar grid.
    """
    stripped = SITE_LAYOUT_RULE.sub("", css)
    assert ".site-layout" not in stripped
    assert GRID_RULE not in stripped
    return stripped


def _token_expression(html):
    """The build expression the stylesheet link's token comes from."""
    match = _INCLUDE_LINK.search(html)
    assert match, (
        "the head must link the stylesheet through a build token, e.g. "
        'href="{{ \'/assets/css/style.css\' | relative_url }}?v={{ ... }}"; a fixed '
        "URL lets a browser pair it with newer HTML (#61)"
    )
    token = match.group("token").strip()
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
        # `{%- assign <token> = <build expression> -%}` in the head
        # itself or in a shared include it pulls in (#295 hoisted the
        # assignment into `_includes/asset-version.html`).
        assign = re.search(
            rf"assign\s+{re.escape(token)}\s*=\s*(.+?)\s*-?%\}}",
            conftest.template_with_includes(HEAD_INCLUDE),
        )
        assert assign, (
            f"the stylesheet version {token!r} is never assigned in "
            f"{HEAD_INCLUDE.relative_to(REPO_ROOT)} or an include it pulls in"
        )
        return assign.group(1).strip()
    return token


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_head_links_the_stylesheet_with_a_build_token():
    html = _read(HEAD_INCLUDE)
    expression = _token_expression(html)
    # The token must come from the build, not from a literal: a hardcoded value
    # would never change on deploy.
    assert re.search(r"\bsite\.time\b|\bsite\.github\.build_revision\b", expression), (
        "the version token must be derived from the build, "
        f"got {{{{{expression}}}}}"
    )
    token_variable = _INCLUDE_LINK.search(html).group("token")
    assert _version(f"{STYLESHEET_PATH}?v={{{{{token_variable}}}}}"), (
        "the token expression must sit in the `v=` query parameter"
    )


@pytest.mark.static
def test_no_unversioned_asset_link_is_left_in_the_templates():
    """Every fixed-URL `/assets/` link must carry the version token (#61).

    The stylesheet was today's symptom; the head's favicon is served from the
    same `max-age=14400` regime, and so is a future asset. Guarding the class is
    cheaper than re-learning this incident.
    """
    offenders = []
    for directory in TEMPLATE_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if not path.is_file():
                continue
            text = _read(path)
            for match in re.finditer(r"(?:href|src)=\"(/assets/[^\"]*)\"", text):
                href = match.group(1)
                if "?v=" not in href:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {href}")
    assert not offenders, (
        "every /assets/ link in the templates must carry the version token, "
        "otherwise a browser can serve the cached copy against new HTML (#61): "
        + "; ".join(offenders)
    )


@pytest.mark.static
def test_head_links_the_uncached_assets_with_the_same_token():
    html = _read(HEAD_INCLUDE)
    token_variable = _INCLUDE_LINK.search(html).group("token")
    for asset in HEAD_ASSETS:
        # Either `{{ '<path>' | relative_url }}?v={{ token }}` or
        # `"<path>?v={{ token }}"`.
        versioned = "?v={{ " + token_variable + " }}"
        forms = (asset + "' | relative_url }}" + versioned, asset + versioned)
        assert any(form in html for form in forms), (
            f"{asset} is served from a fixed URL with a 4-hour max-age and must "
            f"use the same version token as the stylesheet (#61), got no "
            f"`{versioned}` on it"
        )


@pytest.mark.static
def test_asset_version_assignment_has_a_single_source():
    """The `?v=` build token is assigned once and shared (#295).

    The `asset_version = site.time | date: '%s'` assignment used to be
    copy-pasted into the head and the sub-footer, so a
    change to the versioning scheme needed matching edits. It now
    lives in exactly one include; every call site pulls it in instead of
    assigning it, so the head and the deferred scripts
    can never drift to different tokens.
    """
    literal = re.compile(r"assign\s+asset_version\s*=\s*site\.time\s*\|\s*date:")
    owners = []
    for directory in TEMPLATE_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if path.is_file() and literal.search(_read(path)):
                owners.append(path.relative_to(REPO_ROOT).as_posix())
    assert owners == [ASSET_VERSION_INCLUDE.relative_to(REPO_ROOT).as_posix()], (
        "the asset_version assignment must live in exactly one file "
        f"({ASSET_VERSION_INCLUDE.relative_to(REPO_ROOT)}), found in: "
        f"{owners} (#295)"
    )
    for site in (HEAD_INCLUDE, SUB_FOOTER_INCLUDE):
        text = _read(site)
        assert re.search(r"\{%-?\s*include\s+asset-version\.html\s*-?%\}", text), (
            f"{site.relative_to(REPO_ROOT)} must include asset-version.html "
            "instead of assigning asset_version itself (#295)"
        )


@pytest.mark.static
def test_the_matcher_rejects_an_unversioned_stylesheet_url():
    """Guard sensitivity: the assertions above must fail on the old markup."""
    old = '<link id="main-stylesheet" rel="stylesheet" href="/assets/css/style.css">'
    assert _stylesheet_url(old) == STYLESHEET_PATH
    assert _version(_stylesheet_url(old)) is None, (
        "an unversioned stylesheet URL must be reported as not cache-versioned"
    )

    new = (
        '<link id="main-stylesheet" rel="stylesheet" '
        'href="/assets/css/style.css?v=1792254035">'
    )
    assert _version(_stylesheet_url(new)) == "1792254035"
    assert _version(f"{STYLESHEET_PATH}?v=") is None, "an empty token is not a version"


# --- build guards (need Ruby; no browser) ----------------------------------


def _page_urls(built_site):
    """A representative page per template: home, page 2, tag index, tag, post —
    in both languages (#93)."""
    pages = ["index.html", "page2/index.html", "tags/index.html"]
    tag_pages = sorted(built_site.glob("tags/*/index.html"))
    assert tag_pages, "no tag pages in the build"
    pages.append(tag_pages[0].relative_to(built_site).as_posix())
    home = _read(built_site / "index.html")
    post = re.search(r'class="post-link" href="([^"]+)"', home)
    assert post, "the home list links no post"
    pages.append(post.group(1).lstrip("/"))
    # Vietnamese representatives: the `/vi/` home, its tag index, its first
    # tag page and the first post it lists.
    pages.append("vi/index.html")
    pages.append("vi/tags/index.html")
    vi_tag_pages = sorted(built_site.glob("vi/tags/*/index.html"))
    assert vi_tag_pages, "no Vietnamese tag pages in the build"
    pages.append(vi_tag_pages[0].relative_to(built_site).as_posix())
    vi_home = _read(built_site / "vi" / "index.html")
    vi_post = re.search(r'class="post-link" href="([^"]+)"', vi_home)
    assert vi_post, "the Vietnamese home list links no post"
    pages.append(vi_post.group(1).lstrip("/"))
    for page in pages:
        assert (built_site / page).is_file(), f"{page} is missing from the build"
    return pages


def test_every_page_of_one_build_shares_one_versioned_stylesheet_url(built_site, built_site_url):
    pages = _page_urls(built_site)
    tokens = {}
    for page in pages:
        url = _stylesheet_url(_read(built_site / page))
        assert url, f"{page} has no stylesheet link"
        token = _version(url)
        assert token, (
            f"{page} links {url!r}, which is not cache-versioned: a browser may "
            "keep the stylesheet it already has (#61)"
        )
        tokens[page] = token

    assert len(set(tokens.values())) == 1, (
        "one build must serve one stylesheet URL on every page, got "
        f"{json.dumps(tokens, indent=2)}"
    )

    # The versioned URL really resolves and really carries the #58 grid.
    versioned = f"{STYLESHEET_PATH}?v={tokens[pages[0]]}"
    with urllib.request.urlopen(f"{built_site_url}{versioned}") as response:
        assert response.status == 200, f"{versioned} returned {response.status}"
        body = response.read().decode("utf-8")
    assert GRID_RULE in body, (
        f"the stylesheet served at {versioned} does not define the #58 sidebar grid"
    )


def test_a_rebuild_with_another_build_identity_publishes_another_url(built_site, tmp_path):
    """The token tracks the build, so a deploy cannot reuse a cached URL."""
    shipped = _version(_stylesheet_url(_read(built_site / "index.html")))
    assert shipped

    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip("`bundle` not found: this guard rebuilds the site with Ruby")

    # Far in the future so no post counts as unpublished (`future: false` would
    # drop posts dated after `time` and the tag layout needs them).
    extra = tmp_path / "build-identity.yml"
    extra.write_text("time: 2099-01-01T00:00:00Z\n", encoding="utf-8")
    destination = tmp_path / "rebuild"

    result = subprocess.run(
        [
            bundle,
            "exec",
            "jekyll",
            "build",
            "--config",
            f"{REPO_ROOT / '_config.yml'},{extra}",
            "--destination",
            str(destination),
        ],
        cwd=str(REPO_ROOT),
        env=_bundler_env(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=conftest.BUILD_TIMEOUT_S,
    )
    assert result.returncode == 0, (
        f"rebuild failed ({result.returncode})\n{result.stdout}\n{result.stderr}"
    )

    rebuilt = _version(_stylesheet_url(_read(destination / "index.html")))
    assert rebuilt, "the rebuild published an unversioned stylesheet"

    # Honest trade-off: same CSS bytes, different token - the URL follows the
    # build, which is a superset of "the CSS changed", so it can never be stale.
    original_css = (built_site / "assets/css/style.css").read_bytes()
    rebuilt_css = (destination / "assets/css/style.css").read_bytes()
    assert hashlib.sha256(original_css).hexdigest() == hashlib.sha256(rebuilt_css).hexdigest()

    assert rebuilt != shipped, (
        "a new build must publish a new stylesheet URL, otherwise a browser may "
        f"serve the stylesheet it cached at {STYLESHEET_PATH} (#61)"
    )


def _installed_gem_path():
    """Absolute gem path the session's bundler installs into, or None.

    CI (`ruby/setup-ruby` with `bundler-cache`) vendors the gems into
    `<repo>/vendor/bundle` and points bundler at the *relative* path
    `vendor/bundle`, which a copied tree does not contain. Resolving it against
    the real repository keeps the copied build able to find `jekyll`.
    """
    candidates = []
    env_path = os.environ.get("BUNDLE_PATH")
    if env_path:
        candidates.append(env_path)
    config = REPO_ROOT / ".bundle" / "config"
    if config.is_file():
        match = re.search(r"^BUNDLE_PATH:\s*\"?([^\"\n]+?)\"?\s*$", _read(config), re.M)
        if match:
            candidates.append(match.group(1))
    candidates.append("vendor/bundle")
    for candidate in candidates:
        resolved = Path(candidate)
        if not resolved.is_absolute():
            resolved = REPO_ROOT / resolved
        if resolved.is_dir():
            return str(resolved.resolve())
    return None


def _bundler_env(source):
    """Environment for a `bundle exec` in ``source`` (a copy of the repo).

    ``BUNDLE_GEMFILE`` is pinned so a CI-exported value pointing at the original
    repository cannot make the *theme* (and therefore the Sass) come from there
    instead of the copy, and the vendored gem path is made absolute.
    """
    env = dict(os.environ)
    bundle = conftest._bundle()
    if bundle:
        # `bundle` can live in a user gem dir that is not on PATH (#56).
        env["PATH"] = os.pathsep.join(
            [str(Path(bundle).parent), env.get("PATH", "")]
        ).rstrip(os.pathsep)
    env["BUNDLE_GEMFILE"] = str(source / "Gemfile")
    gem_path = _installed_gem_path()
    if gem_path:
        env["BUNDLE_PATH"] = gem_path
    return env


def _build_repo_copy(tmp_path, patch_css_declaration=False):
    """Build a copy of the repository; optionally change one CSS declaration.

    The copy is self-contained (its own `Gemfile`/`minima.gemspec`, so the theme
    `_sass` it compiles is the patched one) and reuses the workspace's
    `Gemfile.lock`, so bundler resolves offline. Returns the build directory.
    """
    bundle = conftest._bundle()
    if bundle is None:
        pytest.skip("`bundle` not found: this guard rebuilds the site with Ruby")
    lockfile = REPO_ROOT / "Gemfile.lock"
    if not lockfile.is_file():
        pytest.skip("no Gemfile.lock to reuse for the copied build (`bundle install`)")

    name = "patched" if patch_css_declaration else "baseline"
    source = tmp_path / f"{name}-src"
    shutil.copytree(
        REPO_ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git", "_site", ".jekyll-cache", ".sass-cache", ".bundle", "vendor",
            "tests", ".ao", ".opencode", "__pycache__", ".pytest_cache",
        ),
        symlinks=False,
    )
    shutil.copy2(lockfile, source / "Gemfile.lock")

    if patch_css_declaration:
        # The declaration lives in the layout partial since #174 split
        # `custom-styles.scss` into an index over `minima/custom/`.
        scss = source / "_sass" / "minima" / "custom" / "_layout.scss"
        text = _read(scss)
        assert CSS_DECLARATION in text, f"{CSS_DECLARATION!r} not found in the Sass"
        scss.write_text(text.replace(CSS_DECLARATION, PATCHED_DECLARATION, 1), encoding="utf-8")

    destination = tmp_path / f"{name}-site"
    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(source),
        env=_bundler_env(source),
        capture_output=True,
        text=True,
        timeout=conftest.BUILD_TIMEOUT_S,
    )
    assert result.returncode == 0, (
        f"{name} build failed ({result.returncode})\n{result.stdout}\n{result.stderr}"
    )
    return source, destination


def test_one_changed_css_declaration_publishes_a_new_stylesheet_url(built_site, tmp_path):
    """The owner's proof for #61: a CSS change moves the emitted asset URL.

    The token follows the build and the build compiles this CSS, so changing one
    declaration necessarily emits a different URL. `site.time` has one-second
    resolution, so the two builds are separated by a whole second to make the
    assertion deterministic instead of lucky.
    """
    shipped_css = (built_site / "assets/css/style.css").read_bytes()
    shipped_token = _version(_stylesheet_url(_read(built_site / "index.html")))
    assert shipped_token

    # A copy of the same sources, without the CSS change: the baseline must be
    # byte-identical to the shipped build, otherwise the comparison below would
    # prove nothing about the CSS.
    _, baseline = _build_repo_copy(tmp_path, patch_css_declaration=False)
    assert (baseline / "assets/css/style.css").read_bytes() == shipped_css, (
        "the copied build differs from the shipped build, so the CSS change is "
        "not the only difference between the two builds"
    )
    baseline_token = _version(_stylesheet_url(_read(baseline / "index.html")))
    assert baseline_token

    time.sleep(BUILD_IDENTITY_INTERVAL_S)
    _, patched = _build_repo_copy(tmp_path, patch_css_declaration=True)

    patched_css = (patched / "assets/css/style.css").read_bytes()
    assert hashlib.sha256(patched_css).hexdigest() != hashlib.sha256(shipped_css).hexdigest(), (
        "the patched Sass did not change the compiled stylesheet"
    )

    patched_token = _version(_stylesheet_url(_read(patched / "index.html")))
    assert patched_token, "the patched build published an unversioned stylesheet"
    assert patched_token != shipped_token, (
        "the stylesheet content changed but the emitted URL did not "
        f"({STYLESHEET_PATH}?v={patched_token}); a warm cache would keep serving "
        "the old layout (#61)"
    )


# --- browser guard: the reporter's client ----------------------------------


def test_a_client_holding_the_old_stylesheet_still_gets_the_sidebar(
    built_site, built_site_url, browser
):
    """The reported bug, modelled as a browser cache keyed by URL.

    The interceptor keeps the old stylesheet under the *unversioned* URL, which
    is what a visitor who loaded the site before #58 still has (four hours of
    `max-age=14400`). The fixed HTML asks for a different URL, so the stale copy
    is bypassed and the sidebar is there.
    """
    served_css = (built_site / "assets/css/style.css").read_text(encoding="utf-8")
    stale_css = _stale_css(served_css)
    origin = urlparse(built_site_url).netloc

    def open_home(serve_stale_for_every_url):
        context = browser.new_context(viewport={"width": DESKTOP_WIDTH, "height": 900})
        try:
            page = context.new_page()
            requested = []
            css_requests = []

            def handler(route):
                url = route.request.url
                if urlparse(url).netloc != origin:
                    route.abort()
                    return
                requested.append(url)
                if urlparse(url).path.endswith(STYLESHEET_PATH):
                    css_requests.append(url)
                    # A cache hit only for the URL the old markup used.
                    if serve_stale_for_every_url or not urlparse(url).query:
                        route.fulfill(
                            status=200,
                            content_type="text/css",
                            headers={"cache-control": "max-age=14400"},
                            body=stale_css,
                        )
                        return
                route.continue_()

            page.route("**/*", handler)
            response = page.goto(f"{built_site_url}/", wait_until="load")
            assert response is not None and response.status == 200
            page.wait_for_selector("aside.site-sidebar", state="attached", timeout=10_000)
            page.wait_for_timeout(200)
            return page.evaluate(_MEASURE_JS), css_requests
        finally:
            context.close()

    # With the fix: the page must not ask for the stale URL at all.
    metrics, css_requests = open_home(serve_stale_for_every_url=False)
    assertive = [url for url in css_requests if _version(url)]
    assert assertive, (
        "the page requested no cache-versioned stylesheet, so a browser holding "
        f"{STYLESHEET_PATH} would keep rendering the old layout (#61): {css_requests}"
    )
    assert metrics["main"] and metrics["aside"], "the sidebar shell is missing"
    assert metrics["main"]["right"] <= metrics["aside"]["left"] + 0.5, (
        "despite the stale stylesheet sitting at the unversioned URL, the sidebar "
        f"must be beside the list at {DESKTOP_WIDTH}px "
        f"(main right {metrics['main']['right']} > aside left {metrics['aside']['left']})"
    )
    assert abs(metrics["aside"]["width"] - 300) <= 10, (
        f"the sidebar should be 300px wide, got {metrics['aside']['width']}"
    )
    assert metrics["asidePosition"] == "sticky"

    # Control: the same harness *does* see the sidebar vanish when the stale
    # stylesheet is served for the URL the page asks for - i.e. this test would
    # have failed before the fix. Only the `.site-layout` rules are removed, so
    # the sheet still carries the (harmless) `.site-sidebar { position: sticky }`
    # rule; sticky cannot lift the block back above the list.
    stale_metrics, _ = open_home(serve_stale_for_every_url=True)
    assert stale_metrics["main"] and stale_metrics["aside"]
    assert stale_metrics["aside"]["top"] >= stale_metrics["main"]["bottom"] - 0.5, (
        "the harness cannot see the reported bug: with the pre-#58 stylesheet the "
        "sidebar must paint below the whole list "
        f"(aside top {stale_metrics['aside']['top']} vs main bottom "
        f"{stale_metrics['main']['bottom']})"
    )
    assert stale_metrics["aside"]["left"] <= stale_metrics["main"]["left"] + 0.5, (
        "the sidebar without the grid must be a full-width block, like the report"
    )
