"""A lightweight collapsible section — a bold clickable header over its content, no box border.

Used instead of nested group boxes so pages stay flat and uncluttered: the only bold text is the
section header, and users can collapse parts they don't need.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from .. import theme


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 6)
        layout.setSpacing(2)

        self._button = QToolButton()
        self._button.setText(title)
        self._button.setCheckable(True)
        self._button.setChecked(expanded)
        self._button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self._button.setAutoRaise(True)
        self._button.setFont(theme.heading_font())
        self._button.setCursor(Qt.PointingHandCursor)
        self._button.toggled.connect(self._toggle)

        self._content = content
        self._content.setVisible(expanded)

        layout.addWidget(self._button)
        layout.addWidget(self._content)

    def _toggle(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def set_expanded(self, expanded: bool) -> None:
        self._button.setChecked(expanded)
