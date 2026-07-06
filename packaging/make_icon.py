"""Regenerate the Brake Design Studio app icons (icon.icns for macOS, icon.ico for Windows).

The mark is a minimal monochrome brake rotor — a light ring with a drilled hole pattern on a
near-black rounded square — drawn with Qt so no extra imaging dependency is needed.

Run from the repo root (any platform):
    python packaging/make_icon.py
The .ico is always written; the .icns additionally needs macOS (uses the system `iconutil`).
Both generated icons are committed, so this only needs re-running if the design changes.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
BG = QColor("#141414")   # app dark background
FG = QColor("#f5f5f5")   # near-white ring


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)

    s = float(size)
    # Rounded-square plate (macOS-style, works fine on Windows too).
    plate = QPainterPath()
    margin, radius = s * 0.05, s * 0.22
    plate.addRoundedRect(QRectF(margin, margin, s - 2 * margin, s - 2 * margin), radius, radius)
    p.fillPath(plate, BG)

    # Brake rotor: annulus with a circle of drilled holes, punched out of the plate colour.
    cx = cy = s / 2
    outer, inner = s * 0.30, s * 0.13
    ring = QPainterPath()
    ring.addEllipse(QRectF(cx - outer, cy - outer, 2 * outer, 2 * outer))
    hub = QPainterPath()
    hub.addEllipse(QRectF(cx - inner, cy - inner, 2 * inner, 2 * inner))
    p.fillPath(ring.subtracted(hub), FG)

    p.setBrush(BG)
    p.setPen(Qt.NoPen)
    hole_r, orbit = s * 0.028, (outer + inner) / 2
    for k in range(8):
        a = math.tau * k / 8 + math.tau / 16
        hx, hy = cx + orbit * math.cos(a), cy + orbit * math.sin(a)
        p.drawEllipse(QRectF(hx - hole_r, hy - hole_r, 2 * hole_r, 2 * hole_r))

    # Hub bore.
    bore = s * 0.045
    p.drawEllipse(QRectF(cx - bore, cy - bore, 2 * bore, 2 * bore))
    p.end()
    return image


def png_bytes(size: int) -> bytes:
    from PySide6.QtCore import QBuffer, QIODevice

    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    draw(size).save(buf, "PNG")
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
