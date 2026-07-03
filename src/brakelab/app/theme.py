"""Application theming: a simple light theme and a matching dark theme, toggleable at runtime.

Both are plain and low-colour (white/near-black), Helvetica, using the Fusion style so the palette
applies consistently and independently of the system setting. A small module-level flag records the
current mode so panels can pick readable "increased / decreased" highlight colours.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Helvetica"
FONT_SIZE = 13

_is_dark = False


def is_dark() -> bool:
    return _is_dark


def _palette(window, text, base, button, highlight, placeholder) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, window)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, base)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, button)
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.Highlight, highlight)
    p.setColor(QPalette.HighlightedText, text)
    p.setColor(QPalette.ToolTipBase, base)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.PlaceholderText, placeholder)
    return p


def apply_theme(app: QApplication, dark: bool) -> None:
    global _is_dark
    _is_dark = dark
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE))
    if dark:
        app.setPalette(
            _palette(
                QColor("#2b2b2b"), QColor("#e6e6e6"), QColor("#232323"),
                QColor("#3a3a3a"), QColor("#4a4a4a"), QColor("#8a8a8a"),
            )
        )
    else:
        app.setPalette(
            _palette(
                QColor("#ffffff"), QColor("#1a1a1a"), QColor("#ffffff"),
                QColor("#f2f2f2"), QColor("#dcdcdc"), QColor("#9a9a9a"),
            )
        )


def apply_light_theme(app: QApplication) -> None:
    apply_theme(app, dark=False)


# Highlight colours for values that increased / decreased since the last recompute.
def increase_color() -> QColor:
    return QColor("#1e5e2f") if _is_dark else QColor("#d7f0d7")


def decrease_color() -> QColor:
    return QColor("#6e2020") if _is_dark else QColor("#f6d9d9")
