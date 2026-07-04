"""A small info popover that appears next to whatever triggered it (not at the page bottom).

``show_popover`` opens a lightweight card at a screen position with a bold title and wrapped body.
It uses the Qt.Popup flag, so it closes automatically when the user clicks elsewhere. Only one is
shown at a time.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from .. import theme

_current: QFrame | None = None


def show_popover(global_pos: QPoint, title: str, text: str, anchor: QWidget | None = None) -> None:
    global _current
    if _current is not None:
        _current.close()
        _current = None

    frame = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
    frame.setAttribute(Qt.WA_DeleteOnClose)
    frame.setStyleSheet(
        f"QFrame {{ background: {theme.card_bg()}; border: 1px solid {theme.border_color()};"
        f" border-radius: 8px; }}"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    heading = QLabel(title)
    heading.setFont(theme.heading_font(12))
    heading.setWordWrap(True)
    body = QLabel(text)
    body.setFont(theme.body_font())
    body.setWordWrap(True)
    body.setStyleSheet(f"color: {theme.muted_text()};")
    layout.addWidget(heading)
    layout.addWidget(body)

    frame.setMaximumWidth(340)
    frame.adjustSize()

    # Keep the popover on-screen.
    screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
    area = screen.availableGeometry()
    x = min(global_pos.x(), area.right() - frame.width() - 8)
    y = global_pos.y() + 6
    if y + frame.height() > area.bottom():
        y = global_pos.y() - frame.height() - 6
    frame.move(max(area.left() + 8, x), max(area.top() + 8, y))
    frame.show()
    _current = frame
