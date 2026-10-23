"""Static guard for the agent-ops metrics scripts (issue #392).

Pins the contract of `script/agent-metrics.py` and
`script/dora-metrics.py`:

- both scripts exist and answer `--help` without network or `gh`;
- `agent-metrics.py --format md` runs offline (missing DB and empty DB
  degrade to `Unavailable`, exit 0, no traceback) and is deterministic
  (identical output modulo the `generated_at` stamp);
- the AO database is never opened for writing: every `sqlite3.connect`
  call in the script passes `mode=ro`, `PRAGMA query_only = ON` is set,
  and the script is stdlib-only (every import is in
  `sys.stdlib_module_names`);
- role parsing prefers the longest canonical prefix (`dev-peer-review`
  beats `dev`).

No network, no Ruby, no browser: safe for the static CI job.
"""

import ast
import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SCRIPT = REPO_ROOT / "script" / "agent-metrics.py"
DORA_SCRIPT = REPO_ROOT / "script" / "dora-metrics.py"
REAL_DB = Path.home() / ".ao" / "data" / "ao.db"


def run_script(script, *args, env=None):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    # Offline: an empty git-credential helper cannot leak, but force no
    # network use at all by clearing token-ish variables.
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        merged.pop(key, None)
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        env=merged,
    )


def load_module(script):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        script.stem.replace("-", "_"), script
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scripts_exist_and_are_executable_python():
    for script in (AGENT_SCRIPT, DORA_SCRIPT):
        assert script.is_file(), script
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, "%s must be executable" % script
        first = script.read_text(encoding="utf-8").splitlines()[0]
        assert first == "#!/usr/bin/env python3", first


def test_help_works_without_network():
    for script in (AGENT_SCRIPT, DORA_SCRIPT):
        proc = run_script(script, "--help")
        assert proc.returncode == 0, proc.stderr
        assert "usage" in proc.stdout


def test_agent_report_missing_db_degrades_gracefully(tmp_path):
    missing = tmp_path / "no-such-db.sqlite3"
    proc = run_script(
        AGENT_SCRIPT, "--format", "md", "--db", str(missing),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    assert "Unavailable" in proc.stdout


def test_agent_report_empty_db_degrades_gracefully(tmp_path):
    import sqlite3

    empty = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty)).close()
    proc = run_script(
        AGENT_SCRIPT, "--format", "md", "--db", str(empty),
        "--pricing-dir", str(tmp_path / "no-pricing"),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    assert "Unavailable" in proc.stdout


def test_agent_report_is_deterministic(tmp_path):
    import sqlite3

    empty = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty)).close()

    def body():
        proc = run_script(
            AGENT_SCRIPT, "--format", "md", "--db", str(empty),
            "--pricing-dir", str(tmp_path / "no-pricing"),
        )
        assert proc.returncode == 0, proc.stderr
        return "\n".join(
            line for line in proc.stdout.splitlines()
            if not line.startswith("_Generated")
        )

    assert body() == body()


def test_agent_report_leaves_real_db_untouched():
    if not REAL_DB.is_file():
        pytest.skip("no local AO database on this machine")
    before = hashlib.sha256(REAL_DB.read_bytes()).hexdigest()
    proc = run_script(AGENT_SCRIPT, "--format", "md", "--days", "1")
    assert proc.returncode == 0, proc.stderr
    after = hashlib.sha256(REAL_DB.read_bytes()).hexdigest()
    assert before == after


def connects_are_read_only(tree):
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name != "connect":
            continue
        first = node.args[0] if node.args else None
        text = ast.unparse(first) if first is not None else ""
        keywords = " ".join(
            ast.unparse(kw.value) for kw in node.keywords
        )
        if "mode=ro" not in text and "mode=ro" not in keywords:
            offenders.append(
                "connect() without mode=ro at line %d" % node.lineno
            )
    return offenders


def test_db_is_never_opened_for_writing():
    text = AGENT_SCRIPT.read_text(encoding="utf-8")
    assert "mode=ro" in text
    assert "query_only" in text
    tree = ast.parse(text)
    assert connects_are_read_only(tree) == []
    # Only read-path sqlite APIs are used: no executescript, no commit.
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert "executescript" not in calls
    assert "commit" not in calls
    # Refusal guard for non-SELECT statements stays in place.
    assert "WRITE_KEYWORDS" in text


def test_agent_script_is_stdlib_only():
    tree = ast.parse(AGENT_SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    assert imported, "expected some imports"
    assert imported <= stdlib, sorted(imported - stdlib)


def test_role_parsing_prefers_longest_prefix():
    module = load_module(AGENT_SCRIPT)
    assert module.parse_role("dev-peer-review #414 radius tokens") == (
        "dev-peer-review"
    )
    assert module.parse_role("dev #392 agent metrics + DORA") == "dev"
    assert module.parse_role("buffer: file something") == "buffer"
    assert module.parse_role("") == "unlabeled"
    assert module.parse_role("post-ai") == "other"
