from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainterPath, QRegion


class RoundedMenu(QMenu):
    def __init__(self, *args, radius: float = 4.0, **kwargs):
        super().__init__(*args, **kwargs)
        self._radius = float(radius)

        flags = self.windowFlags()
        flags |= Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
