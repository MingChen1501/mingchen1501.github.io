"""Giscus comment embed end-to-end coverage in production builds (#211).

The comments E2E (``test_comments.py``) only stubs Disqus, while Giscus
(``comments.provider: giscus``) ships with no embed coverage. This module
closes that gap. Comments stay gated off in development builds
(``site.comments.dev`` is false), so every test here builds with
``JEKYLL_ENV=production``:

- the comments-enabled post renders the ``section#comments`` container and the
  ``https://giscus.app/client.js`` script with every configured data
  attribute;
- Giscus network traffic is intercepted and aborted, so the suite proves the
  page attempts the load while making zero real requests to ``giscus.app``;
- negative cases: ``comments: false`` renders the disabled message with no
  embed, and a build whose comments provider is off renders no embed at all.

Theme sync (#258) rides on top: ``assets/js/giscus-theme.js`` primes the
embed's ``data-theme`` to the site-mapped Giscus theme before the lazy iframe
boots and re-sends the Giscus ``setConfig`` postMessage on every theme flip
and iframe load, without reloading. The guards below pin the template wiring
(mapping attributes, deferred versioned script tag), the script contract
(postMessage shape/origin, iframe query, silent fallback) and the runtime
behavior with a mocked Giscus client (initial paint + toggle flip in all
four OS x site combos, EN + VI, zero real network, no iframe replacement).

Static guards (no Ruby, no browser) pin the template contract; build guards
(need Ruby, no browser) pin the emitted markup; browser guards drive the
production pages with the Giscus routes aborted.

Note: the ``comments-unavailable`` branch in ``comments.html`` is guarded by
``!= blank``, which never matches a missing or empty value under the pinned
Liquid 4.0.4, so the "no provider configured" build below disables comments
via ``comments.provider: "none"`` instead of blanking Giscus keys (blanking
still emits the script tag). That template quirk is out of scope here and
left untouched.
"""

from __future__ import annotations

import contextlib
import functools
import os
import re
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENTS_INCLUDE = REPO_ROOT / "_includes" / "comments.html"
BASE_CONFIG = REPO_ROOT / "_config.yml"

EN_POST_REL = Path("2022/10/27/brewing-vietnamese-coffee.html")
VI_POST_REL = Path("vi/2022/10/27/cach-pha-ca-phe.html")
EN_POST_SOURCE = "_posts/2022-10-27-brewing-vietnamese-coffee.md"

BUILD_TIMEOUT_S = 300

GISCUS_CLIENT_SRC = "https://giscus.app/client.js"
# Pinned production values from `_config.yml` (`giscus:`): the test must fail
# loudly if the shipped config drifts, so these stay hardcoded instead of
# being read back from the config under test.
EXPECTED_ATTRS = {
    "data-repo": "MingChen1501/mingchen1501.github.io",
    "data-repo-id": "R_kgDOHBJg8A",
    "data-category": "Announcements",
    "data-category-id": "DIC_kwDOHBJg8M4DIbBW",
    "data-mapping": "pathname",
    "data-theme": "preferred_color_scheme",
    # The site-to-Giscus theme map (#258): the page default stays the OS
    # setting, and the sync script swaps it for one of these at runtime.
    "data-light-theme": "light",
    "data-dark-theme": "dark",
}
DISABLED_MESSAGE = "Comments have been disabled for this post."
UNAVAILABLE_MESSAGE = "Comments are temporarily unavailable."

# Extra `--config` overlays for the negative builds (merged over the real
# `_config.yml`; the provider overlay must quote "none" or YAML reads null).
PROVIDER_OFF_OVERLAY = 'comments:\n  provider: "none"\n'
DISABLED_POST_OVERLAY = (
    "defaults:\n"
    "  - scope:\n"
    f"      path: {EN_POST_SOURCE}\n"
    "    values:\n"
    "      comments: false\n"
)


def _read(path):
    return path.read_text(encoding="utf-8")


def _giscus_script_tag(html):
    """Return the Giscus ``<script ...>...</script>`` block, or None."""
    match = re.search(
        r'<script\s+src="https://giscus\.app/client\.js".*?</script>',
        html,
        re.S,
    )
    return match.group(0) if match else None


