"""Static / subprocess guard tests for script/check-images (issue #32).

These run without a browser and verify the CI image guard accepts the clean
tree and rejects fixtures for oversize files, bad names and oversize dimensions.

Budget literals live in script/image-budget.sh (single source of truth,
issue #171). The tests below pin the documented policy values and assert
script/check-images sources that file instead of redeclaring its own copies,
so the numbers cannot silently drift apart.
"""

import re
import struct
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "check-images"
BUDGET_FILE = REPO_ROOT / "script" / "image-budget.sh"

# Documented policy (#33): 500 KiB per file, 6 MiB total, 1600px long edge.
EXPECTED_BUDGET = {
    "MAX_FILE_BYTES": 500 * 1024,
    "MAX_TOTAL_BYTES": 6 * 1024 * 1024,
    "MAX_DIMENSION": 1600,
}


def _read_budget():
    values = {}
    for line in BUDGET_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(MAX_[A-Z_]+)=(\d+)\s*$", line.strip())
        if match:
            values[match.group(1)] = int(match.group(2))
    return values


def _run(assets_dir):
    return subprocess.run(
        [str(SCRIPT), str(assets_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _write_png_header(path, width, height):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", 0)
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", 0)
    path.write_bytes(sig + chunk + iend)


def test_image_budget_matches_documented_policy():
    assert BUDGET_FILE.is_file(), "script/image-budget.sh is missing"
    assert _read_budget() == EXPECTED_BUDGET


def test_check_images_uses_single_source_budget():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "image-budget.sh" in text, (
        "script/check-images must source script/image-budget.sh"
    )
    for name in EXPECTED_BUDGET:
        assert not re.search(rf"^{name}=", text, re.M), (
            f"script/check-images redeclares {name}; "
            "script/image-budget.sh is the single source of truth (#171)"
        )
    assert "MAX_IMAGE_DIMENSION" not in text, (
        "dead constant MAX_IMAGE_DIMENSION is back (removed in #171)"
    )
    assert "MAX_IMAGE_DIMENSION" not in BUDGET_FILE.read_text(encoding="utf-8")


def test_budget_enforced_at_single_source_values(tmp_path):
    budget = _read_budget()
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    # One byte over the single-sourced per-file cap must fail and name it.
    (img_dir / "just-over.jpg").write_bytes(b"0" * (budget["MAX_FILE_BYTES"] + 1))
    result = _run(img_dir)
    assert result.returncode != 0
    assert str(budget["MAX_FILE_BYTES"]) in result.stdout + result.stderr


def test_check_images_passes_on_clean_tree():
    result = _run(REPO_ROOT / "assets" / "img")
    assert result.returncode == 0, result.stdout + result.stderr


def test_good_image_passes_in_isolation(tmp_path):
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    _write_png_header(img_dir / "good-name.png", 100, 80)
    result = _run(img_dir)
    assert result.returncode == 0, result.stdout + result.stderr


def test_oversize_file_rejected(tmp_path):
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    (img_dir / "huge.jpg").write_bytes(b"0" * 520000)
    result = _run(img_dir)
    assert result.returncode != 0
    assert "MAX_FILE_BYTES" in result.stdout + result.stderr or "over" in (result.stdout + result.stderr).lower()


def test_bad_name_rejected(tmp_path):
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    _write_png_header(img_dir / "Bad Name.png", 100, 80)
    result = _run(img_dir)
    assert result.returncode != 0
    assert "BAD NAME" in (result.stdout + result.stderr)


def test_oversize_dimension_rejected(tmp_path):
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    _write_png_header(img_dir / "too-big.png", 2000, 100)
    result = _run(img_dir)
    assert result.returncode != 0
    assert "OVERSIZE DIMENSION" in (result.stdout + result.stderr)


def test_allowlist_has_no_stale_entries():
    # Every allowlist entry must still need grandfathering (#171): the file
    # exists and its name violates the lowercase-hyphen rule. Entries that
    # pass the rule (or point at removed files) must be dropped.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_image_details", str(REPO_ROOT / "script" / "check-image-details.py")
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)

    allow = helper.load_allowlist(
        str(REPO_ROOT / "script" / "check-images.allowlist")
    )
    stale = []
    for rel in sorted(allow):
        if not (REPO_ROOT / "assets" / "img" / rel).is_file():
            stale.append(f"{rel} (file gone)")
        elif helper.NAME_RE.match(Path(rel).name):
            stale.append(f"{rel} (name already compliant)")
    assert not stale, "stale allowlist entries:\n" + "\n".join(stale)