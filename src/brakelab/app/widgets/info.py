"""Click-to-open information affordance.

A small "ⓘ" button that shows its explanatory text in a popup when clicked (not on hover), used to
explain inputs, outputs and requirements.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QToolButton, QWidget


class InfoButton(QToolButton):
    """A compact "ⓘ" button that opens a message box with ``title`` and ``text`` on click."""

    def __init__(self, title: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText("ⓘ")
        self.setAutoRaise(True)
        self.setCursor(self.cursor())  # default arrow; makes clickability obvious enough
        self.setToolTip("Click for details")
        self._title = title
        self._text = text
        self.clicked.connect(self._show)

    def set_info(self, title: str, text: str) -> None:
        self._title, self._text = title, text

    def _show(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(self._title)
        box.setText(self._text)
        box.setIcon(QMessageBox.NoIcon)
        box.setStandardButtons(QMessageBox.Close)
        box.exec()


def show_info(parent: QWidget, title: str, text: str) -> None:
    """Show an information popup (used where a full button isn't convenient, e.g. table cells)."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.NoIcon)
    box.setStandardButtons(QMessageBox.Close)
    box.exec()