def _bundle():
    """Return the `bundle` executable, or None when Ruby is unavailable."""
    found = shutil.which("bundle")
    if found:
        return found
    for candidate in sorted(Path.home().glob(".gem/ruby/*/bin/bundle")):
        return str(candidate)
    return None


def _production_env(bundle):
    env = {key: value for key, value in os.environ.items()}
    env["JEKYLL_ENV"] = "production"
    env["PATH"] = os.pathsep.join(
        [str(Path(bundle).parent), env.get("PATH", "")]
    ).rstrip(os.pathsep)
    return env


def _build_production(destination, config_files, label):
    bundle = _bundle()
    if bundle is None:
        pytest.skip(
            "`bundle` not found: the Giscus production guards need Ruby + "
            "`bundle install` (CI installs both in .github/workflows/e2e.yml)"
        )
    result = subprocess.run(
        [
            bundle,
            "exec",
            "jekyll",
            "build",
            "--destination",
            str(destination),
            "--config",
            ",".join(str(path) for path in config_files),
        ],
        cwd=str(REPO_ROOT),
        env=_production_env(bundle),
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_S,
    )
    if result.returncode != 0:
        pytest.fail(
            f"`jekyll build` ({label}) failed with exit code "
            f"{result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    return destination


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def page(browser):
    context = browser.new_context()
    browser_page = context.new_page()
    try:
        yield browser_page
    finally:
        context.close()


def _intercept_giscus(browser_page, requests):
    """Abort every Giscus request: recorded, never touching the network."""

    def handler(route):
        requests.append(route.request.url)
        route.abort()

    browser_page.route("**://giscus.app/**", handler)
    browser_page.route("**://*.giscus.app/**", handler)


def _wait_for_network_quiet(browser_page, timeout=5_000):
    """Bounded settle before asserting that no (further) request arrives.

    A page that must contact *nothing* — or must not retry an aborted load
    — offers no event to wait on, so the old fixed sleeps could only flake
    on slow runners (a stray request can arrive after the sleep) or stall
    fast ones. ``networkidle`` returns as soon as the page is quiet —
    typically after ~500ms of silence — and the short bound keeps a stray
    late request from hanging the suite. A bounded wait is unavoidable for
    a negative network assertion; the recorded route-log assertion that
    follows is what guards the behavior, and this wait only gives a stray
    request its chance to show up first (#276).
    """
    try:
        browser_page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        pass


# --- static guards (no Ruby, no browser) -----------------------------------


@pytest.mark.static
def test_comments_include_renders_giscus_client_script():
    html = _read(COMMENTS_INCLUDE)
    assert GISCUS_CLIENT_SRC in html, (
        "comments.html must load the Giscus client from giscus.app"
    )


@pytest.mark.static
def test_comments_include_wires_giscus_config_attributes():
    html = _read(COMMENTS_INCLUDE)
    for attribute, liquid in (
        ("data-repo", "site.giscus.repo"),
        ("data-repo-id", "site.giscus.repo_id"),
        ("data-category", "site.giscus.category"),
        ("data-category-id", "site.giscus.category_id"),
        ("data-mapping", "site.giscus.mapping"),
        ("data-theme", "site.giscus.theme"),
        ("data-lang", "page.lang"),
    ):
        assert f'{attribute}="{{{{ {liquid}' in html, (
            f"the Giscus script tag must wire {attribute} from `{liquid}`"
        )


@pytest.mark.static
def test_comments_include_renders_giscus_section_container():
    html = _read(COMMENTS_INCLUDE)
    assert 'class="comments" id="comments"' in html
    assert 'class="comments__title"' in html


@pytest.mark.static
def test_comments_include_has_unconfigured_branch_without_script():
    html = _read(COMMENTS_INCLUDE)
    assert "comments-unavailable" in html
    assert UNAVAILABLE_MESSAGE in html
    fallback = html.split("comments-unavailable")[1].split("{%- endif -%}")[0]
    assert "<script" not in fallback, (
        "the unconfigured Giscus branch must render no script tag"
    )


@pytest.mark.static
def test_comments_include_wires_the_giscus_theme_mapping():
    """The site-to-Giscus theme map (#258) rides on the embed script tag."""
    html = _read(COMMENTS_INCLUDE)
    for attribute, liquid in (
        ("data-light-theme", "site.giscus.light_theme"),
        ("data-dark-theme", "site.giscus.dark_theme"),
    ):
        assert f'{attribute}="{{{{ {liquid}' in html, (
            f"the Giscus script tag must wire {attribute} from `{liquid}`"
        )


@pytest.mark.static
def test_comments_include_loads_the_theme_sync_script():
    """The first-party sync script (#258) ships deferred and versioned."""
    html = _read(COMMENTS_INCLUDE)
    match = re.search(
        r'<script src="(/assets/js/giscus-theme\.js\?v=([^"]+))" defer></script>',
        html,
    )
    assert match, (
        "comments.html must load giscus-theme.js deferred with the `?v=` "
        "build token (#61: a warm browser must never pair new markup with "
        "an old sync script)"
    )
    # The token must derive from the build, not from a literal.
    assert "site.time" in html, (
        "the sync script version token must be derived from the build"
    )
    # Inside the configured branch only: comment-less and unconfigured pages
    # fetch nothing.
    branch = html.index("site.giscus.repo != blank")
    fallback = html.index("comments-unavailable")
    assert branch < match.start() < fallback, (
        "the sync script tag must live inside the configured Giscus branch"
    )


SYNC_SCRIPT = REPO_ROOT / "assets" / "js" / "giscus-theme.js"

# Same tiny-script budget as the sibling header scripts (#114, #126, #220):
# the sync script is fetched on every comment page view.
MAX_SYNC_SCRIPT_BYTES = 3584
MAX_SYNC_SCRIPT_CODE_LINES = 80


@pytest.mark.static
def test_giscus_theme_script_exists_and_stays_tiny():
    assert SYNC_SCRIPT.is_file(), f"{SYNC_SCRIPT.relative_to(REPO_ROOT)} is missing"
    text = _read(SYNC_SCRIPT)
    assert len(text.encode("utf-8")) <= MAX_SYNC_SCRIPT_BYTES, (
        "the Giscus sync script must stay tiny; it is fetched on every "
        "comment page view"
    )
    code = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("/*", "*", "//"))
    ]
    assert len(code) <= MAX_SYNC_SCRIPT_CODE_LINES, (
        f"the Giscus sync script has {len(code)} code lines, expected at "
        f"most {MAX_SYNC_SCRIPT_CODE_LINES}"
    )
    # No dependency, no build step: the file runs as it is served.
    assert "import " not in text and "require(" not in text, (
        "the Giscus sync script must not depend on anything"
    )


