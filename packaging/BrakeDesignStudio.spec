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
        "pyqtgraph",  # listed in old requirements, never actually imported
        # Unused Qt modules. The app only uses QtCore/QtGui/QtWidgets (verified by grep), so drop
        # the rest of Qt — this alone removes ~20-25 MB of frameworks/bindings from the bundle.
        "PySide6.QtQml",
        "PySide6.QtQmlModels",
        "PySide6.QtQmlMeta",
        "PySide6.QtQmlWorkerScript",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtVirtualKeyboard",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtSql",
        "PySide6.Qt3DCore",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtTest",
        "PySide6.QtSensors",
        "PySide6.QtPositioning",
        "PySide6.QtBluetooth",
    ],
    noarchive=False,
)

# --- Prune unused Qt libraries from what was actually collected --------------------------------
# The `excludes` above stop the unused PySide6 *Python bindings* from being imported, but
# PyInstaller's PySide6 hook still copies the whole Qt lib/plugins tree wholesale. So we drop the
# heavyweight Qt modules (and their plugins) from the collected TOCs here. The app only uses
# QtCore/QtGui/QtWidgets, so removing the rest is safe — this cuts ~20 MB from the bundle.
#
# Matching is by filename so it works for both macOS (QtQuick.framework, QtQuick.abi3.so) and
# Windows (Qt6Quick.dll, QtQuick.pyd). The suffixes (.framework/.abi3/.dll/.pyd) keep prefixes like
# "QtQml" from also matching the kept modules; none of the kept names appear in the drop list.
_DROP_QT_MODULES = [
    "QtQml", "QtQmlModels", "QtQmlMeta", "QtQmlWorkerScript",
    "QtQuick", "QtQuickWidgets", "QtQuick3D", "QtQuickControls2",
    "QtPdf", "QtPdfWidgets", "QtNetwork", "QtOpenGL", "QtOpenGLWidgets",
    "QtVirtualKeyboard", "QtWebEngineCore", "QtWebEngineWidgets", "QtWebChannel",
    "QtMultimedia", "QtMultimediaWidgets", "QtCharts", "QtDataVisualization",
    "QtSql", "Qt3DCore", "QtDesigner", "QtHelp", "QtTest",
    "QtSensors", "QtPositioning", "QtBluetooth",
]
# Whole plugin subfolders that only matter to the dropped modules (or to Linux, which we don't ship).
_DROP_PLUGIN_DIRS = [
    "plugins/tls", "plugins/networkinformation", "plugins/platforminputcontexts",
    "plugins/sqldrivers", "plugins/multimedia", "plugins/webview", "plugins/canbus",
    "plugins/position", "plugins/sensors", "plugins/renderplugins", "plugins/geometryloaders",
]

def _qt_fragments(mods):
    frags = []
    for mod in mods:
        short = mod[2:] if mod.startswith("Qt") else mod   # QtQuick -> Quick
        frags += [f"{mod}.framework", f"{mod}.abi3", f"{mod}.pyd", f"Qt6{short}.dll"]
    return frags

_DROP_FRAGMENTS = _qt_fragments(_DROP_QT_MODULES) + _DROP_PLUGIN_DIRS

def _keep(entry):
    dest = entry[0].replace("\\", "/")
    return not any(frag in dest for frag in _DROP_FRAGMENTS)

a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]

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
            "CFBundleShortVersionString": "1.7.0",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        },
    )
