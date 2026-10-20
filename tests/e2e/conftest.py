"""Shared plumbing for the E2E suite (#56).

Two independent things are served and reused here so that no module rebuilds
or relaunches them on its own:

- ``tests/e2e/fixtures/`` over loopback HTTP (``e2e_server``) for the hermetic
  comments browser tests (script injection, network requests).
- the *real* site, built exactly once per session with
  ``bundle exec jekyll build`` into a temp directory (``built_site``), served
  over loopback HTTP (``built_site_url``) and driven by one Playwright browser
  (``browser``; engine via ``--browser-name``/``$E2E_BROWSER``, #209) for the
  layout/overflow and home tag-chip guards.

The build fixture logs its one invocation to stderr (and to ``$E2E_BUILD_LOG``
when set), so a run can prove the suite builds once instead of once per module.

``pytest_collection_modifyitems`` orders the browser-free ``static`` guards
first so a local ``python -m pytest tests/e2e`` run fails fast on cheap
guards; CI additionally splits the two groups into two jobs (``-m static`` /
``-m "not static"``).
"""

import contextlib
import functools
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

CUSTOM_SCSS_INDEX = REPO_ROOT / "_sass" / "minima" / "custom-styles.scss"
CUSTOM_SCSS_DIR = REPO_ROOT / "_sass" / "minima" / "custom"


def custom_styles_text():
    """Concatenated site-specific SCSS in cascade order (#174).

    ``custom-styles.scss`` is an index over ``_sass/minima/custom/_*.scss``;
    static guards read this concatenation so they see the same rules in the
    same order as the Sass compiler does.
    """
    index = CUSTOM_SCSS_INDEX.read_text(encoding="utf-8")
    parts = []
    for block in re.finditer(r"@import\s+(.*?);", index, re.S):
        for item in block.group(1).split(","):
            name = item.strip().strip("\"'")
            if not name.startswith("minima/custom/"):
                continue
            partial = CUSTOM_SCSS_DIR / ("_" + name[len("minima/custom/"):] + ".scss")
            parts.append(partial.read_text(encoding="utf-8"))
    assert parts, "custom-styles.scss imports no custom partials"
    return "\n".join(parts)

BUILD_TIMEOUT_S = 300

#: Browser engines the E2E suite can run on (#209). CI runs one job per
#: engine (``E2E_BROWSER``); locally ``--browser-name`` (or ``E2E_BROWSER``)
#: selects the engine. Chromium stays the default because it is the only
#: engine with a system-Chrome fallback and the fastest install.
BROWSER_NAMES = ("chromium", "firefox", "webkit")


def pytest_addoption(parser):
    parser.addoption(
        "--browser-name",
        action="store",
        default=os.environ.get("E2E_BROWSER", "chromium"),
        choices=BROWSER_NAMES,
        help="browser engine to drive the browser guards with "
        "(also via $E2E_BROWSER; #209)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "static: guard runs without Ruby or a browser (fast, fail-fast group)",
    )


def pytest_collection_modifyitems(config, items):
    """Run the ``static`` guards before the browser tests (fail fast)."""
    items.sort(key=lambda item: 0 if item.get_closest_marker("static") else 1)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def _served(directory):
    """Serve ``directory`` over loopback HTTP for the duration of the block."""
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


def _bundle():
    """Return the `bundle` executable, or None when Ruby is unavailable."""
    found = shutil.which("bundle")
    if found:
        return found
    for candidate in sorted(Path.home().glob(".gem/ruby/*/bin/bundle")):
        return str(candidate)
    return None


def _launch_browser(playwright, name):
    """Launch headless ``name`` (one of ``BROWSER_NAMES``) for the session.

    Chromium prefers a system Chrome install and falls back to Playwright's
    bundled Chromium, so ``playwright install`` can be skipped on machines
    that already have Chrome. Firefox and WebKit always use Playwright's
    bundled builds (``python -m playwright install firefox webkit``).
    """
    engine = getattr(playwright, name)
    if name == "chromium":
        args = ["--no-sandbox", "--disable-dev-shm-usage"]
        try:
            return engine.launch(channel="chrome", headless=True, args=args)
        except Exception:
            return engine.launch(headless=True, args=args)
    # Firefox/WebKit reject Chromium's sandbox flags, so launch with defaults.
    return engine.launch(headless=True)


@pytest.fixture(scope="session")
def e2e_server():
    """Serve ``tests/e2e/fixtures/`` for the comments browser tests."""
    with _served(FIXTURES_DIR) as url:
        yield url


@pytest.fixture(scope="session")
def built_site(tmp_path_factory):
    """Build the real site once per session and return the build destination.

    Every guard that needs the real site shares this single ``jekyll build``
    (dev environment: the external giscus embed is never fetched).
    """
    bundle = _bundle()
    if bundle is None:
        pytest.skip(
            "`bundle` not found: the guards that need the real site need Ruby + "
            "`bundle install` (CI installs both in .github/workflows/e2e.yml)"
        )
    destination = tmp_path_factory.mktemp("site-build")
    env = {k: v for k, v in os.environ.items() if k != "JEKYLL_ENV"}
    # `bundle` may have been found in a user gem directory that is not on PATH
    # (common for non-login shells); `bundle exec` needs it to resolve `jekyll`.
    env["PATH"] = os.pathsep.join(
        [str(Path(bundle).parent), env.get("PATH", "")]
    ).rstrip(os.pathsep)

    invocation = f"[e2e] {bundle} exec jekyll build --destination {destination}"
    print(invocation, file=sys.stderr)
    build_log = os.environ.get("E2E_BUILD_LOG")
    if build_log:
        with open(build_log, "a", encoding="utf-8") as handle:
            handle.write(invocation + "\n")

    result = subprocess.run(
        [bundle, "exec", "jekyll", "build", "--destination", str(destination)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_S,
    )
    if result.returncode != 0:
        pytest.fail(
            f"`jekyll build` failed with exit code {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    if not (destination / "index.html").is_file():
        pytest.fail(f"`jekyll build` produced no index.html in {destination}")
    return destination


@pytest.fixture(scope="session")
def built_site_url(built_site):
    """Serve the session's single build over loopback HTTP."""
    with _served(built_site) as url:
        yield url


@pytest.fixture(scope="session")
def browser_name(request):
    """Engine under test (``chromium``/``firefox``/``webkit``; #209).

    Browser guards that cannot run on an engine skip with an explicit reason,
    e.g. ``if browser_name == "webkit": pytest.skip("...")``.
    """
    return request.config.getoption("--browser-name")


@pytest.fixture(scope="session")
def browser(browser_name):
    """One headless browser shared by every browser test in the session."""
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, browser_name)
        try:
            yield browser
        finally:
            browser.close()
