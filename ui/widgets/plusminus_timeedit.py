from PySide6.QtWidgets import QTimeEdit, QAbstractSpinBox, QStyle, QStyleOptionSpinBox
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtCore import Qt, QRect
from ui import material_symbols as ms


class PlusMinusTimeEdit(QTimeEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

    def paintEvent(self, event):
        super().paintEvent(event)

        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        style = self.style()

        up_rect: QRect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxUp, self)
        dn_rect: QRect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, self)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        group = QPalette.Disabled if not self.isEnabled() else QPalette.Active
        fg = self.palette().color(group, QPalette.ButtonText)
        p.setPen(fg)
        p.setBrush(Qt.NoBrush)

        def px_for(rect: QRect) -> int:
            return max(10, min(rect.width(), rect.height()) - 6)

        f_up = ms.font(10);  f_up.setPixelSize(px_for(up_rect))
        f_dn = ms.font(10);  f_dn.setPixelSize(px_for(dn_rect))

        p.setFont(f_up)
        p.drawText(up_rect, Qt.AlignCenter | Qt.TextDontClip, "expand_less")

        p.setFont(f_dn)
        p.drawText(dn_rect, Qt.AlignCenter | Qt.TextDontClip, "expand_more")

        p.end()
