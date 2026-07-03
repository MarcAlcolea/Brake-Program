"""Make Qt find its platform plugins regardless of how the environment is set up.

Some PySide6 installs (notably under the macOS CommandLineTools Python) don't register the Qt
plugin directory, so Qt starts with an empty plugin search path and aborts with
"Could not find the Qt platform plugin 'cocoa'". We point Qt at the plugin folder that ships
inside the installed PySide6 package before any ``QApplication`` is created.

Importing this module runs the fix once; it is imported by ``brakelab.app`` at package import time,
which happens before the GUI is constructed.
"""

from __future__ import annotations

import os
from pathlib import Path


def ensure_qt_plugins() -> None:
    """Set the Qt plugin path from the installed PySide6 location if Qt can't find it itself."""
    try:
        import PySide6
    except ImportError:
        return

    plugins = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
    platforms = plugins / "platforms"
    if not platforms.is_dir():
        return

    # Only set these if unset or pointing somewhere that doesn't actually contain the plugins.
    current = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    if not current or not Path(current).is_dir():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
    if not os.environ.get("QT_PLUGIN_PATH"):
        os.environ["QT_PLUGIN_PATH"] = str(plugins)
