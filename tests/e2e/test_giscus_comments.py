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

    page.goto(f"{prod_site_url}/{EN_POST_REL}")
    script = page.locator('script[src="https://giscus.app/client.js"]')
    assert script.count() == 1, (
        "the enabled post must embed exactly one Giscus client script"
    )
    for attribute, value in EXPECTED_ATTRS.items():
        assert script.first.get_attribute(attribute) == value
    assert script.first.get_attribute("data-lang") == "en"

    # Give the page a moment: the aborted client load must not retry off-page
    # and no other Giscus request may slip past the interception.
    page.wait_for_timeout(1_000)
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
    page.wait_for_timeout(1_000)
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
    page.wait_for_timeout(1_000)
    assert requests == [], (
        f"page with comments switched off must not contact Giscus, saw: "
        f"{requests}"
    )
