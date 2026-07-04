"""The "ⓘ" info affordance — clicking it opens a popover next to the icon."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

from .popover import show_popover


class InfoButton(QToolButton):
    """A compact "ⓘ" button that shows ``title``/``text`` in a popover anchored to itself."""

    def __init__(self, title: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText("ⓘ")
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Details")
        self._title = title
        self._text = text
        self.clicked.connect(self._open)

    def _open(self) -> None:
        pos = self.mapToGlobal(self.rect().bottomLeft())
        show_popover(pos, self._title, self._text, anchor=self)
