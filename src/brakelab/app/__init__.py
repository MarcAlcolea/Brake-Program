"""PySide6 desktop GUI.

Importing this package ensures Qt can locate its platform plugins (see _bootstrap) before any
QApplication is created, so the GUI launches reliably across environments.
"""

from ._bootstrap import ensure_qt_plugins

ensure_qt_plugins()
