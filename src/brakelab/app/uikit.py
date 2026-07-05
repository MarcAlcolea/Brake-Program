"""Small UI helpers shared across panels: plain tables that size to their content.

Sizing tables to their content and turning off their own scrollbars means a page scrolls once,
rather than a scroll area inside another scroll area.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPalette
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


class _WheelGuard(QObject):
    """Swallows wheel events on a combo box so scrolling the page never changes its value.

    A combo under the pointer would otherwise cycle its selection on scroll — surprising for a unit
    picker. We eat the wheel event so it neither changes the value nor is consumed here, letting the
    surrounding scroll area move instead.
    """

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() == QEvent.Wheel:
            event.ignore()
            return True
        return False


_wheel_guard = _WheelGuard()


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
    """Show a combo's chosen option in bold in the popup instead of a grey highlight box, and stop
    the mouse wheel from changing the selection (it should only change on a click)."""
    combo.view().setItemDelegate(_BoldCurrentDelegate(combo.currentIndex, strip_hover=False, parent=combo))
    combo.setFocusPolicy(Qt.StrongFocus)
    combo.installEventFilter(_wheel_guard)
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
    # No focus rectangle: clicking a cell must never draw a grey/box highlight — these are read-only
    # display tables, and the only interactive cell (the ⓘ) still emits cellClicked without focus.
    t.setFocusPolicy(Qt.NoFocus)
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
    """Grey a label's text via its palette, not a stylesheet.

    A colour stylesheet engages Qt's style-sheet machinery, which on macOS drops the widget's
    inherited Helvetica-Light font when the theme is re-applied (the text reverts to the system font
    on a dark/light toggle). Setting the palette colour avoids that entirely."""
    pal = label.palette()
    pal.setColor(QPalette.WindowText, QColor(color))
    label.setPalette(pal)
    return label
