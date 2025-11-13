from PySide6.QtWidgets import QTreeWidget, QStyle, QFrame
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt


class StyledTreeWidget(QTreeWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setRootIsDecorated(True)
        self.setAttribute(Qt.WA_Hover, True)
        self.setIndentation(18)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)

    def drawRow(self, painter: QPainter, option, index):
        rect = option.rect
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, QColor(7, 92, 178))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(rect, QColor(7, 92, 178, int(0.15 * 255)))
        super().drawRow(painter, option, index)
