from PySide6.QtWidgets import QLineEdit
from PySide6.QtGui import QContextMenuEvent, QPalette, QIcon, QPixmap, QPainter, QColor
from ui.widgets.rounded_menu import RoundedMenu
from PySide6.QtCore import Qt


class SearchLineEdit(QLineEdit):
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        default_menu = self.createStandardContextMenu()

        menu = RoundedMenu(self)

        is_dark = self._is_dark_theme()

        for action in default_menu.actions():
            icon = action.icon()
            if not icon.isNull() and not is_dark:
                action.setIcon(self._tint_icon(icon, QColor("#3b2a21")))
            menu.addAction(action)

        menu.exec(event.globalPos())
        default_menu.deleteLater()

    def _is_dark_theme(self) -> bool:
        base = self.palette().color(QPalette.Base)
        brightness = 0.299 * base.red() + 0.587 * base.green() + 0.114 * base.blue()
        return brightness < 128

    def _tint_icon(self, icon: QIcon, color: QColor) -> QIcon:
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