# ui/widgets/rounded_menu.py

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QRegion, QPen, QPalette


class RoundedMenu(QMenu):
    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)

        self._radius = 8

        self.setWindowFlags(
            Qt.Popup |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setObjectName("RoundedMenu")
        self.setContentsMargins(4, 6, 4, 6)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Clip the *actual popup window* to a rounded shape
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(rect, self._radius, self._radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        pal = self.palette()
        bg_color = pal.color(QPalette.Window)       # from background-color
        border_color = pal.color(QPalette.WindowText)  # from color

        painter.fillPath(path, bg_color)

        pen = QPen(border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.setClipPath(path)
        super().paintEvent(event)
