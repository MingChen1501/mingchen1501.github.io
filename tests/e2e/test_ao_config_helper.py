"""Static guard for the safe AO project-config wrapper (issue #354).

`ao project set-config <id>` with a focused field flag *replaces* the
whole per-project config, which once wiped models, reviewers, and the
orchestrator pool rule. `script/ao-project-config.sh` exists so every
partial update merges into the current config and writes the full
object back with `--config-json`. This guard pins that contract:

- the wrapper exists, is executable POSIX sh, reads via
  `ao project get --json`, and writes only via `--config-json`;
- the wrapper refuses arg-parsing failures without touching `ao`;
- the merge itself preserves unmentioned keys: a fake `ao` stub on
  `PATH` answers `ao project get --json` with a canned config, so the
  tests assert `--dry-run` stdout keeps every unmentioned key without
  invoking `set-config`, and that a real run passes the merged JSON
  to `set-config` exactly once;
- the stderr before/after diff never prints `--env` values (keys only,
  values replaced with `***`);
- no repo doc or the wrapper itself instructs a bare
  `set-config <id> --flag` invocation.
"""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "ao-project-config.sh"

#: `set-config <id> --flag` occurrences whose flag is not allowlisted
#: are bare (whole-config-replacing) invocations.
BARE_FLAG = re.compile(r"set-config\s+\S+\s+--([\w-]+)")
ALLOWED_FLAGS = {"config-json", "clear", "json", "help"}


def bare_flags(text):
    return [
        match.group(1)
        for match in BARE_FLAG.finditer(text)
        if match.group(1) not in ALLOWED_FLAGS
    ]


def repo_docs():
    docs = sorted((REPO_ROOT / "docs").rglob("*.md"))
    docs += sorted(REPO_ROOT.glob("*.md"))
    return docs


def test_wrapper_exists_executable_posix_sh():
    assert SCRIPT.is_file()
    mode = os.stat(SCRIPT).st_mode
    assert mode & stat.S_IXUSR, "wrapper must be executable"
    first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "#!/bin/sh"


def test_wrapper_reads_before_writing_with_config_json():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "ao project get" in text
    assert "--json" in text
    assert "--config-json" in text
    assert "refusing to run" in text
    # The only set-config write path uses the full merged object
    # (comment/help lines describe the danger; the code line below is
    # the single place the config is written).
    assert 'ao project set-config "$PROJECT_ID" --config-json "$MERGED"' in text
    assert bare_flags(text) == []


