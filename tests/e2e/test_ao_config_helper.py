"""Static guard for the safe AO project-config wrapper (issue #354).

`ao project set-config <id>` with a focused field flag *replaces* the
whole per-project config, which once wiped models, reviewers, and the
orchestrator pool rule. `script/ao-project-config.sh` exists so every
partial update merges into the current config and writes the full
object back with `--config-json`. This guard pins that contract:

- the wrapper exists, is executable POSIX sh, reads via
  `ao project get --json`, and writes only via `--config-json`;
- the wrapper refuses arg-parsing failures without touching `ao`;
- no repo doc or the wrapper itself instructs a bare
  `set-config <id> --flag` invocation.
"""

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
