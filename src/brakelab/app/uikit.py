"""Small UI helpers shared across panels: plain tables that size to their content.

Sizing tables to their content and turning off their own scrollbars means a page scrolls once,
rather than a scroll area inside another scroll area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
)


class _BoldCurrentDelegate(QStyledItemDelegate):
    """Draws the current item in bold and everything else normally, with no selection box.

    ``current`` returns the index that should be bold. Reads the live palette at paint time, so it
    stays correct when the theme changes.
    """

    def __init__(self, current, strip_hover: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._current = current
        self._strip_hover = strip_hover

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        if index.row() == self._current():
            option.font.setBold(True)

    def paint(self, painter, option, index) -> None:
        option.state &= ~QStyle.State_Selected
        if self._strip_hover:
            option.state &= ~QStyle.State_MouseOver
        super().paint(painter, option, index)


def style_combo(combo: QComboBox) -> QComboBox:
    """Show a combo's chosen option in bold in the popup instead of a grey highlight box."""
    combo.view().setItemDelegate(_BoldCurrentDelegate(combo.currentIndex, strip_hover=False, parent=combo))
    return combo


def style_nav(nav: QListWidget) -> QListWidget:
    """Bold the active sidebar item and drop the grey selection box."""
    nav.setItemDelegate(_BoldCurrentDelegate(nav.currentRow, strip_hover=True, parent=nav))
    return nav


def plain_table(headers: list[str], stretch_col: int = 0) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setShowGrid(False)
    t.setFrameShape(QTableWidget.NoFrame)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    header = t.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeToContents)
    header.setSectionResizeMode(stretch_col, QHeaderView.Stretch)
    header.setHighlightSections(False)
    return t


def fit_table(table: QTableWidget) -> None:
    """Fix a table's height to exactly fit its rows so it never shows its own scrollbar."""
    height = table.horizontalHeader().height() + 2 * table.frameWidth()
    for r in range(table.rowCount()):
        height += table.rowHeight(r)
    table.setFixedHeight(height + 2)


def muted(label: QLabel, color: str) -> QLabel:
    label.setStyleSheet(f"color: {color};")
    return label
