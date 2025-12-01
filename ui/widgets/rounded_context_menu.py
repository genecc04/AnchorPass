from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QKeySequenceEdit
from ui.widgets.date_picker import DatePicker as BaseDatePicker
from PySide6.QtGui import QContextMenuEvent, QColor, QPalette, QIcon, QPainter, QPixmap
from PySide6.QtCore import Qt, QPoint
from ui.widgets.rounded_menu import RoundedMenu
from ui.widgets.plusminus_spinbox import PlusMinusSpinBox as BasePlusMinusSpinBox
from ui.widgets.plusminus_timeedit import PlusMinusTimeEdit as BasePlusMinusTimeEdit

def _is_dark_theme_for(widget) -> bool:
    base = widget.palette().color(QPalette.Base)
    brightness = (
        0.299 * base.red()
        + 0.587 * base.green()
        + 0.114 * base.blue()
    )
    return brightness < 128


def _tint_icon(icon: QIcon, color: QColor) -> QIcon:
    size = 16  # menu icon size
    base = icon.pixmap(size, size)
    if base.isNull():
        return icon

    tinted = QPixmap(base.size())
    tinted.fill(Qt.transparent)

    p = QPainter(tinted)
    p.drawPixmap(0, 0, base)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(tinted.rect(), color)
    p.end()

    new_icon = QIcon()
    new_icon.addPixmap(tinted, QIcon.Normal)
    new_icon.addPixmap(tinted, QIcon.Disabled)
    return new_icon


def _build_rounded_menu_with_tint(owner, default_menu):
    menu = RoundedMenu(owner)

    is_dark = _is_dark_theme_for(owner)

    for action in default_menu.actions():
        icon = action.icon()
        if not icon.isNull() and not is_dark:
            action.setIcon(_tint_icon(icon, QColor("#000000")))
        menu.addAction(action)

    return menu

class RoundedContextMenuMixin:
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        create_menu = getattr(self, "createStandardContextMenu", None)
        if not callable(create_menu):
            return super().contextMenuEvent(event)

        default_menu = create_menu()
        menu = _build_rounded_menu_with_tint(self, default_menu)

        menu.exec(event.globalPos())
        default_menu.deleteLater()


class LineEdit(RoundedContextMenuMixin, QLineEdit):
    pass


class PlainTextEdit(RoundedContextMenuMixin, QPlainTextEdit):
    pass

class DatePicker(RoundedContextMenuMixin, BaseDatePicker):
    pass


class KeySequenceEdit(QKeySequenceEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._line_edit = self.findChild(QLineEdit)
        if self._line_edit is not None:
            self._line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
            self._line_edit.customContextMenuRequested.connect(self._show_rounded_menu)

    def _show_rounded_menu(self, pos: QPoint) -> None:
        if self._line_edit is None:
            return

        default_menu = self._line_edit.createStandardContextMenu()
        menu = _build_rounded_menu_with_tint(self._line_edit, default_menu)

        global_pos = self._line_edit.mapToGlobal(pos)
        menu.exec(global_pos)
        default_menu.deleteLater()


class SpinBox(BasePlusMinusSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._line_edit = self.findChild(QLineEdit)
        if self._line_edit is not None:
            self._line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
            self._line_edit.customContextMenuRequested.connect(self._show_rounded_menu)

    def _show_rounded_menu(self, pos: QPoint) -> None:
        if self._line_edit is None:
            return

        default_menu = self._line_edit.createStandardContextMenu()
        menu = _build_rounded_menu_with_tint(self._line_edit, default_menu)

        global_pos = self._line_edit.mapToGlobal(pos)
        menu.exec(global_pos)
        default_menu.deleteLater()



class TimeEdit(BasePlusMinusTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._line_edit = self.findChild(QLineEdit)
        if self._line_edit is not None:
            self._line_edit.setContextMenuPolicy(Qt.CustomContextMenu)
            self._line_edit.customContextMenuRequested.connect(self._show_rounded_menu)

    def _show_rounded_menu(self, pos: QPoint) -> None:
        if self._line_edit is None:
            return

        default_menu = self._line_edit.createStandardContextMenu()
        menu = _build_rounded_menu_with_tint(self._line_edit, default_menu)

        global_pos = self._line_edit.mapToGlobal(pos)
        menu.exec(global_pos)
        default_menu.deleteLater()
