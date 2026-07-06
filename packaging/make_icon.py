"""Regenerate the Brake Design Studio app icons from the source artwork.

Source: ``packaging/icon_source.png`` (a rotor-and-caliper mark on a black rounded square). The
solid-black exterior is made transparent with a border flood-fill — so the rounded-square shape
floats as a proper macOS/Windows app icon — then resampled into every size the icon formats need.
Interior artwork is never touched: only pixels connected to the image border are cleared, so the
dark gaps inside the mark (which are the body colour, not pure black) stay opaque.

Run from the repo root (any platform):
    python packaging/make_icon.py
Writes icon.png (preview), src/brakelab/app/assets/icon.png (runtime window icon) and icon.ico
always; icon.icns additionally needs macOS (uses the system ``iconutil``). All generated icons are
committed, so this only needs re-running if ``icon_source.png`` changes.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "icon_source.png"
_BLACK_THRESHOLD = 14   # a pixel is "background black" if max(R,G,B) < this (body colour is ~19)


def _load_base() -> QImage:
    """Load the source and make its solid-black exterior transparent (border flood-fill)."""
    src = QImage(str(SOURCE))
    if src.isNull():
        raise SystemExit(f"missing or unreadable source icon: {SOURCE}")
    src = src.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = src.width(), src.height()

    arr = np.frombuffer(src.constBits(), np.uint8).reshape((h, w, 4)).copy()
    is_black = arr[:, :, :3].max(axis=2) < _BLACK_THRESHOLD

    # Flood-fill the near-black region from every border pixel; only the connected exterior clears,
    # so interior black outlines/gaps (if any) are preserved.
    exterior = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_black[y, x] and not exterior[y, x]:
                exterior[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if is_black[y, x] and not exterior[y, x]:
                exterior[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and is_black[ny, nx] and not exterior[ny, nx]:
                exterior[ny, nx] = True
                q.append((ny, nx))

    arr[exterior, 3] = 0
    out = QImage(arr.tobytes(), w, h, QImage.Format.Format_RGBA8888).copy()
    return out


_BASE: QImage | None = None


def _base() -> QImage:
    global _BASE
    if _BASE is None:
        _BASE = _load_base()
    return _BASE


def png_bytes(size: int) -> bytes:
    scaled = _base().scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    scaled.save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path: Path) -> None:
    """Pack PNG images into a .ico (PNG-in-ICO, supported since Windows Vista)."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    blobs = [png_bytes(sz) for sz in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    entries, offset = b"", len(header) + 16 * len(sizes)
    for sz, blob in zip(sizes, blobs):
        entries += struct.pack(
            "<BBBBHHII", sz % 256, sz % 256, 0, 0, 1, 32, len(blob), offset
        )
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(blobs))
    print(f"wrote {path}")


def write_icns(path: Path) -> None:
    if sys.platform != "darwin" or not shutil.which("iconutil"):
        print("skipping .icns (needs macOS iconutil)")
        return
    with tempfile.TemporaryDirectory() as td:
        iconset = Path(td) / "BrakeDesignStudio.iconset"
        iconset.mkdir()
        for sz in (16, 32, 128, 256, 512):
            (iconset / f"icon_{sz}x{sz}.png").write_bytes(png_bytes(sz))
            (iconset / f"icon_{sz}x{sz}@2x.png").write_bytes(png_bytes(sz * 2))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(path)], check=True)
    print(f"wrote {path}")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    (HERE / "icon.png").write_bytes(png_bytes(512))
    # Runtime window/taskbar icon, shipped inside the package (see app.main.run).
    (HERE.parent / "src" / "brakelab" / "app" / "assets" / "icon.png").write_bytes(png_bytes(256))
    write_ico(HERE / "icon.ico")
    write_icns(HERE / "icon.icns")
