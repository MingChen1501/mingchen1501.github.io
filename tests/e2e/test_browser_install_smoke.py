"""Static guard for the E2E browser-install reliability policy (#421).

Pins the workflow contract: the slow layer is `playwright install
--with-deps` (apt stalls of 10-40 min on warm caches), never the suite
itself, so the workflow (1) skips apt on a Playwright cache hit, (2)
proves the engine launches with a real headless smoke test before
deciding about OS dependencies, and (3) fails fast with evidence
otherwise. A missing pytest log (setup/install died first) warns, and
the suite rollup pins the head SHA while failing closed.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows" / "e2e.yml"


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps():
    return _workflow()["jobs"]["browser-e2e"]["steps"]


def _step(prefix):
    matches = [s for s in _steps() if s.get("name", "").startswith(prefix)]
    assert matches, f"e2e.yml lost the {prefix!r} step (#421)"
    assert len(matches) == 1, f"e2e.yml has {len(matches)} {prefix!r} steps"
    return matches[0]


def test_job_has_hang_backstop():
    job = _workflow()["jobs"]["browser-e2e"]
    assert job.get("timeout-minutes") == 25


def test_cache_step_exposes_cache_hit():
    cache = _step("Cache Playwright browsers")
    assert cache.get("id") == "playwright-cache"


def test_cache_hit_step_smoke_gates_install_deps():
    # The deciding gate is a real headless launch (about:blank), not
    # parsed install output: only a launch proves the OS libraries are
    # present. install-deps runs solely as the smoke-failure fallback.
    step = _step("Install Playwright browser (")
    assert step.get("if") == "steps.playwright-cache.outputs.cache-hit == 'true'"
    run = step["run"]
    assert "sync_playwright" in run
    assert "about:blank" in run
    assert "timeout 60 python" in run
    assert "install-deps" in run
    assert "--with-deps" not in run


def test_cache_miss_step_uses_bounded_with_deps():
    step = _step("Install Playwright browser with deps (")
    assert step.get("if") == "steps.playwright-cache.outputs.cache-hit != 'true'"
    assert step.get("timeout-minutes") == 15
    assert "--with-deps" in step["run"]
    assert "timeout 6m" in step["run"]


def test_pytest_log_upload_warns_when_suite_never_ran():
    step = _step("Upload pytest log (")
    assert step["with"]["if-no-files-found"] == "warn"


def test_summary_pins_head_sha():
    run = _step("Summarize engine result (")["run"]
    assert "GITHUB_SHA" in run
    assert "FAILED" in run
