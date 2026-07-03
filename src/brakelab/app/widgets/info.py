"""Click-to-open information affordance and the in-window details area.

Clicking an "ⓘ" does not open an external dialog; it routes the text to a :class:`DetailsPanel`
docked inside the main window, so the explanation feels part of the program. Info text is passed
around as ``(title, body)`` and displayed by an ``InfoSink`` callable.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QGroupBox, QLabel, QTextEdit, QToolButton, QVBoxLayout, QWidget

#: A callable that displays an information entry: ``sink(title, body)``.
InfoSink = Callable[[str, str], None]


class InfoButton(QToolButton):
    """A compact "ⓘ" button that sends its text to an :data:`InfoSink` on click."""

    def __init__(self, title: str, text: str, sink: InfoSink, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText("ⓘ")
        self.setAutoRaise(True)
        self.setToolTip("Click for details")
        self.clicked.connect(lambda: sink(title, text))


class DetailsPanel(QGroupBox):
    """An in-window panel that shows the explanation for the last-clicked item."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Details", parent)
        layout = QVBoxLayout(self)
        self._title = QLabel("Click any ⓘ to see the note and formula here.")
        f = self._title.font()
        f.setBold(True)
        self._title.setFont(f)
        self._title.setWordWrap(True)
        self._body = QTextEdit()
        self._body.setReadOnly(True)
        self._body.setFrameStyle(0)
        layout.addWidget(self._title)
        layout.addWidget(self._body)
        self.setMaximumHeight(150)

    def show_details(self, title: str, body: str) -> None:
        self._title.setText(title)
        self._body.setPlainText(body)
