"""Static guards for #195: CI/E2E support for external attachment images.

Article images are embedded by direct GitHub issue-attachment URL
(`https://github.com/user-attachments/assets/...`) as a temporary workaround
until a dedicated store (Cloudflare R2, Amazon S3, or equivalent) is approved.
`script/check-external-images` validates them fully offline against the single
central config `_data/image_hosts.yml` — no test below fetches a live
attachment, so the suite stays network-independent.

Guarded here:

- the host config exists, pins the attachment hosts, and is the file the
  guard script reads (repointing the config repoints the guard);
- the guard script performs no network I/O (no socket/urllib/requests);
- a valid fixture (allowlisted https URL, alt text, dimensions) passes;
- `http://` URLs, empty alt text, missing dimensions, and unlisted hosts
  each fail with a clear message;
- the real `_posts/` / `_vi_posts/` tree passes (offline);
- `script/check-images` still owns only the local `assets/img/` budgets.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "check-external-images"
CONFIG = REPO_ROOT / "_data" / "image_hosts.yml"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "external-images"


def _run(root, config=CONFIG):
    return subprocess.run(
        ["python3", str(SCRIPT), "--root", str(root), "--config", str(config)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _tree_with(*fixture_names, tmp_path):
    root = tmp_path / "site"
    posts = root / "_posts"
    posts.mkdir(parents=True)
    for name in fixture_names:
        shutil.copy(str(FIXTURES / name), str(posts / name))
    (root / "_vi_posts").mkdir()
    return root


def test_image_host_config_is_the_single_source_of_truth():
    assert CONFIG.is_file(), "_data/image_hosts.yml is missing (#195)"
    text = CONFIG.read_text(encoding="utf-8")
    assert "github.com" in text
    assert "/user-attachments/assets/" in text
    script = SCRIPT.read_text(encoding="utf-8")
    assert "image_hosts.yml" in script, (
        "script/check-external-images must read _data/image_hosts.yml"
    )
    assert "_data" in script


def test_guard_script_performs_no_network_io():
    """The guard never fetches a URL: `urlparse` is pure string parsing."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "import socket" not in text
    assert "urllib.request" not in text
    assert "http.client" not in text
    assert "requests" not in text
    assert "urlopen" not in text
    assert "urlretrieve" not in text


def test_valid_fixture_passes(tmp_path):
    root = _tree_with("valid.md", tmp_path=tmp_path)
    result = _run(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 external image(s)" in result.stdout


def test_insecure_scheme_fails_with_clear_message(tmp_path):
    root = _tree_with("insecure-scheme.md", tmp_path=tmp_path)
    result = _run(root)
    assert result.returncode != 0
    assert "INSECURE SCHEME" in result.stdout + result.stderr


def test_empty_alt_fails_with_clear_message(tmp_path):
    root = _tree_with("empty-alt.md", tmp_path=tmp_path)
    result = _run(root)
    assert result.returncode != 0
    assert "EMPTY ALT TEXT" in result.stdout + result.stderr


def test_missing_dimensions_fail_with_clear_message(tmp_path):
    root = _tree_with("missing-dims.md", tmp_path=tmp_path)
    result = _run(root)
    assert result.returncode != 0
    assert "MISSING DIMENSIONS" in result.stdout + result.stderr


def test_unlisted_host_fails_with_clear_message(tmp_path):
    root = _tree_with("unlisted-host.md", tmp_path=tmp_path)
    result = _run(root)
    assert result.returncode != 0
    assert "HOST NOT ALLOWLISTED" in result.stdout + result.stderr


def test_repointing_the_config_repoints_the_guard(tmp_path):
    """The allowlist lives in exactly one file: a config change moves the guard."""
    config = tmp_path / "hosts.yml"
    config.write_text(
        "scheme: https\n"
        "allowed_hosts:\n"
        "  - cdn.example.com\n"
        "attachment_path_prefixes:\n"
        "  - /photos/\n",
        encoding="utf-8",
    )
    root = _tree_with("unlisted-host.md", "valid.md", tmp_path=tmp_path)
    result = _run(root, config=config)
    assert result.returncode != 0
    # The cdn.example.com fixture image is now accepted; the github.com ones fail.
    output = result.stdout + result.stderr
    assert "github.com/user-attachments/assets/1111111111" in output
    assert "cdn.example.com/photos/fedora.jpg" not in output


def test_real_post_tree_passes_offline():
    result = _run(REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_images_still_owns_only_the_local_budgets():
    text = (REPO_ROOT / "script" / "check-images").read_text(encoding="utf-8")
    assert "check-external-images" in text, (
        "script/check-images must point external images at "
        "script/check-external-images (#195)"
    )
    result = subprocess.run(
        [str(REPO_ROOT / "script" / "check-images")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Image check passed." in result.stdout
