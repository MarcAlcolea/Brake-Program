"""Application theming: a genuinely light theme and a genuinely dark theme.

Design goals: mostly white in light mode (almost no grey), near-black in dark mode, Helvetica Light
for body text with Helvetica Bold used sparingly for headings. The Fusion style makes the palette
apply consistently. A module flag records the current mode so widgets can pick readable accents.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


def _family_stack() -> list[str]:
    """A clean, light-weight sans-serif per platform.

    Windows has no Helvetica: asking for it there yields a low-resolution *bitmap* substitute
    (MS Sans Serif) that doesn't antialias or scale. So we ask for the native crisp font instead —
    Segoe UI, which also has a real Light weight — and only use Helvetica on macOS where it exists.
    """
    if sys.platform == "darwin":
        return ["Helvetica Neue", "Helvetica", "Arial"]
    if sys.platform.startswith("win"):
        return ["Segoe UI", "Arial"]
    return ["Nimbus Sans", "Arial", "DejaVu Sans"]  # Linux


_FAMILIES = _family_stack()
_SIZE = 13

_is_dark = False


def is_dark() -> bool:
    return _is_dark


def body_font() -> QFont:
    f = QFont()
    f.setFamilies(_FAMILIES)
    f.setPointSize(_SIZE)
    f.setWeight(QFont.Weight.Light)
    f.setStyleStrategy(QFont.PreferAntialias)  # never fall back to a bitmap font
    return f


def heading_font(size: int = _SIZE, bold: bool = True) -> QFont:
    f = QFont()
    f.setFamilies(_FAMILIES)
    f.setPointSize(size)
    f.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Light)
    f.setStyleStrategy(QFont.PreferAntialias)
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


def checkbox_qss() -> str:
    """Stylesheet for a visible checkbox indicator (theme-aware fill: darker on light, lighter on dark).

    Applied per-checkbox rather than app-wide: an *application* stylesheet makes macOS drop the custom
    Helvetica-Light application font on first paint (only a theme toggle re-applied it), so we keep the
    app stylesheet empty and touch only the individual checkboxes."""
    fill = "#b8b8b8" if _is_dark else "#4a4a4a"
    return (
        "QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #8a8a8a;"
        " border-radius: 3px; }"
        f"QCheckBox::indicator:checked {{ background: {fill}; border: 1px solid {fill}; }}"
    )


def style_checkboxes(root) -> None:
    """Give every checkbox under ``root`` the visible indicator style and keep its text Helvetica-Light.

    Setting a per-widget stylesheet can drop that widget's inherited font, so we re-assert the body
    font on each checkbox. Call after building the UI and again on each theme switch (for the fill)."""
    from PySide6.QtWidgets import QCheckBox

    qss = checkbox_qss()
    font = body_font()
    for cb in root.findChildren(QCheckBox):
        cb.setStyleSheet(qss)
        cb.setFont(font)


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
