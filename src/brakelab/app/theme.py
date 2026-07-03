"""A single, simple light theme applied to the whole application.

Forces a plain light look (white background, black text, Helvetica) regardless of the system's
dark-mode setting, and keeps colour to a minimum. Using the Fusion style makes the palette apply
consistently.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Helvetica"
FONT_SIZE = 13

_WHITE = QColor("#ffffff")
_TEXT = QColor("#1a1a1a")
_BUTTON = QColor("#f2f2f2")
_LINE = QColor("#e6e6e6")
_SELECT = QColor("#dcdcdc")


def apply_light_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE))

    p = QPalette()
    p.setColor(QPalette.Window, _WHITE)
    p.setColor(QPalette.WindowText, _TEXT)
    p.setColor(QPalette.Base, _WHITE)
    p.setColor(QPalette.AlternateBase, _WHITE)
    p.setColor(QPalette.Text, _TEXT)
    p.setColor(QPalette.Button, _BUTTON)
    p.setColor(QPalette.ButtonText, _TEXT)
    p.setColor(QPalette.Highlight, _SELECT)
    p.setColor(QPalette.HighlightedText, _TEXT)
    p.setColor(QPalette.ToolTipBase, _WHITE)
    p.setColor(QPalette.ToolTipText, _TEXT)
    p.setColor(QPalette.PlaceholderText, QColor("#9a9a9a"))
    p.setColor(QPalette.Mid, _LINE)
    app.setPalette(p)