@pytest.mark.static
def test_giscus_theme_script_syncs_via_the_postmessage_api():
    """The runtime contract (#258): setConfig without reload, silent fallback."""
    text = _read(SYNC_SCRIPT)
    assert "iframe.giscus-frame" in text, (
        "the sync must target the Giscus iframe (never a full reload)"
    )
    assert "setConfig" in text and "postMessage" in text, (
        "theme flips must go through the Giscus `setConfig` postMessage API"
    )
    assert "'https://giscus.app'" in text or '"https://giscus.app"' in text, (
        "the postMessage must be addressed at the Giscus origin"
    )
    assert "data-theme" in text, (
        "the script must prime the embed's `data-theme` before the lazy "
        "iframe boots and follow `html[data-theme]` afterwards"
    )
    assert "MutationObserver" in text, (
        "later flips (toggle clicks, OS changes) must be observed via the "
        "`html[data-theme]` attribute the toggle owns"
    )
    assert "data-light-theme" in text and "data-dark-theme" in text, (
        "the site theme must map through the configured Giscus light/dark "
        "themes, never a hardcoded pair"
    )
    assert text.count("try") >= 2 and "catch" in text, (
        "a missing iframe or an unavailable postMessage API must fall back "
        "to the page default silently"
    )
    # No third-party script beyond the existing embed: the only remote origin
    # this script may name is Giscus itself.
    remotes = re.findall(r"https://[A-Za-z0-9.-]+", text)
    assert remotes and all(url == "https://giscus.app" for url in remotes), (
        f"the sync script must name no remote origin but Giscus, got {remotes}"
    )


# --- production builds (need Ruby; no browser) ------------------------------


