"""Guard tests for the paths that must never be published (#82).

``_config.yml`` excludes the repository internals: the agent guide and the
agent kit, the E2E test suite, the CI helper scripts, the gem metadata, the
project docs and the retired Unity WebGL demo payload (``gam102.html`` +
``Build/`` + ``TemplateData/``).

The demo payload was deleted from the working tree (#186) but stays in the
``exclude:`` list as belt-and-braces, and ``test_retired_demo_payload_stays_
deleted`` fails if any of those paths reappears in the repo.

These guards keep that list honest:

- the ``exclude:`` list in ``_config.yml`` must keep naming every one of
  them, so a future config edit cannot silently re-publish them;
- the retired demo paths must not exist in the repository at all;
- the built site must contain no file from those paths.

The build guard uses the session-wide ``built_site`` fixture on purpose: it
builds the site into a temp directory, CI never creates ``_site`` and the
suite must build exactly once per session.  The config and repo guards are
``static`` tests (no Ruby, no browser) so they still run in the fast CI job.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "_config.yml"

# Every path that must never end up in the published site (#82).
EXCLUDED_PATHS = [
    "AGENTS.md",
    ".opencode",
    "tests",
    "script",
    "Gemfile",
    "Gemfile.lock",
    "minima.gemspec",
    "README.md",
    "LICENSE.txt",
    "CODE_OF_CONDUCT.md",
    "gam102.html",
    "Build",
    "TemplateData",
]

# Paths deleted from the working tree (#186) that must never return.
# Kept separate from EXCLUDED_PATHS on purpose: these must be absent from the
# repo itself, not just from the published site.
RETIRED_DEMO_PATHS = [
    "gam102.html",
    "Build",
    "TemplateData",
]

POST_URL_RE = re.compile(r"\A\d{4}/\d{2}/\d{2}/.+\.html\Z")


def _config_exclude():
    """Return the ``exclude:`` entries of ``_config.yml``, slash-normalised."""
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    return [str(entry).rstrip("/") for entry in config.get("exclude") or []]


def _published_paths(built_site):
    """Return every path (files and directories) inside the built site."""
    return {
        path.relative_to(built_site).as_posix()
        for path in built_site.rglob("*")
    }


@pytest.mark.static
def test_config_excludes_every_repository_internal():
    """``_config.yml`` must keep excluding every path listed above."""
    excluded = _config_exclude()
    missing = [path for path in EXCLUDED_PATHS if path not in excluded]
    assert not missing, (
        "_config.yml no longer excludes: " + ", ".join(missing)
    )


@pytest.mark.static
def test_retired_demo_payload_stays_deleted():
    """The Unity demo payload removed in #186 must not reappear in the repo."""
    present = [
        path for path in RETIRED_DEMO_PATHS if (REPO_ROOT / path).exists()
    ]
    assert not present, (
        "retired demo payload is back in the repo: " + ", ".join(present)
    )


def test_excluded_paths_are_absent_from_the_build(built_site):
    """No file from an excluded path may exist under the build destination."""
    published = _published_paths(built_site)
    for excluded in EXCLUDED_PATHS:
        offenders = sorted(
            name
            for name in published
            if name == excluded or name.startswith(excluded + "/")
        )
        assert not offenders, (
            f"{excluded} is published in {built_site}: " + ", ".join(offenders[:5])
        )


def test_the_exclusions_do_not_hide_the_real_site(built_site):
    """The guard must not pass because the build lost its real content."""
    assert (built_site / "index.html").is_file(), (
        f"the build has no index.html in {built_site}"
    )
    assert (built_site / "assets" / "css" / "style.css").is_file(), (
        f"the build has no stylesheet in {built_site}"
    )
    posts = [
        name
        for name in sorted(_published_paths(built_site))
        if POST_URL_RE.match(name)
    ]
    assert posts, f"the build has no post page in {built_site}"
