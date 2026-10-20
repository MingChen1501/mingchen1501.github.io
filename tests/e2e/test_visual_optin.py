"""Opt-in guard for the visual-regression pixel compares (#265).

The baselines are canonical on the CI runner, so the pixel compares fail on
clean local trees for environment reasons. `test_visual_baseline` therefore
skips locally unless explicitly enabled, while CI always runs it and the
static `test_baseline_budget` guard always runs everywhere. These static
(no Ruby, no browser) tests pin that contract.
"""

from __future__ import annotations

import pytest

import test_visual_regression as visual

pytestmark = pytest.mark.static


def test_pixel_compares_skipped_by_default(monkeypatch):
    """A clean local tree runs no pixel compares without any opt-in."""
    monkeypatch.delenv("E2E_VISUAL", raising=False)
    monkeypatch.delenv("UPDATE_BASELINES", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert not visual._visual_enabled()


@pytest.mark.parametrize("env", [{"E2E_VISUAL": "1"}, {"UPDATE_BASELINES": "1"}])
def test_explicit_flag_enables_pixel_compares(monkeypatch, env):
    """Local opt-in flags run the pixel compares."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert visual._visual_enabled()


@pytest.mark.parametrize("env", [{"CI": "true"}, {"GITHUB_ACTIONS": "true"}])
def test_ci_runs_pixel_compares_unconditionally(monkeypatch, env):
    """CI never needs the opt-in flag."""
    monkeypatch.delenv("E2E_VISUAL", raising=False)
    monkeypatch.delenv("UPDATE_BASELINES", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert visual._visual_enabled()


def test_skip_reason_names_opt_in():
    """The skip message tells the worker how to run the compares."""
    assert "E2E_VISUAL=1" in visual.VISUAL_SKIP_REASON


def test_baseline_budget_guard_stays_always_on():
    """File sizes are deterministic locally, so the budget guard never skips."""
    markers = {
        mark.name for mark in getattr(visual.test_baseline_budget, "pytestmark", [])
    }
    assert "static" in markers


def test_pixel_compares_are_not_static():
    """The pixel compares stay in the browser half, never in the static job."""
    markers = {
        mark.name for mark in getattr(visual.test_visual_baseline, "pytestmark", [])
    }
    assert "static" not in markers
