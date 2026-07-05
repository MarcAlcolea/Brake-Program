"""Application theming: a genuinely light theme and a genuinely dark theme.

Design goals: mostly white in light mode (almost no grey), near-black in dark mode, Helvetica Light
for body text with Helvetica Bold used sparingly for headings. The Fusion style makes the palette
apply consistently. A module flag records the current mode so widgets can pick readable accents.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

_FAMILIES = ["Helvetica Neue", "Helvetica", "Arial"]
_SIZE = 13

_is_dark = False


def is_dark() -> bool:
    return _is_dark


def body_font() -> QFont:
    f = QFont()
    f.setFamilies(_FAMILIES)
    f.setPointSize(_SIZE)
    f.setWeight(QFont.Weight.Light)
    return f


def heading_font(size: int = _SIZE, bold: bool = True) -> QFont:
    f = QFont()
    f.setFamilies(_FAMILIES)
    f.setPointSize(size)
    f.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Light)
    return f


# ---- palette ---------------------------------------------------------------------------------
def apply_theme(app: QApplication, dark: bool) -> None:
    global _is_dark
    _is_dark = dark
    app.setStyle("Fusion")
    app.setFont(body_font())

    if dark:
        win = QColor("#141414")
        base = QColor("#161616")
        text = QColor("#ececec")
        button = QColor("#1f1f1f")
        highlight = QColor("#2c2c2c")
        placeholder = QColor("#7a7a7a")
    else:
        win = QColor("#ffffff")
        base = QColor("#ffffff")
        text = QColor("#1a1a1a")
        button = QColor("#ffffff")
        highlight = QColor("#e9eef7")
        placeholder = QColor("#a0a0a0")

    p = QPalette()
    for role in (QPalette.Window, QPalette.Base, QPalette.AlternateBase, QPalette.ToolTipBase, QPalette.Button):
        p.setColor(role, win if role in (QPalette.Window,) else base if role != QPalette.Button else button)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.Highlight, highlight)
    p.setColor(QPalette.HighlightedText, text)
    p.setColor(QPalette.PlaceholderText, placeholder)
    app.setPalette(p)

    # A single, app-wide checkbox style so every tick box is clearly visible (not white-on-white):
    # an empty bordered square when off, a filled square when on. Only the ``::indicator`` sub-control
    # is styled, so widget text still follows the palette. Re-applied on every theme switch, so the
    # fill tracks the mode — a darker grey on light, a lighter grey on dark.
    check_fill = "#b8b8b8" if dark else "#4a4a4a"
    app.setStyleSheet(
        "QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #8a8a8a;"
        " border-radius: 3px; }"
        f"QCheckBox::indicator:checked {{ background: {check_fill}; border: 1px solid {check_fill}; }}"
    )


# ---- accent helpers --------------------------------------------------------------------------
def card_bg() -> str:
    return "#1c1c1c" if _is_dark else "#ffffff"


def border_color() -> str:
    return "#333333" if _is_dark else "#e4e4e4"


def muted_text() -> str:
    return "#9a9a9a" if _is_dark else "#767676"


def increase_color() -> QColor:
    return QColor("#1e5330") if _is_dark else QColor("#e3f5e6")


def decrease_color() -> QColor:
    return QColor("#5c1f1f") if _is_dark else QColor("#fbe4e4")
