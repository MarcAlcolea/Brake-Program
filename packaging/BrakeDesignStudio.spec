# PyInstaller spec for the standalone Brake Design Studio app (Windows .exe folder / macOS .app).
#
# Build from the repo root:
#     pyinstaller --noconfirm packaging/BrakeDesignStudio.spec
# Output lands in dist/: `Brake Design Studio/Brake Design Studio.exe` on Windows,
# `Brake Design Studio.app` on macOS.
# CI (.github/workflows/build.yml) runs exactly this on both platforms for every release.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent          # repo root (spec lives in packaging/)
SRC = str(ROOT / "src")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[SRC],
    binaries=[],
    datas=[
        # Runtime window/taskbar icon (app.main reads it relative to the module).
        (str(ROOT / "src" / "brakelab" / "app" / "assets"), "brakelab/app/assets"),
    ],
    hiddenimports=[
        # The Qt canvas is imported inside GUI modules; make sure the hook machinery sees it.
        "matplotlib.backends.backend_qtagg",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Dev/test-only and unused heavyweight packages — keeps the download small.
        "tkinter",
        "PyQt5",
        "PyQt6",
        "IPython",
        "pytest",
        "openpyxl",
        "docx",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

icon = str(ROOT / "packaging" / ("icon.icns" if sys.platform == "darwin" else "icon.ico"))

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Brake Design Studio",
    debug=False,
    strip=False,
    upx=False,
    console=False,           # windowed app: no terminal window
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Brake Design Studio",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Brake Design Studio.app",
        icon=icon,
        bundle_identifier="eu.alcolea.brakedesignstudio",
        info_plist={
            "CFBundleName": "Brake Design Studio",
            "CFBundleDisplayName": "Brake Design Studio",
            "CFBundleShortVersionString": "1.1.1",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        },
    )