@pytest.fixture(scope="module")
def prod_site(tmp_path_factory):
    """Production build with the real config (Giscus enabled)."""
    destination = tmp_path_factory.mktemp("site-build-giscus-prod")
    return _build_production(destination, [BASE_CONFIG], "production")


def _overlay_build(tmp_path_factory, name, overlay_text, label):
    """Production build with a small YAML overlay merged over `_config.yml`."""
    workdir = tmp_path_factory.mktemp(f"site-build-giscus-{name}-config")
    overlay = workdir / "overlay.yml"
    overlay.write_text(overlay_text, encoding="utf-8")
    destination = tmp_path_factory.mktemp(f"site-build-giscus-{name}")
    return _build_production(
        destination, [BASE_CONFIG, overlay], f"production, {label}"
    )


@pytest.fixture(scope="module")
def prod_site_comments_off(tmp_path_factory):
    """Production build with the comments provider switched off.

    No provider means ``comments.html`` renders nothing: the "no embed"
    negative case.
    """
    return _overlay_build(
        tmp_path_factory, "off", PROVIDER_OFF_OVERLAY, "comments off"
    )


@pytest.fixture(scope="module")
def prod_site_comments_disabled(tmp_path_factory):
    """Production build with the English sample post set to `comments: false`."""
    return _overlay_build(
        tmp_path_factory,
        "disabled",
        DISABLED_POST_OVERLAY,
        "post comments disabled",
    )


