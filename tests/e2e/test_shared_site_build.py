"""Static guard for the shared site build (issue #320).

Pins the CI contract: one `bundle exec jekyll build` serves the browser
matrix and both LHCI jobs from a single `site` artifact, classified by one
shared composite action -- instead of one build per workflow. Also pins
that ci.yaml keeps both Jekyll legs (the shared build does not replace
the theme-dev matrix).
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "e2e.yml"
CLASSIFY_ACTION = REPO_ROOT / ".github" / "actions" / "classify-content-only" / "action.yml"
CI_WORKFLOW = WORKFLOWS / "ci.yaml"
BUILD_RUN = "bundle exec jekyll build"
SHARED_ARTIFACT = "site"


def load(path):
    return yaml.safe_load(path.read_text())


def job_steps(job):
    return job.get("steps", []) or []


def run_commands(job):
    return [s.get("run", "") for s in job_steps(job) if "run" in s]


def test_lighthouse_workflow_is_merged():
    assert not (WORKFLOWS / "lighthouse.yml").exists()


def test_single_build_job_builds_once():
    jobs = load(WORKFLOW)["jobs"]
    builders = [
        name for name, job in jobs.items()
        if any(BUILD_RUN in run for run in run_commands(job))
    ]
    assert builders == ["build-site"]


def test_single_shared_artifact_for_all_heavy_jobs():
    jobs = load(WORKFLOW)["jobs"]
    uploads = [
        (name, s["with"]["name"])
        for name, job in jobs.items()
        for s in job_steps(job)
        if s.get("uses", "").startswith("actions/upload-artifact")
        and str(s.get("with", {}).get("path", "")).startswith("_site")
    ]
    assert uploads == [("build-site", SHARED_ARTIFACT)]
    for consumer in ("browser-e2e", "lighthouse-desktop", "lighthouse-mobile"):
        downloads = [
            s["with"]["name"]
            for s in job_steps(jobs[consumer])
            if s.get("uses", "").startswith("actions/download-artifact")
        ]
        assert downloads == [SHARED_ARTIFACT], consumer


def test_single_shared_classify_step():
    action = load(CLASSIFY_ACTION)
    assert action["outputs"]["content_only"]
    jobs = load(WORKFLOW)["jobs"]
    users = [
        name for name, job in jobs.items()
        for s in job_steps(job)
        if str(s.get("uses", "")).endswith("/classify-content-only")
    ]
    assert users == ["classify"]
    # No job inlines the classify script anymore; the action owns it.
    inlined = [
        name for name, job in jobs.items()
        if any("classify-content-only" in run for run in run_commands(job))
    ]
    assert inlined == []


def test_ci_jekyll_matrix_kept():
    matrix = load(CI_WORKFLOW)["jobs"]["build"]["strategy"]["matrix"]
    assert matrix["jekyll"] == ["~> 3.9", "~> 4.2"]


def test_aggregator_display_names_pinned():
    # Branch protection matches these display names; a rename would
    # silently unsatisfy the required checks, so pin them verbatim.
    jobs = load(WORKFLOW)["jobs"]
    assert jobs["e2e-summary"]["name"] == "E2E suite result"
    assert jobs["lighthouse-summary"]["name"] == "Lighthouse suite result"
