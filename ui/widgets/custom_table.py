from PySide6.QtWidgets import ( QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGraphicsDropShadowEffect, QLabel )
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QFont, QDrag, QPainter, QPixmap, QPainterPath

from datetime import datetime

STATUS_ORDER = {"active": 0, "archived": 1, "expired": 2, "deleted": 3}

class SortableItem(QTableWidgetItem):
    def __init__(self, display_text, sort_key):
        super().__init__(display_text)
        self._sort_key = sort_key
    def __lt__(self, other):
        try:
            return self._sort_key < other._sort_key
        except Exception:
            return super().__lt__(other)

class ModernTable(QTableWidget):

    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self._hovered_row = -1
        self._status_col = -1
        self._setup_ui()

        self.setMouseTracking(True)

    def _setup_ui(self):
        self.setObjectName("ModernTable")

        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setCornerButtonEnabled(False)
        self.setFont(QFont("Inter", 11))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)

        header = self.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSectionsMovable(True)
        self.setSortingEnabled(True)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid() and self._hovered_row != -1:
            self._reset_row_color(self._hovered_row)
            self._hovered_row = -1
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hovered_row != -1:
            self._reset_row_color(self._hovered_row)
            self._hovered_row = -1
        super().leaveEvent(event)

    def _set_row_color(self, row, color):
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(QBrush(color))

    def _reset_row_color(self, row):
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(QBrush(Qt.NoBrush))

    def load_data(self, data, headers):
        header = self.horizontalHeader()
        prev_col   = header.sortIndicatorSection()
        prev_order = header.sortIndicatorOrder()

        self.setSortingEnabled(False)
        try:
            self.clearContents()
            self.setColumnCount(len(headers))
            self.setRowCount(len(data))
            self.setHorizontalHeaderLabels(headers)

            try:
                self._status_col = headers.index("Status")
            except ValueError:
                self._status_col = -1

            for r, row_data in enumerate(data):
                for c, value in enumerate(row_data):
                    item = self._make_sortable_item(value, c)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(r, c, item)
        finally:
            self.setSortingEnabled(True)
            if prev_col >= 0:
                self.sortItems(prev_col, prev_order)
            elif self.columnCount():
                self.sortItems(0, Qt.AscendingOrder)

    def _make_sortable_item(self, value, col_idx=None):
        if value is None:
            return SortableItem("", (1, ""))

        if col_idx is not None and col_idx == self._status_col and isinstance(value, str):
            v = value.strip().lower()
            if v in STATUS_ORDER:
                return SortableItem(value, (0, STATUS_ORDER[v]))

        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return SortableItem(value, (0, dt))
            except Exception:
                pass

        try:
            num = float(value)
            return SortableItem(str(value), (0, num))
        except Exception:
            pass

        return SortableItem(str(value), (0, str(value).lower()))

    def startDrag(self, supportedActions):
        model = self.model()
        if model is None:
            return

        indexes = self.selectedIndexes()
        if not indexes:
            return

        mime = model.mimeData(indexes)
        drag = QDrag(self)
        drag.setMimeData(mime)

        rows = sorted({idx.row() for idx in indexes})
        if not rows:
            return
        
        MAX_CHARS = 20 

        if len(rows) == 1:
            first_row = rows[0]
            site_index = model.index(first_row, 0)
            name = str(site_index.data(Qt.DisplayRole) or "").strip()

            if name:
                text = name
            else:
                text = "No Site/Title"
        else:
            count = len(rows)
            text = f"{count} items selected"

        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS - 3] + "..."

        chip = QLabel(text, self)
        chip.setObjectName("DragPreviewChip")
        chip.ensurePolished()
        chip.adjustSize()

        pm = chip.grab()

        radius = 6
        rounded = QPixmap(pm.size())
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, pm.width(), pm.height()), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pm)
        painter.end()

        drag.setPixmap(rounded)
        drag.setHotSpot(rounded.rect().center())
        drag.exec(supportedActions)