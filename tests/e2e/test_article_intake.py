"""Static guard tests for script/article-intake (#190).

The orchestrator's cron-wake article-intake scan must list exactly the
eligible ``article`` issues (open, still labelled, no open PR covering them,
not claimed by a live session) and never double-list one issue. These tests
feed saved ``gh`` JSON through the script's offline mode, so they need no
network, no Ruby, and no browser.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "article-intake"
SKILL = (
    REPO_ROOT / ".opencode" / "skills" / "orchestrator" / "SKILL.md"
)


def _article(number, **overrides):
    issue = {
        "number": number,
        "title": "Article %s" % number,
        "url": "https://github.com/x/y/issues/%s" % number,
        "state": "open",
        "labels": [{"name": "article"}, {"name": "risk-low"}],
    }
    issue.update(overrides)
    return issue


def _pr(number, body="", headRefName="topic"):
    return {
        "number": number,
        "title": "PR %s" % number,
        "body": body,
        "headRefName": headRefName,
    }


def _run(issues, prs, tmp_dir, *extra_args):
    issues_file = tmp_dir / "issues.json"
    prs_file = tmp_dir / "prs.json"
    issues_file.write_text(json.dumps(issues), encoding="utf-8")
    prs_file.write_text(json.dumps(prs), encoding="utf-8")
    return subprocess.run(
        [
            str(SCRIPT),
            "--issues-file",
            str(issues_file),
            "--prs-file",
            str(prs_file),
            "--format",
            "json",
        ]
        + list(extra_args),
        capture_output=True,
        text=True,
    )


def _eligible(proc):
    assert proc.returncode == 0, proc.stderr
    return [entry["number"] for entry in json.loads(proc.stdout)]


def test_eligible_issue_is_listed(tmp_path, monkeypatch):
    """An open labelled article issue with no PR and no claim is eligible."""
    monkeypatch.chdir(tmp_path)
    assert _eligible(_run([_article(193)], [], tmp_path)) == [193]


def test_issue_covered_by_closing_pr_is_excluded(tmp_path, monkeypatch):
    """'Closes #N' / 'Fixes #N' in an open PR body excludes issue N."""
    monkeypatch.chdir(tmp_path)
    issues = [_article(193), _article(194)]
    prs = [_pr(7, body="Implements the draft.\n\nCloses #193")]
    assert _eligible(_run(issues, prs, tmp_path)) == [194]
    prs = [_pr(7, body="Fixes #193\nFixes #194")]
    assert _eligible(_run(issues, prs, tmp_path)) == []


def test_issue_covered_by_article_branch_is_excluded(tmp_path, monkeypatch):
    """An open PR on an ``article-…<N>…`` branch covers issue N."""
    monkeypatch.chdir(tmp_path)
    issues = [_article(193), _article(194)]
    prs = [_pr(7, headRefName="ao/s-1/article-193-draft")]
    assert _eligible(_run(issues, prs, tmp_path)) == [194]


def test_unrelated_pr_reference_does_not_cover(tmp_path, monkeypatch):
    """A bare '#N' mention without a closing keyword is not coverage."""
    monkeypatch.chdir(tmp_path)
    prs = [_pr(7, body="See also #193 for context")]
    assert _eligible(_run([_article(193)], prs, tmp_path)) == [193]


def test_claimed_issue_is_excluded(tmp_path, monkeypatch):
    """An issue owned by a live session is never double-spawned."""
    monkeypatch.chdir(tmp_path)
    issues = [_article(193), _article(194)]
    assert _eligible(_run(issues, [], tmp_path, "--claimed", "193")) == [194]
    claimed_file = tmp_path / "claimed.txt"
    claimed_file.write_text("#193, #194\n", encoding="utf-8")
    assert (
        _eligible(_run(issues, [], tmp_path, "--claimed-file", str(claimed_file)))
        == []
    )


def test_closed_or_unlabelled_issues_are_excluded(tmp_path, monkeypatch):
    """Closed issues and issues that lost the label are ineligible."""
    monkeypatch.chdir(tmp_path)
    issues = [
        _article(193, state="closed"),
        _article(194, labels=[{"name": "enhancement"}]),
        _article(195),
    ]
    assert _eligible(_run(issues, [], tmp_path)) == [195]


def test_each_issue_is_listed_once(tmp_path, monkeypatch):
    """Duplicate rows for one issue never produce two spawns."""
    monkeypatch.chdir(tmp_path)
    assert _eligible(_run([_article(193), _article(193)], [], tmp_path)) == [193]


def test_skill_documents_the_detection_command():
    """The orchestrator skill must keep the copy-pasteable scan commands."""
    text = SKILL.read_text(encoding="utf-8")
    assert "script/article-intake" in text
    assert "gh issue list --label article --state open" in text
    assert "gh pr list --state open" in text
    assert "ao session ls" in text
