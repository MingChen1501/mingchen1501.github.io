"""Static / subprocess guard tests for script/check-images (issue #32).

These run without a browser and verify the CI image guard accepts the clean
tree and rejects fixtures for oversize files, bad names and oversize dimensions.
"""

import struct
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "script" / "check-images"


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


def test_existing_extension_filenames_allowed():
    # Clean tree includes 17 uppercase .JPG legacy files; guard must still pass.
    result = _run(REPO_ROOT / "assets" / "img")
    assert result.returncode == 0, result.stdout + result.stderr