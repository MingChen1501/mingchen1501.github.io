"""Static guard for the content-only CI classification (issue #229).

Pins the contract of script/classify-content-only: content-only PRs
(posts, VI posts, content images, highlights list) classify as
content_only=true, while any code/config/test/unknown path -- or an
empty or uncertain file list -- forces the full suite. No silent skip.
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "classify-content-only"


def classify(files):
    proc = subprocess.run(
        [str(SCRIPT), *files],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def classify_stdin(payload):
    proc = subprocess.run(
        [str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def test_script_is_executable_shell():
    assert SCRIPT.exists()
    first_line = SCRIPT.read_text().splitlines()[0]
    assert first_line == "#!/bin/sh"


def test_content_only_posts_vi_images_highlights():
    assert classify([
        "_posts/2026-10-20-two-weeks-running-ai-agent-team-blog.md",
        "_vi_posts/hai-tuan-van-hanh-blog-cung-ai-agent-team.md",
        "assets/img/some-post/cover.jpg",
        "_data/highlights.yml",
    ]) == "content_only=true"


def test_stdin_form_matches_args_form():
    payload = "_posts/a.md\n_vi_posts/b.md\nassets/img/c.png\n"
    assert classify_stdin(payload) == "content_only=true"


def test_pr_228_shape_without_baselines_is_content_only():
    # #228 was a content-only article PR; its article files alone must
    # classify as content-only (the baseline binaries it also carried are
    # a code-path change and must force the full run -- see below).
    assert classify([
        "_posts/2026-10-20-two-weeks-running-ai-agent-team-blog.md",
        "_vi_posts/hai-tuan-van-hanh-blog-cung-ai-agent-team.md",
    ]) == "content_only=true"


@pytest.mark.parametrize("code_path", [
    "_layouts/post.html",
    "_includes/comments.html",
    "_sass/minima/custom-styles.scss",
    "assets/js/copy-code.js",
    "_config.yml",
    "_config_theme-dev.yml",
    "tests/e2e/test_comments.py",
    "script/cibuild",
    ".github/workflows/e2e.yml",
    "tests/e2e/visual/baseline/home-en@1280.jpg",
    "about.md",
    "Gemfile",
])
def test_code_or_unknown_path_forces_full_run(code_path):
    assert classify(["_posts/a.md", code_path]) == "content_only=false"


def test_empty_list_is_uncertain_and_runs_full():
    assert classify([]) == "content_only=false"
    assert classify_stdin("") == "content_only=false"
