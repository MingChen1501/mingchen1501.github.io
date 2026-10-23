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


def test_quiesce_apt_runs_before_any_install():
    # Fresh runners boot with unattended-upgrades holding dpkg's lock
    # (run 39902712204): the quiesce step must exist and run before
    # every step that can touch apt.
    names = [s.get("name", "") for s in _steps()]
    assert "Quiesce apt (#421)" in names
    quiesce_at = names.index("Quiesce apt (#421)")
    for prefix in ("Install Playwright browser (", "Install Playwright browser with deps ("):
        at = next(i for i, n in enumerate(names) if n.startswith(prefix))
        assert quiesce_at < at, f"Quiesce apt must precede {prefix}"
    run = _steps()[quiesce_at]["run"]
    assert "unattended-upgrades" in run
    assert "kill -9" not in run


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


def test_install_steps_release_lock_only_from_verified_upgraders():
    # Lock contention is handled apt-natively (DPkg::Lock::Timeout) plus
    # a fallback that TERMs the holder ONLY after identifying it by full
    # command line as an unattended-upgrades worker; unknown holders are
    # never touched, and kill -9 is never used.
    for prefix in ("Install Playwright browser (", "Install Playwright browser with deps ("):
        run = _step(prefix)["run"]
        assert "wait_for_apt_lock" not in run
        assert "release_apt_lock" in run
        assert "-o comm=" in run and "-o args=" in run
        assert "kill -TERM" in run
        assert "kill -9" not in run


def test_quiesce_step_disables_periodic_triggers_and_verifies():
    run = _step("Quiesce apt (#421)")["run"]
    assert "DPkg::Lock::Timeout" in run
    assert "apt-daily" in run
    assert "is-active" in run
    assert "kill -9" not in run


def test_apt_package_cache_straddles_install():
    # The 117 MB webkit system-deb download cannot be retried into
    # existence on a trickling mirror (run 39904461383): cache only
    # finished *.debs per engine + Playwright version (glob excludes
    # partial/ and lock files, so root-owned partials can never break
    # the save). The dir must be runner-owned before restore, and a
    # final always-run chown must precede the post-job save.
    names = [s.get("name", "") for s in _steps()]
    prepare_at = names.index("Prepare apt package cache dir (#421)")
    cache_at = names.index("Cache apt packages (#421)")
    fix_at = names.index("Fix apt cache ownership (#421)")
    assert prepare_at < cache_at < fix_at
    for prefix in ("Install Playwright browser (", "Install Playwright browser with deps ("):
        at = next(i for i, n in enumerate(names) if n.startswith(prefix))
        assert cache_at < at, f"apt cache must restore before {prefix}"
    assert "chown" in _steps()[prepare_at]["run"]
    assert "/var/cache/apt/archives" in _steps()[prepare_at]["run"]
    cache_with = _steps()[cache_at]["with"]
    assert cache_with["path"] == "/var/cache/apt/archives/*.deb"
    assert "matrix.browser" in cache_with["key"]
    assert "playwright.outputs.version" in cache_with["key"]
    fix_step = _steps()[fix_at]
    assert fix_step.get("if") == "always()"
    assert "chown" in fix_step["run"]
    assert "/var/cache/apt/archives" in fix_step["run"]


def test_install_attempts_kill_process_group_on_timeout():
    # Plain `timeout` only signals the direct child, orphaning apt-get
    # with dpkg's lock (run 39916453942: PID 3641 survived attempt 1
    # and starved attempt 2). Both install steps cap attempts via a
    # setsid process-group kill, and TERM orphaned apt-get holders
    # (PPID 1) while never touching unknown live holders.
    for prefix in ("Install Playwright browser (", "Install Playwright browser with deps ("):
        run = _step(prefix)["run"]
        assert "run_capped()" in run
        assert "setsid" in run
        assert 'kill -TERM -- -"$child"' in run
        assert "-o ppid=" in run
        assert "PPID 1" in run


def test_install_attempts_are_timestamped():
    # Attempt start/end timestamps separate mirror stalls from lock
    # contention in the next red log.
    for prefix in ("Install Playwright browser (", "Install Playwright browser with deps ("):
        run = _step(prefix)["run"]
        assert "starting at $(date -u" in run
        assert "SECONDS - start" in run


def test_cache_miss_step_uses_bounded_with_deps():
    step = _step("Install Playwright browser with deps (")
    assert step.get("if") == "steps.playwright-cache.outputs.cache-hit != 'true'"
    assert step.get("timeout-minutes") == 25
    assert "--with-deps" in step["run"]
    assert "run_capped 600" in step["run"]
    assert "timeout 10m" not in step["run"]


def test_pytest_log_upload_warns_when_suite_never_ran():
    step = _step("Upload pytest log (")
    assert step["with"]["if-no-files-found"] == "warn"


def test_pytest_run_step_has_id_for_outcome_checks():
    assert _step("Run browser E2E,")["id"] == "pytest"


def test_visual_captures_warn_only_when_suite_never_ran():
    # Missing captures warn when install failed first (pytest skipped —
    # the job is already red for the real cause) and error only when
    # tests really ran and failed without captures.
    value = _step("Upload fresh visual captures (")["with"]["if-no-files-found"]
    assert "steps.pytest.outcome" in value
    assert "'warn'" in value and "'error'" in value


def test_summary_pins_head_sha():
    run = _step("Summarize engine result (")["run"]
    assert "GITHUB_SHA" in run
    assert "FAILED" in run