@contextlib.contextmanager
def _served_url(directory):
    handler = functools.partial(_QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def prod_site_url(prod_site):
    with _served_url(prod_site) as url:
        yield url


@pytest.fixture(scope="module")
def prod_site_comments_off_url(prod_site_comments_off):
    with _served_url(prod_site_comments_off) as url:
        yield url


@pytest.fixture(scope="module")
def prod_site_comments_disabled_url(prod_site_comments_disabled):
    with _served_url(prod_site_comments_disabled) as url:
        yield url


def test_production_build_renders_giscus_section_and_script(prod_site):
    html = (prod_site / EN_POST_REL).read_text(encoding="utf-8")
    assert 'class="comments" id="comments"' in html, (
        "the enabled post must render the comments section container"
    )
    assert "Comments</h2>" in html

    tag = _giscus_script_tag(html)
    assert tag is not None, (
        "the enabled post must embed the Giscus client script"
    )
    for attribute, value in EXPECTED_ATTRS.items():
        assert f'{attribute}="{value}"' in tag, (
            f"the Giscus script must carry {attribute}={value!r}"
        )
    assert 'data-lang="en"' in tag, (
        "the English post must request the English Giscus UI"
    )
    assert 'crossorigin="anonymous"' in tag
    assert re.search(r"<script[^>]*\basync\b", tag), (
        "the Giscus script must load asynchronously"
    )


def test_production_build_localizes_giscus_lang(prod_site):
    vi_html = (prod_site / VI_POST_REL).read_text(encoding="utf-8")
    tag = _giscus_script_tag(vi_html)
    assert tag is not None, (
        "the Vietnamese post must embed the Giscus client script"
    )
    assert 'data-lang="vi"' in tag, (
        "the Vietnamese post must request the Vietnamese Giscus UI"
    )


def test_production_build_links_the_theme_sync_script(prod_site):
    """The deferred sync script (#258) ships on comment pages, versioned."""
    for post_rel in (EN_POST_REL, VI_POST_REL):
        html = (prod_site / post_rel).read_text(encoding="utf-8")
        match = re.search(
            r'<script src="(/assets/js/giscus-theme\.js\?v=([^"]+))" defer>'
            r"</script>",
            html,
        )
        assert match, (
            f"{post_rel} must link the deferred Giscus theme sync script"
        )
        assert re.fullmatch(r"\d+", match.group(2)), (
            f"{post_rel}: the sync script token must be a non-empty epoch, "
            f"got {match.group(2)!r}"
        )


def test_comments_off_build_renders_no_embed(prod_site_comments_off):
    for post_rel in (EN_POST_REL, VI_POST_REL):
        html = (prod_site_comments_off / post_rel).read_text(encoding="utf-8")
        assert _giscus_script_tag(html) is None
        assert "giscus.app" not in html
        assert 'id="comments"' not in html
        assert DISABLED_MESSAGE not in html
        assert UNAVAILABLE_MESSAGE not in html


def test_disabled_post_build_renders_message_without_embed(
    prod_site_comments_disabled,
):
    disabled_html = (prod_site_comments_disabled / EN_POST_REL).read_text(
        encoding="utf-8"
    )
    assert DISABLED_MESSAGE in disabled_html
    assert "comments-disabled-message" in disabled_html
    assert _giscus_script_tag(disabled_html) is None
    assert "giscus.app" not in disabled_html

    # The sibling post is unaffected: its embed still renders.
    enabled_html = (prod_site_comments_disabled / VI_POST_REL).read_text(
        encoding="utf-8"
    )
    assert _giscus_script_tag(enabled_html) is not None


# --- browser guards (need Ruby + Chromium) -----------------------------------


def test_enabled_post_attempts_giscus_load_without_real_network(
    page, prod_site_url
):
    requests = []
    _intercept_giscus(page, requests)

    # Event wait (#276): resolve the moment the stubbed route observes the
    # client load instead of sleeping a fixed second for it.
    with page.expect_request(
        lambda request: "giscus.app" in request.url, timeout=10_000
    ):
        page.goto(f"{prod_site_url}/{EN_POST_REL}")
    script = page.locator('script[src="https://giscus.app/client.js"]')
    assert script.count() == 1, (
        "the enabled post must embed exactly one Giscus client script"
    )
    # `data-theme` is deliberately skipped here: the #258 sync script reprimes
    # it at runtime to the site-mapped theme, so the live value depends on the
    # painted theme. The shipped default stays pinned on the built file in
    # `test_production_build_renders_giscus_section_and_script`.
    for attribute, value in EXPECTED_ATTRS.items():
        if attribute == "data-theme":
            continue
        assert script.first.get_attribute(attribute) == value
    assert script.first.get_attribute("data-lang") == "en"

    # Settle on quiet instead of sleeping: the aborted client load must not
    # retry off-page, and no other Giscus request may slip past the
    # interception before the log assertions below.
    _wait_for_network_quiet(page)
    assert requests, "expected the page to attempt the Giscus client load"
    assert all("giscus.app" in url for url in requests), (
        f"every Giscus-bound request must go through the aborting "
        f"interception (zero real network), saw: {requests}"
    )
    assert page.locator("iframe.giscus-frame").count() == 0, (
        "the aborted client must not boot a Giscus iframe"
    )


def test_disabled_post_shows_message_and_makes_no_giscus_requests(
    page, prod_site_comments_disabled_url
):
    requests = []
    _intercept_giscus(page, requests)

    page.goto(f"{prod_site_comments_disabled_url}/{EN_POST_REL}")
    message = page.locator(".comments-disabled-message")
    message.wait_for(state="visible", timeout=10_000)
    assert DISABLED_MESSAGE in message.inner_text()
    assert (
        page.locator('script[src*="giscus.app"]').count() == 0
    ), "the disabled post must embed no Giscus script"
    # Settle on quiet instead of sleeping: a stray request shows up in the
    # recorded log before the emptiness assertion below.
    _wait_for_network_quiet(page)
    assert requests == [], (
        f"disabled post must not contact Giscus, saw: {requests}"
    )


def test_comments_off_post_makes_no_giscus_requests(
    page, prod_site_comments_off_url
):
    requests = []
    _intercept_giscus(page, requests)

    page.goto(f"{prod_site_comments_off_url}/{VI_POST_REL}")
    page.locator(".post-content").wait_for(state="visible", timeout=10_000)
    assert page.locator("#comments").count() == 0
    assert (
        page.locator('script[src*="giscus.app"]').count() == 0
    ), "the post with comments switched off must embed no Giscus script"
    # Settle on quiet instead of sleeping: a stray request shows up in the
    # recorded log before the emptiness assertion below.
    _wait_for_network_quiet(page)
    assert requests == [], (
        f"page with comments switched off must not contact Giscus, saw: "
        f"{requests}"
    )


# --- browser guards: theme sync with a mocked Giscus client (#258) ----------


#: Stand-in for ``https://giscus.app/client.js``: like the real client with
#: ``data-loading="lazy"`` it boots the ``iframe.giscus-frame`` when the
#: comments section scrolls into view (or immediately when
#: ``window.__giscusEager`` is set, modelling a client that wins the race
#: against the deferred sync script). It records the ``data-theme`` it booted
#: with, and its same-origin ``postMessage`` calls are observable from the
#: test. Zero real network.
GISCUS_CLIENT_STUB = """(function () {
  var embed = document.currentScript;
  window.__giscusBootTheme = null;
  window.__giscusBooted = false;
  window.__giscusMessages = [];
  function boot() {
    if (window.__giscusBooted) return;
    window.__giscusBooted = true;
    window.__giscusBootTheme = embed ? embed.getAttribute('data-theme') : null;
    var frame = document.createElement('iframe');
    frame.className = 'giscus-frame';
    frame.setAttribute('title', 'Comments');
    // An explicit src like the real widget: the initial navigation completes
    // asynchronously and fires `load`, which is what the sync script listens
    // for. A bare about:blank iframe loads synchronously with no event.
    frame.src = 'about:blank';
    var mount = document.getElementById('comments') || document.body;
    mount.appendChild(frame);
  }
  var mount = document.getElementById('comments');
  if (window.__giscusEager || !('IntersectionObserver' in window) || !mount) {
    boot();
  } else {
    new IntersectionObserver(function (entries, observer) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) {
          observer.disconnect();
          boot();
          break;
        }
      }
    }).observe(mount);
  }
})();"""

GISCUS_EMBED_SELECTOR = 'script[src="https://giscus.app/client.js"]'


def _stub_giscus_client(browser_page, requests):
    """Serve the mock client; abort anything else Giscus-bound."""

    def fulfill(route):
        requests.append(route.request.url)
        route.fulfill(
            status=200,
            content_type="application/javascript",
            body=GISCUS_CLIENT_STUB,
        )

    def abort(route):
        requests.append(route.request.url)
        route.abort()

    browser_page.route("**://giscus.app/client.js", fulfill)
    browser_page.route("**://*.giscus.app/**", abort)


#: Observes the page's ``postMessage`` calls into the Giscus iframe. Installed
#: via ``add_init_script`` (before every page script), it wraps
#: ``document.querySelector`` so the app's ``iframe.giscus-frame`` lookups
#: resolve to a facade whose ``postMessage`` records every call and then
#: delegates to the live window. The facade resolves ``contentWindow`` at call
#: time, so navigations cannot orphan it the way patching the ``Window``
#: object (or shadowing ``contentWindow``, ``LegacyUnforgeable``) would.
#: Every other selector delegates to the native lookup untouched.
GISCUS_POSTMESSAGE_OBSERVER = """(function () {
  window.__giscusMessages = [];
  var realQuerySelector = document.querySelector.bind(document);
  document.querySelector = function (selector) {
    var el = realQuerySelector(selector);
    if (selector === 'iframe.giscus-frame' && el) {
      if (!el.__giscusProxy) {
        el.__giscusProxy = new Proxy(el, {
          get: function (target, prop) {
            if (prop === 'contentWindow') {
              var win = target.contentWindow;
              if (!win || !win.postMessage) return win;
              return {
                postMessage: function (message, origin) {
                  window.__giscusMessages.push({
                    message: message,
                    origin: origin,
                  });
                  return win.postMessage(message, origin);
                },
              };
            }
            var value = target[prop];
            return typeof value === 'function' ? value.bind(target) : value;
          },
        });
      }
      return el.__giscusProxy;
    }
    return el;
  };
})();"""


@pytest.mark.parametrize("post_rel", [EN_POST_REL, VI_POST_REL])
@pytest.mark.parametrize(
    "color_scheme,stored,expected",
    [
        ("light", None, "light"),
        ("dark", None, "dark"),
        ("dark", "light", "light"),
        ("light", "dark", "dark"),
    ],
)
def test_giscus_theme_matches_the_site_theme_and_follows_the_toggle(
    browser, prod_site_url, post_rel, color_scheme, stored, expected
):
    """All four OS x site combos (EN + VI): paint + flip without reload (#258).

    The stored choice (or the OS preference on first visit) primes the
    embed's ``data-theme`` before the lazy iframe boots, and the header
    toggle repaints the live iframe through ``setConfig`` while the iframe
    element itself stays put.
    """
    flipped = "dark" if expected == "light" else "light"
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, color_scheme=color_scheme
    )
    context.add_init_script(GISCUS_POSTMESSAGE_OBSERVER)
    if stored is not None:
        context.add_init_script(
            f'window.localStorage.setItem("theme", "{stored}");'
        )
    try:
        test_page = context.new_page()
        errors = []
        test_page.on("pageerror", lambda exc: errors.append(exc))
        requests = []
        _stub_giscus_client(test_page, requests)

        test_page.goto(f"{prod_site_url}/{post_rel}")
        test_page.locator("#comments").wait_for(state="attached", timeout=10_000)
        # Lazy parity, without a fixed sleep (#276): first wait for the stub
        # client to execute (it sets `__giscusBooted = false` on boot-up, so
        # the assertion below cannot pass trivially before the script runs),
        # then settle two animation frames to give the lazy
        # IntersectionObserver its chance to fire. Below the fold it must
        # not boot yet, so the deferred sync script always primes
        # `data-theme` first.
        test_page.wait_for_function(
            "() => window.__giscusBooted !== undefined", timeout=10_000
        )
        test_page.evaluate(
            "() => new Promise((resolve) => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        assert test_page.evaluate("() => window.__giscusBooted") is False, (
            f"{post_rel}: the lazy client must not boot above the fold"
        )
        test_page.locator("#comments").scroll_into_view_if_needed()
        test_page.wait_for_function(
            "() => window.__giscusBooted === true",
            timeout=10_000,
        )
        assert test_page.evaluate("() => window.__giscusBootTheme") == expected, (
            f"{post_rel}: a {color_scheme} OS with stored {stored!r} must boot "
            f"Giscus on {expected}"
        )
        test_page.wait_for_function(
            f"() => document.querySelector('{GISCUS_EMBED_SELECTOR}')"
            f".getAttribute('data-theme') === '{expected}'",
            timeout=10_000,
        )
        test_page.wait_for_function(
            "() => window.__giscusMessages.length > 0", timeout=10_000
        )
        initial = test_page.evaluate(
            "() => window.__giscusMessages.map((m) => "
            "m.message.giscus.setConfig.theme)"
        )
        assert initial and all(theme == expected for theme in initial), (
            f"{post_rel}: every pre-flip setConfig must carry {expected}, "
            f"saw {initial}"
        )

        test_page.evaluate(
            "() => { window.__giscusFrame = "
            "document.querySelector('iframe.giscus-frame'); }"
        )
        test_page.locator(".theme-toggle").click()
        test_page.wait_for_function(
            "() => window.__giscusMessages.some((m) => m.message "
            f"&& m.message.giscus && m.message.giscus.setConfig "
            f"&& m.message.giscus.setConfig.theme === '{flipped}')",
            timeout=10_000,
        )
        last = test_page.evaluate(
            "() => window.__giscusMessages[window.__giscusMessages.length - 1]"
        )
        assert last == {
            "message": {"giscus": {"setConfig": {"theme": flipped}}},
            "origin": "https://giscus.app",
        }, f"{post_rel}: the flip must post the exact setConfig shape, saw {last}"
        assert test_page.evaluate(
            "() => document.querySelector('iframe.giscus-frame') "
            "=== window.__giscusFrame"
        ), f"{post_rel}: the toggle must repaint Giscus without reloading it"
        assert test_page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        ) == flipped, f"{post_rel}: the site theme itself must flip"

        assert errors == [], f"{post_rel}: unexpected page errors: {errors}"
        assert requests, f"{post_rel}: expected the mocked Giscus client load"
        assert all(
            "giscus.app" in url and url.endswith("/client.js") for url in requests
        ), (
            f"{post_rel}: every Giscus-bound request must be the mocked "
            f"client (zero real network), saw: {requests}"
        )
    finally:
        context.close()


