"""Static guard for the risk-low autonomous-merge rule (issue #433).

Owner direction (2026-10-24): below risk-medium, the team decides and
closes by itself. Anything rated risk-low is decided and merged by the
team with no owner involvement in the decision path — not even a
report-for-approval step. The normative wording lives in the risk-label
bullet of `AGENTS.md` and in the merge-policy/self-check sections of
the orchestrator skill.

These guards pin that contract:

- `AGENTS.md` and the orchestrator skill state that risk-low merges on
  green CI + one different-role APPROVE with no owner gate, and the
  orchestrator reports completion only (never asks);
- no risk-low line in either file reintroduces an owner-approval gate:
  any line mentioning `risk-low` alongside gate words (`owner
  approval`, `approval required`, `ask the owner`, ...) fails unless
  the same line negates it (`no` / `zero` / `never` / `not` /
  `without`);
- the risk-medium (merge, then inform via the normal report flow — no
  explicit approval) and risk-high/very-high/missing-label (explicit
  owner approval required) gates stay intact, so a future rewording of
  risk-low cannot weaken them by accident.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS = REPO_ROOT / "AGENTS.md"
ORCHESTRATOR_SKILL = (
    REPO_ROOT / ".opencode" / "skills" / "orchestrator" / "SKILL.md"
)

#: Gate phrases that must never apply to risk-low without a negation
#: on the same line.
GATE_PHRASES = (
    "owner approval",
    "approval required",
    "approval first",
    "ask the owner",
    "asks the owner",
    "ask for approval",
    "asks for approval",
    "report for approval",
)

#: Words that negate a gate phrase on the same line.
NEGATIONS = ("no ", "zero", "never", "not ", "without")


def _risk_low_gate_offenders(text, source):
    """Return risk-low lines that carry an unnegated owner-approval gate."""
    offenders = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower().replace("-", " ").replace("`", "")
        if "risk low" not in lowered:
            continue
        gated = [phrase for phrase in GATE_PHRASES if phrase in lowered]
        if gated and not any(neg in lowered for neg in NEGATIONS):
            offenders.append(f"{source}:{lineno}: {line.strip()}")
    return offenders


def test_agents_states_risk_low_no_owner_gate():
    """`AGENTS.md` must say risk-low merges without any owner gate."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "no owner gate" in text
    assert "never asks" in text
    assert "different-role" in text
    assert "explicit owner approval" in text


def test_orchestrator_skill_states_risk_low_no_owner_gate():
    """The orchestrator skill must say risk-low carries zero owner gates."""
    text = ORCHESTRATOR_SKILL.read_text(encoding="utf-8")
    assert "zero owner gates" in text
    assert "never asks" in text
    assert "different-role" in text
    assert "Merge self-check" in text


def test_medium_inform_only_and_high_needs_approval():
    """risk-medium informs; risk-high/very-high/missing label needs approval."""
    text = ORCHESTRATOR_SKILL.read_text(encoding="utf-8")
    assert "normal report flow" in text
    assert "no explicit" in text and "approval" in text
    assert "explicit owner approval required" in text


def test_no_risk_low_line_reintroduces_an_owner_gate():
    """No risk-low line may carry an unnegated owner-approval gate."""
    offenders = []
    offenders += _risk_low_gate_offenders(
        AGENTS.read_text(encoding="utf-8"), "AGENTS.md"
    )
    offenders += _risk_low_gate_offenders(
        ORCHESTRATOR_SKILL.read_text(encoding="utf-8"),
        ".opencode/skills/orchestrator/SKILL.md",
    )
    assert offenders == [], (
        "risk-low must merge with no owner gate (not even report-for-approval); "
        f"unnegated gate wording found: {offenders}"
    )
