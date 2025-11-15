from typing import Optional
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import ( QFont, QPixmap, QPainter, QIcon, QColor, QGuiApplication, QPalette )
from PySide6.QtCore import Qt, QSize, QCoreApplication, QEvent

def _material_symbols_font(point_size: int) -> QFont:
    app = QCoreApplication.instance()
    family = app.property("MaterialSymbols.family") if app else None
    family = family or "Material Symbols Rounded"
    f = QFont(family)
    f.setPointSize(point_size)
    return f

def _glyph_to_icon(glyph: str, size: int, color: QColor, y_offset: int = 0) -> QIcon:
    px_side = int(size * 1.8)
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0

    pm = QPixmap(int(px_side * dpr), int(px_side * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setFont(_material_symbols_font(size))
    p.setPen(color)

    rect = pm.rect()
    if y_offset != 0:
        rect = rect.adjusted(0, y_offset, 0, y_offset)

    p.drawText(rect, Qt.AlignCenter, glyph)
    p.end()
    return QIcon(pm)

class FontIconButton(QPushButton):
    """
    Parameters:
      - hover_enabled / border_enabled
      - radius, min button side
      - checkable + optional checked_glyph
      - focus ring toggle
      - badge overlay (optional)
      - THEME ICON COLOR (follows palette ButtonText / Disabled)
    """
    def __init__( self, glyph: str, *, size: int = 20, color: Optional[str] = None, tooltip: Optional[str] = None,
        object_name: Optional[str] = None, hover_enabled: bool = True, border_enabled: bool = False, focus_ring: bool = True,
        flat: bool = True, min_button_side: Optional[int] = None, checkable: bool = False, checked_glyph: Optional[str] = None,
        badge_count: Optional[int] = None, parent=None, ):

        super().__init__(parent)
        if object_name:
            self.setObjectName(object_name)
        self._glyph = glyph
        self._icon_size = int(size)
        self._icon_color = QColor(color) if color else None
        self._hover_enabled = bool(hover_enabled)
        self._border_enabled = bool(border_enabled)
        self._focus_ring = bool(focus_ring)
        self._radius = 0
        self._checked_glyph = checked_glyph
        self._badge_count = badge_count

        if tooltip:
            self.setToolTip(tooltip)

        self.setFlat(bool(flat))
        self.setCheckable(bool(checkable))
        self.toggled.connect(lambda _c: self._apply_icon())

        self.setFocusPolicy(Qt.StrongFocus)

        side = min_button_side or int(size * 2.2)
        self.setMinimumSize(QSize(side, side))
        self.setIconSize(QSize(int(size * 1.6), int(size * 1.6)))
        self.setText("")
        self.setAccessibleName(tooltip or glyph)

        self._apply_style()
        self._apply_icon()

    def _apply_style(self):
        base = f"""
            QPushButton {{
                border-radius: {self._radius}px;
                background: transparent;
                {'border: 1px solid rgba(0,0,0,0.20);' if self._border_enabled else 'border: none;'}
            }}
        """
        hover = "QPushButton:hover { background: rgba(0,0,0,0.06); }" if self._hover_enabled else ""
        pressed = "QPushButton:pressed { background: rgba(0,0,0,0.10); }"
        focus = (
            "QPushButton:focus { outline: none; border: 1px solid rgba(59,130,246,0.8); }"
            if self._focus_ring else ""
        )
        self.setStyleSheet("\n".join([base, hover, pressed, focus]))

    def _current_glyph(self) -> str:
        if self.isCheckable() and self.isChecked() and self._checked_glyph:
            return self._checked_glyph
        return self._glyph

    def _theme_icon_color(self) -> QColor:
        if self._icon_color is not None:
            return self._icon_color
        pal = self.palette()
        group = QPalette.Disabled if not self.isEnabled() else QPalette.Active
        return pal.color(group, QPalette.ButtonText)

    def _apply_icon(self):
        self.setIcon(_glyph_to_icon(self._current_glyph(), self._icon_size, self._theme_icon_color()))

    def changeEvent(self, e):
        et = e.type()
        if et in (QEvent.EnabledChange, QEvent.PaletteChange, QEvent.StyleChange):
            self._apply_icon()
        super().changeEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._badge_count is not None and self._badge_count >= 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            r = 9; m = 4
            rect = self.rect()
            cx = rect.right() - m - r
            cy = rect.top() + m + r
            pal = self.palette()
            bubble = pal.color(QPalette.Highlight)
            textc = pal.color(QPalette.BrightText)
            p.setBrush(bubble)
            p.setPen(Qt.NoPen)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            p.setPen(textc)
            p.setFont(self.font())
            p.drawText(cx - r, cy - r, r * 2, r * 2, Qt.AlignCenter, str(self._badge_count))
            p.end()

    def setGlyph(self, glyph: str):
        self._glyph = glyph
        self._apply_icon()

    def setCheckedGlyph(self, glyph: Optional[str]):
        self._checked_glyph = glyph
        self._apply_icon()

    def setIconPointSize(self, size: int):
        self._icon_size = int(size)
        self._apply_icon()

    def setIconColor(self, color: Optional[str]):
        self._icon_color = QColor(color) if color else None
        self._apply_icon()

    def setHoverEnabled(self, enabled: bool):
        self._hover_enabled = bool(enabled)
        self._apply_style()

    def setBorderEnabled(self, enabled: bool):
        self._border_enabled = bool(enabled)
        self._apply_style()

    def setMinimumButtonSide(self, side: int) -> None:
        self.setMinimumSize(QSize(max(0, int(side)), max(0, int(side))))

    def setRadius(self, radius: int):
        self._radius = max(0, int(radius))
        self._apply_style()

    def setFocusRingEnabled(self, enabled: bool):
        self._focus_ring = bool(enabled)
        self._apply_style()

    def setBadgeCount(self, count: Optional[int]) -> None:
        self._badge_count = count
        self.update()
