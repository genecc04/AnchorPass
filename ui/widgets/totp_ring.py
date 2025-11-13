from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QEvent, Property
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget
import time

class TotpRingWidget(QWidget):
    tick = Signal(int)
    rollover = Signal()

    def __init__(self, parent=None, period: int = 30):
        super().__init__(parent)
        self._period = max(1, int(period))
        self._remaining = self._period

        self._bg_color = QColor("#1f1f1f")
        self._fg_color = QColor("#075cb2")
        self._track_color = QColor("#343434")
        self._thickness = 4

        self.setMinimumSize(22, 22)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def getRingColor(self): return self._fg_color
    def setRingColor(self, c): 
        self._fg_color = QColor(c) if not isinstance(c, QColor) else c
        self.update()
    ringColor = Property(QColor, fget=getRingColor, fset=setRingColor)

    def getTrackColor(self): return self._track_color
    def setTrackColor(self, c): 
        self._track_color = QColor(c) if not isinstance(c, QColor) else c
        self.update()
    trackColor = Property(QColor, fget=getTrackColor, fset=setTrackColor)

    def getBgColor(self): return self._bg_color
    def setBgColor(self, c): 
        self._bg_color = QColor(c) if not isinstance(c, QColor) else c
        self.update()
    bgColor = Property(QColor, fget=getBgColor, fset=setBgColor)

    def getThickness(self): return self._thickness
    def setThickness(self, v):
        try:
            v = int(v)
        except Exception:
            return
        self._thickness = max(1, v)
        self.update()
    thickness = Property(int, fget=getThickness, fset=setThickness)

    def set_colors(self, track=None, ring=None, bg=None):
        if track is not None:
            self.setTrackColor(track)
        if ring is not None:
            self.setRingColor(ring)
        if bg is not None:
            self.setBgColor(bg)

    def set_period(self, period: int):
        p = max(1, int(period))
        if p != self._period:
            self._period = p
            self._remaining = min(self._remaining, self._period)
            self.update()

    def set_remaining(self, remaining: int, period: int | None = None):
        if period is not None:
            self.set_period(period)
        self._remaining = max(0, min(int(remaining), self._period))
        self.update()

    def start(self, interval_ms: int = 200):
        if not self._timer.isActive():
            self._timer.start(max(50, int(interval_ms)))
        self._on_tick()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def changeEvent(self, ev):
        if ev.type() in (QEvent.StyleChange, QEvent.PaletteChange):
            self.update()
        super().changeEvent(ev)

    def _on_tick(self):
        p = self._period
        if p <= 0:
            return
        now = int(time.time())
        new_remaining = p - 1 - (now % p)  # 29..0 UX
        if new_remaining == p - 1 and self._remaining != new_remaining:
            self.rollover.emit()
        self._remaining = new_remaining
        self.tick.emit(self._remaining)
        self.update()

    def paintEvent(self, _ev):
        w = min(self.width(), self.height())
        thickness = max(2, int(w * 0.14)) if w < 40 else self._thickness
        r = QRectF((self.width() - w) / 2 + 2, (self.height() - w) / 2 + 2, w - 4, w - 4)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_color)
        p.drawEllipse(r)

        pen = QPen(self._track_color, thickness)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(r, 90 * 16, -360 * 16)

        frac = (self._remaining / float(self._period)) if self._period > 0 else 0.0
        span = -int(360 * 16 * frac)  # clockwise
        pen.setColor(self._fg_color)
        p.setPen(pen)
        p.drawArc(r, 90 * 16, span)
        p.end()