def test_wrapper_rejects_bad_args_without_touching_ao():
    for args in ([], ["some-id", "--dry-run"], ["some-id", "--bogus"]):
        proc = subprocess.run(
            [str(SCRIPT), *args],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 2, args


def test_wrapper_help_mentions_dry_run_and_config_json():
    proc = subprocess.run(
        [str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--dry-run" in proc.stdout
    assert "--config-json" in proc.stdout


def test_no_doc_instructs_bare_set_config_flag():
    offenders = {}
    for doc in repo_docs():
        flags = bare_flags(doc.read_text(encoding="utf-8"))
        if flags:
            offenders[str(doc.relative_to(REPO_ROOT))] = flags
    assert offenders == {}, (
        "docs must not instruct bare 'ao project set-config <id> --flag' "
        f"invocations (whole-config replace): {offenders}"
    )


def test_bootstrap_and_rules_point_at_wrapper():
    bootstrap = (REPO_ROOT / "docs" / "agentic-template" / "bootstrap.md").read_text(
        encoding="utf-8"
    )
    assert "script/ao-project-config.sh" in bootstrap
    rules = (REPO_ROOT / "docs" / "ao-rules.md").read_text(encoding="utf-8")
    assert "script/ao-project-config.sh" in rules


#: Canned config served by the fake `ao` stub: every key the wrapper is
#: *not* asked to change must survive the merge untouched.
CANNED_CONFIG = {
    "status": "ok",
    "project": {
        "id": "test-proj",
        "config": {
            "agentRulesFile": "AGENTS.md",
            "orchestratorRules": "orchestrator pool rules",
            "agentConfig": {"model": "top-model", "permissions": "allow"},
            "worker": {
                "agent": "opencode",
                "agentConfig": {"model": "worker-model"},
            },
            "orchestrator": {
                "agent": "opencode",
                "agentConfig": {"model": "orch-model"},
            },
            "reviewers": [{"harness": "opencode"}],
            "env": {"KEEP_ME": "keep-value"},
            "sessionPrefix": "test",
        },
    },
}

FAKE_AO_STUB = """\
#!/bin/sh
# Fake `ao` for the merge-teeth tests: answers `project get --json`
# with the canned config and records every `project set-config`
# invocation (one line per call in $FAKE_AO_CALLS, the --config-json
# payload in $FAKE_AO_SETCONFIG_JSON).
set -u
CALLS_FILE="${FAKE_AO_CALLS:?}"
if [ "${1:-}" = "project" ] && [ "${2:-}" = "get" ]; then
  cat "${FAKE_AO_GET_JSON:?}"
  exit 0
fi
if [ "${1:-}" = "project" ] && [ "${2:-}" = "set-config" ]; then
  printf 'set-config\\n' >>"$CALLS_FILE"
  prev=""
  for arg in "$@"; do
    if [ "$prev" = "--config-json" ]; then
      printf '%s' "$arg" >"${FAKE_AO_SETCONFIG_JSON:?}"
    fi
    prev="$arg"
  done
  exit 0
fi
echo "fake ao: unexpected invocation: $*" >&2
exit 1
"""


@pytest.fixture
def fake_ao(tmp_path, monkeypatch):
    """Put a fake `ao` executable first on PATH.

    The stub serves CANNED_CONFIG for `ao project get <id> --json`
    and records `ao project set-config` calls so tests can assert
    exactly when (and with what payload) the wrapper writes.
    """
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    get_json = tmp_path / "get.json"
    get_json.write_text(json.dumps(CANNED_CONFIG), encoding="utf-8")
    stub = bin_dir / "ao"
    stub.write_text(FAKE_AO_STUB, encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv(
        "PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    )
    monkeypatch.setenv("FAKE_AO_GET_JSON", str(get_json))
    calls = tmp_path / "calls.log"
    monkeypatch.setenv("FAKE_AO_CALLS", str(calls))
    monkeypatch.setenv(
        "FAKE_AO_SETCONFIG_JSON", str(tmp_path / "set-config.json")
    )
    return {"calls": calls, "set_config_json": tmp_path / "set-config.json"}


def assert_unmentioned_keys_preserved(merged):
    assert merged["agentRulesFile"] == "AGENTS.md"
    assert merged["orchestratorRules"] == "orchestrator pool rules"
    assert merged["worker"]["agentConfig"]["model"] == "worker-model"
    assert merged["orchestrator"]["agentConfig"]["model"] == "orch-model"
    assert merged["reviewers"] == [{"harness": "opencode"}]
    assert merged["env"]["KEEP_ME"] == "keep-value"
    assert merged["sessionPrefix"] == "test"


def test_wrapper_dry_run_preserves_unmentioned_keys_and_writes_nothing(fake_ao):
    proc = subprocess.run(
        [str(SCRIPT), "test-proj", "--model", "new-model", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    merged = json.loads(proc.stdout)
    assert merged["agentConfig"]["model"] == "new-model"
    assert_unmentioned_keys_preserved(merged)
    assert not fake_ao["calls"].exists(), "--dry-run must not call set-config"


def test_wrapper_real_run_merges_and_calls_set_config_once(fake_ao):
    proc = subprocess.run(
        [str(SCRIPT), "test-proj", "--model", "new-model"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert fake_ao["calls"].read_text(encoding="utf-8").splitlines() == [
        "set-config"
    ]
    payload = json.loads(
        fake_ao["set_config_json"].read_text(encoding="utf-8")
    )
    assert payload["agentConfig"]["model"] == "new-model"
    assert_unmentioned_keys_preserved(payload)


def test_wrapper_diff_redacts_env_values(fake_ao):
    proc = subprocess.run(
        [str(SCRIPT), "test-proj", "--env", "MYSECRET=topsecret123", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "topsecret123" not in proc.stderr
    assert "MYSECRET" in proc.stderr
    assert "***" in proc.stderr
    # The stdout merged object still carries the real value: it is the
    # payload a real run hands to `set-config --config-json`.
    merged = json.loads(proc.stdout)
    assert merged["env"]["MYSECRET"] == "topsecret123"
    assert merged["env"]["KEEP_ME"] == "keep-value"
    assert not fake_ao["calls"].exists(), "--dry-run must not call set-config"
