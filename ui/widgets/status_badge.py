from typing import Optional, Union

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QPixmap, QFontMetrics


class StatusBadge(QWidget):

    BASELINE_NUDGE_PX = 2  

    STATUS_CONFIG = {
    "active": {
        "text": "Active",
        "icon": "check_circle",
        "bg_color": "rgba(16, 185, 129, 0.15)",
        "bg_color_selected": "#10b981",
        "text_color": "#059669",
        "text_color_selected": "#ffffff",
        "border_color": "#10b981",
    },
    "expiring": {
        "text": "Active",
        "icon": "warning",
        "bg_color": "rgba(245, 158, 11, 0.15)",
        "bg_color_selected": "#f59e0b",
        "text_color": "#b45309",
        "text_color_selected": "#ffffff",
        "border_color": "#f59e0b",
    },
    "expired": {
        "text": "Expired",
        "icon": "error",
        "bg_color": "rgba(239, 68, 68, 0.15)",
        "bg_color_selected": "#ef4444",
        "text_color": "#dc2626",
        "text_color_selected": "#ffffff",
        "border_color": "#ef4444",
    },
    "archived": {
        "text": "Archived",
        "icon": "inventory_2",
        "bg_color": "rgba(107, 114, 128, 0.15)",
        "bg_color_selected": "#6b7280",
        "text_color": "#4b5563",
        "text_color_selected": "#ffffff",
        "border_color": "#6b7280",
    },
    "deleted": {
        "text": "Deleted",
        "icon": "delete",
        "bg_color": "rgba(107, 114, 128, 0.15)",
        "bg_color_selected": "#6b7280",
        "text_color": "#4b5563",
        "text_color_selected": "#ffffff",
        "border_color": "#6b7280",
        },
    }

    def __init__(self, status: str, icon_family: Union[str, QFont, None] = None, parent=None):
        super().__init__(parent)
        self.status = (status or "active").lower()
        self.icon_family = icon_family
        self._is_selected = False

        self.config = self.STATUS_CONFIG.get(self.status, self.STATUS_CONFIG["active"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignVCenter)

        self.icon_label = QLabel()
        self.icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.icon_label.setAlignment(Qt.AlignVCenter)
        self.icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.text_label = QLabel(self.config["text"])
        text_font = QFont()
        text_font.setPixelSize(12)
        text_font.setWeight(QFont.Medium)
        self.text_label.setFont(text_font)
        self.text_label.setAlignment(Qt.AlignVCenter)
        self.text_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.icon_label.setContentsMargins(0, 0, 0, 0)
        self.text_label.setContentsMargins(2, 0, 0, 0)
        self.setFocusPolicy(Qt.NoFocus)
        self.icon_label.setFocusPolicy(Qt.NoFocus)
        self.text_label.setFocusPolicy(Qt.NoFocus)

        for lab in (self.icon_label, self.text_label):
            lab.setFrameShape(QFrame.NoFrame)
            lab.setTextInteractionFlags(Qt.NoTextInteraction)

        layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)
        layout.addWidget(self.text_label, 0, Qt.AlignVCenter)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("StatusBadge")

        self.setFixedHeight(24)
        self.setMaximumWidth(120)

        self._update_appearance()

    def set_selected(self, selected: bool):
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_appearance()

    def _update_appearance(self):
        if self._is_selected:
            bg_color = self.config["bg_color_selected"]
            text_color = self.config["text_color_selected"]
        else:
            bg_color = self.config["bg_color"]
            text_color = self.config["text_color"]

        self.setStyleSheet(
            f"""
            #StatusBadge {{
                background-color: {bg_color};
                border: 1px solid {self.config['border_color']};
                border-radius: 12px;
                max-height: 24px;
            }}
            """
        )

        nudge = self.BASELINE_NUDGE_PX
        label_css = (
            f"background: transparent; color: {text_color}; "
            f"border: none; outline: none; margin: 0;"
            f"padding-top: 0px; padding-bottom: {nudge}px; padding-left: 0px; padding-right: 0px;"
        )
        self.icon_label.setStyleSheet(label_css)
        self.text_label.setStyleSheet(label_css)

        fg = QColor(text_color)
        font = self._resolve_icon_font(self.icon_family)
        pm = self._render_symbol_pixmap(self.config["icon"], font, px=16, color=fg, inner_pad=0)
        if pm is not None:
            self.icon_label.setPixmap(pm)
        else:
            self.icon_label.setText("•")

    def _resolve_icon_font(self, icon_family: Union[str, QFont, None]) -> Optional[QFont]:
        if isinstance(icon_family, QFont):
            f = QFont(icon_family)
            f.setPixelSize(16)
            return f
        if isinstance(icon_family, str) and icon_family:
            f = QFont(icon_family)
            f.setPixelSize(16)
            return f
        return None

    def _render_symbol_pixmap(self, ligature: str, font: Optional[QFont], px: int,
                          color: QColor, inner_pad: int = 0) -> Optional[QPixmap]:
        if not font:
            return None
        f = QFont(font); f.setPixelSize(px)
        metrics = QFontMetrics(f)
        w = max(px, metrics.horizontalAdvance(ligature) + inner_pad * 2)
        h = max(px, metrics.height() + inner_pad * 2)

        pm = QPixmap(w, h); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setFont(f); p.setPen(color)
        p.drawText(pm.rect(), Qt.AlignCenter, ligature)
        p.end()
        return pm

class StatusBadgeTableWidget(QWidget):
    def __init__(self, status: str, icon_family: Union[str, QFont, None] = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.badge = StatusBadge(status, icon_family)
        layout.addWidget(self.badge, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet("background: transparent;")

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_selection)
        self._check_timer.start(100)

    def _check_selection(self):
        parent = self.parent()
        if not parent:
            return

        table = parent
        while table is not None and not hasattr(table, "rowCount"):
            table = table.parent()

        if table is None:
            return

        try:
            for row in range(table.rowCount()):
                for col in range(table.columnCount()):
                    if table.cellWidget(row, col) is self:
                        item0 = table.item(row, 0)
                        is_selected = bool(item0 and item0.isSelected())
                        self.badge.set_selected(is_selected)
                        return
        except Exception:
            pass