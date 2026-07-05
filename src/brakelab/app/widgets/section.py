"""A collapsible section — a plain clickable header over its content, with no box.

The header is a clickable label (not a button), so there is never a grey background box. When the
section is expanded the header is bold Helvetica; when collapsed it is light. A small triangle marks
the state.
"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import theme
from .clickable import ClickableLabel


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._expanded = expanded
        self._content = content

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 6)
        layout.setSpacing(2)

        self._header = ClickableLabel()
        self._header.setMargin(2)
        self._header.clicked.connect(self._toggle)
        self._content.setVisible(expanded)
        self._render()

        layout.addWidget(self._header)
        layout.addWidget(self._content)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._render()

    def _render(self) -> None:
        arrow = "▾" if self._expanded else "▸"  # ▾ / ▸
        self._header.setText(f"{arrow}  {self._title}")
        self._header.setFont(theme.heading_font(13, bold=self._expanded))

    def set_expanded(self, expanded: bool) -> None:
        if expanded != self._expanded:
            self._toggle()
