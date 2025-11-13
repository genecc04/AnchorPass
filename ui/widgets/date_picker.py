from typing import Optional

from PySide6.QtCore import Qt, QDate, QSize, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import ( QWidget, QLineEdit, QToolButton, QCalendarWidget, QHBoxLayout )

class _CalendarPopup(QCalendarWidget):
    datePicked = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.clicked.connect(self._pick_and_close)
        self.activated.connect(self._pick_and_close)

    def _pick_and_close(self, qdate: QDate):
        self.datePicked.emit(qdate)
        self.close()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class DatePicker(QWidget):
    """
    Parameters:
    icon_font : Optional[QFont]
    icon_px : int
    display_format : str
    initial_date : Optional[QDate]
    """
    dateChanged = Signal(QDate)

    def __init__( self, parent=None, display_format: str = "yyyy-MM-dd", 
        initial_date: Optional[QDate] = None, icon_font: Optional[QFont] = None, icon_px: int = 22, ):
        super().__init__(parent)

        self._display_format = display_format
        self._date = initial_date if (isinstance(initial_date, QDate) and initial_date.isValid()) else QDate()
        self._icon_font = icon_font
        self._icon_px = icon_px

        self._edit = QLineEdit(self)
        self._edit.setReadOnly(True)
        self._edit.setPlaceholderText("Select a date…")
        self._edit.setMinimumWidth(160)

        self._btn = QToolButton(self)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.NoFocus)
        self._btn.setAutoRaise(True)
        self._btn.setToolTip("Clear date")
        self._btn.setAccessibleName("Clear date")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._edit)
        layout.addWidget(self._btn)
        self.setLayout(layout)

        self._calendar = _CalendarPopup(self)
        self._calendar.hide()
        self._calendar.datePicked.connect(self._on_date_picked)

        self._sync_text()
        self._apply_icon("event_busy")

        self._btn.clicked.connect(self.clearDate)
        self._edit.mousePressEvent = self._wrap_edit_click(self._edit.mousePressEvent)
        self._edit.keyPressEvent  = self._wrap_edit_key(self._edit.keyPressEvent)

    def setDisplayFormat(self, fmt: str):
        self._display_format = fmt
        self._sync_text()

    def displayFormat(self) -> str:
        return self._display_format

    def setDate(self, date: Optional[QDate]):
        if date is None or not isinstance(date, QDate) or not date.isValid():
            self.clearDate()
            return
        if date != self._date:
            self._date = date
            self._sync_text()
            self.dateChanged.emit(self._date)

    def clearDate(self):
        self._date = QDate()
        self._sync_text()
        self.dateChanged.emit(self._date)

    def date(self) -> QDate:
        return self._date

    def hasDate(self) -> bool:
        return self._date.isValid()

    def setMinimumDate(self, date: QDate):
        self._calendar.setMinimumDate(date)

    def setMaximumDate(self, date: QDate):
        self._calendar.setMaximumDate(date)

    def setIconFont(self, font: Optional[QFont], icon_px: Optional[int] = None):
        self._icon_font = font
        if icon_px:
            self._icon_px = icon_px
        self._apply_icon("event_busy")

    def showCalendar(self):
        if self._date.isValid():
            self._calendar.setSelectedDate(self._date)
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        self._calendar.move(global_pos)
        self._calendar.show()
        self._calendar.setFocus()

    def _on_date_picked(self, qdate: QDate):
        self.setDate(qdate)

    def _sync_text(self):
        if self._date.isValid():
            self._edit.setText(self._date.toString(self._display_format))
        else:
            self._edit.clear()

    def _wrap_edit_click(self, original_handler):
        def handler(event):
            if event.button() == Qt.LeftButton:
                self.showCalendar()
            if original_handler:
                original_handler(event)
        return handler

    def _wrap_edit_key(self, original_handler):
        def handler(event):
            if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
                self.clearDate()
                return
            if original_handler:
                original_handler(event)
        return handler

    def _apply_icon(self, icon_name: str):
        if isinstance(self._icon_font, QFont):
            icon = self._icon_from_font(icon_name, self._icon_font, self._icon_px)
            self._btn.setIcon(icon)
            self._btn.setIconSize(QSize(self._icon_px, self._icon_px))
            self._btn.setText("")
            pad = max(6, self._icon_px // 4)
            self._btn.setFixedSize(self._icon_px + pad * 2, self._icon_px + pad * 2)
        else:
            self._btn.setIcon(QIcon())
            self._btn.setText("⌫")
            self._btn.setFixedWidth(34)

    def _icon_from_font(self, text: str, font: QFont, size_px: int) -> QIcon:
        f = QFont(font)
        f.setPixelSize(size_px)
        metrics = QFontMetrics(f)
        w = max(size_px, metrics.horizontalAdvance(text) + 6)
        h = max(size_px, metrics.height() + 6)

        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setFont(f)
        color = self.palette().color(QPalette.ButtonText)
        painter.setPen(color)
        painter.drawText(pm.rect(), Qt.AlignCenter, text)
        painter.end()

        return QIcon(pm)