def test_giscus_eager_boot_is_corrected_without_reload(
    browser, prod_site_url
):
    """A client that beats the deferred prime still lands on the site theme.

    With ``__giscusEager`` the stub boots during parsing; the sync script's
    on-load ``setConfig`` must still repaint it to the stored site theme, and
    the toggle must keep working — all without replacing the iframe.
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, color_scheme="dark"
    )
    context.add_init_script(GISCUS_POSTMESSAGE_OBSERVER)
    context.add_init_script(
        'window.__giscusEager = true; window.localStorage.setItem("theme", "light");'
    )
    try:
        test_page = context.new_page()
        errors = []
        test_page.on("pageerror", lambda exc: errors.append(exc))
        requests = []
        _stub_giscus_client(test_page, requests)

        test_page.goto(f"{prod_site_url}/{EN_POST_REL}")
        test_page.wait_for_function(
            "() => window.__giscusBooted === true", timeout=10_000
        )
        # Two legal interleavings of the eager race (async stub vs deferred
        # prime): the stub may read the shipped ``preferred_color_scheme``
        # fallback (Chromium/Firefox) or the already-primed ``light``
        # (WebKit runs the deferred prime first). Either way the page must
        # converge on the site theme through ``setConfig`` below.
        assert test_page.evaluate("() => window.__giscusBootTheme") in (
            "preferred_color_scheme",
            "light",
        ), "the eager boot must read the shipped fallback or the primed theme"
        test_page.wait_for_function(
            "() => window.__giscusMessages.length > 0", timeout=10_000
        )
        corrected = test_page.evaluate(
            "() => window.__giscusMessages.map((m) => "
            "m.message.giscus.setConfig.theme)"
        )
        assert corrected and all(theme == "light" for theme in corrected), (
            f"the on-load setConfig must correct the eager boot to light, "
            f"saw {corrected}"
        )

        test_page.evaluate(
            "() => { window.__giscusFrame = "
            "document.querySelector('iframe.giscus-frame'); }"
        )
        test_page.locator(".theme-toggle").click()
        test_page.wait_for_function(
            "() => window.__giscusMessages.some((m) => m.message "
            "&& m.message.giscus && m.message.giscus.setConfig "
            "&& m.message.giscus.setConfig.theme === 'dark')",
            timeout=10_000,
        )
        last = test_page.evaluate(
            "() => window.__giscusMessages[window.__giscusMessages.length - 1]"
        )
        assert last == {
            "message": {"giscus": {"setConfig": {"theme": "dark"}}},
            "origin": "https://giscus.app",
        }, f"the flip must post the exact setConfig shape, saw {last}"
        assert test_page.evaluate(
            "() => document.querySelector('iframe.giscus-frame') "
            "=== window.__giscusFrame"
        ), "the toggle must repaint Giscus without reloading it"

        assert errors == [], f"unexpected page errors: {errors}"
        assert requests, "expected the mocked Giscus client load"
        assert all(
            "giscus.app" in url and url.endswith("/client.js") for url in requests
        ), (
            "every Giscus-bound request must be the mocked client "
            f"(zero real network), saw: {requests}"
        )
    finally:
        context.close()


def test_theme_toggle_without_the_giscus_iframe_is_a_silent_noop(
    browser, prod_site_url
):
    """Aborted Giscus load: the embed stays primed, the toggle never throws.

    When the ``postMessage`` API has no iframe to talk to, the sync falls
    back to the page default (the primed ``data-theme``) instead of failing.
    """
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    try:
        test_page = context.new_page()
        errors = []
        test_page.on("pageerror", lambda exc: errors.append(exc))
        requests = []
        _intercept_giscus(test_page, requests)

        test_page.goto(f"{prod_site_url}/{EN_POST_REL}")
        test_page.wait_for_selector(".theme-toggle", state="visible", timeout=10_000)
        embed = test_page.locator(GISCUS_EMBED_SELECTOR)
        test_page.wait_for_function(
            f"() => document.querySelector('{GISCUS_EMBED_SELECTOR}')"
            ".getAttribute('data-theme') === 'light'",
            timeout=10_000,
        )
        assert test_page.locator("iframe.giscus-frame").count() == 0

        test_page.locator(".theme-toggle").click()
        assert embed.get_attribute("data-theme") == "dark", (
            "the primed fallback must follow the toggle even with no iframe"
        )
        test_page.locator(".theme-toggle").click()
        assert embed.get_attribute("data-theme") == "light"

        assert test_page.locator("iframe.giscus-frame").count() == 0
        assert errors == [], f"unexpected page errors: {errors}"
        assert requests, "expected the page to attempt the Giscus client load"
    finally:
        context.close()
