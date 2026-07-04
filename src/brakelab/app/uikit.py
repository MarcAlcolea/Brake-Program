"""Small UI helpers shared across panels: plain tables that size to their content.

Sizing tables to their content and turning off their own scrollbars means a page scrolls once,
rather than a scroll area inside another scroll area.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel, QTableWidget


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
