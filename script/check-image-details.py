#!/usr/bin/env python3
"""Naming + dimension lint helper for script/check-images.

Pure standard-library (Pillow is optional if present). Emits diagnostics on
stdout/stderr and exits non-zero when any image violates the naming rule or
the long-edge dimension limit.

Usage:
    check-image-details.py --root DIR --max-dimension N --allowlist FILE
"""
import argparse
import os
import re
import struct
import subprocess
import sys

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.(jpg|jpeg|png|webp|gif)$")


def load_allowlist(path):
    entries = set()
    if not path or not os.path.isfile(path):
        return entries
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries.add(line.replace(os.sep, "/"))
    return entries


def parse_dimensions(path):
    """Return (width, height) or None if the format is not recognised."""
    # Optional Pillow fast path: available locally, maybe absent in CI.
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as im:
            return im.size
    except ImportError:
        pass
    except Exception:
        # Fall through to the stdlib parsers; Pillow may reject truncated
        # fixtures that still carry a readable header.
        pass

    try:
        with open(path, "rb") as fh:
            head = fh.read(64)
    except OSError:
        return None

    # PNG
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        try:
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        except struct.error:
            return None

    # GIF
    if head[:6] in (b"GIF87a", b"GIF89a"):
        try:
            w, h = struct.unpack("<HH", head[6:10])
            return w, h
        except struct.error:
            return None

    # JPEG
    if head[:2] == b"\xff\xd8":
        try:
            with open(path, "rb") as fh:
                fh.read(2)
                while True:
                    b = fh.read(1)
                    if not b:
                        return None
                    if b != b"\xff":
                        continue
                    # skip fill bytes
                    while True:
                        nb = fh.read(1)
                        if nb != b"\xff":
                            break
                        if not nb:
                            return None
                    if not nb:
                        return None
                    marker = nb[0]
                    if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                        continue
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6,
                                  0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE,
                                  0xCF):
                        # SOF: length(2) precision(1) height(2) width(2)
                        fh.read(2)  # length
                        fh.read(1)  # precision
                        hbytes = fh.read(2)
                        wbytes = fh.read(2)
                        if len(hbytes) < 2 or len(wbytes) < 2:
                            return None
                        h = int.from_bytes(hbytes, "big")
                        w = int.from_bytes(wbytes, "big")
                        return w, h
                    # skip segment
                    seg = fh.read(2)
                    if len(seg) < 2:
                        return None
                    seglen = int.from_bytes(seg, "big")
                    if seglen < 2:
                        return None
                    fh.seek(seglen - 2, 1)
        except OSError:
            return None

    # WebP
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        chunk = head[12:16]
        try:
            if chunk == b"VP8 ":
                with open(path, "rb") as fh:
                    data = fh.read(30)
                # frame header at offset 26
                if len(data) >= 30:
                    w = int.from_bytes(data[26:28], "little") & 0x3FFF
                    h = int.from_bytes(data[28:30], "little") & 0x3FFF
                    return w, h
            if chunk == b"VP8L":
                with open(path, "rb") as fh:
                    data = fh.read(25)
                if len(data) >= 25 and data[20] == 0x2F:
                    bits = int.from_bytes(data[21:25], "little")
                    w = (bits & 0x3FFF) + 1
                    h = ((bits >> 14) & 0x3FFF) + 1
                    return w, h
            if chunk == b"VP8X":
                with open(path, "rb") as fh:
                    data = fh.read(30)
                if len(data) >= 30:
                    w = int.from_bytes(data[24:27], "little") + 1
                    h = int.from_bytes(data[27:30], "little") + 1
                    return w, h
        except OSError:
            return None

    # Last resort: the `file` utility (available on most Linux runners).
    try:
        out = subprocess.run(
            ["file", path], capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r",\s*(\d+)\s*x\s*(\d+)\s*,", out)
    if not m:
        m = re.search(r"\b(\d+)\s*x\s*(\d+)\b", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--max-dimension", type=int, required=True)
    parser.add_argument("--allowlist", default="")
    args = parser.parse_args(argv)

    root = args.root
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 2

    allow = load_allowlist(args.allowlist)
    errors = []
    for dp, _, files in os.walk(root):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            path = os.path.join(dp, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            # Naming lint (new files only).
            if rel not in allow and not NAME_RE.match(name):
                errors.append(
                    f"BAD NAME: {rel} (expected lowercase-hyphen basename"
                    f" with lowercase extension)"
                )
            dims = parse_dimensions(path)
            if dims is None:
                errors.append(f"UNREADABLE IMAGE: {rel} (cannot determine dimensions)")
                continue
            w, h = dims
            long_edge = max(w, h)
            if long_edge > args.max_dimension:
                errors.append(
                    f"OVERSIZE DIMENSION: {rel} ({w}x{h}, long edge {long_edge}px"
                    f" > {args.max_dimension}px)"
                )

    if errors:
        print("Image naming/dimension check FAILED:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("OK: image names (new files) and dimensions within limits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())