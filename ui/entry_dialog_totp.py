from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QIcon, QPalette, QFont, QFontDatabase, QPixmap, QPainter

from core import totp as totp_util
from core.settings_manager import SettingsManager
from ui.widgets.totp_ring import TotpRingWidget


def _icon_from_ligature(ligature: str, family: str, point_size: int = 18, 
                        padding: int = 2, color=None) -> QIcon:
    """Render a Material Symbols ligature into a QIcon (DPI-aware)."""
    side = point_size + padding * 2
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0

    pix = QPixmap(int(side * dpr), int(side * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.transparent)

    font = QFont(family, point_size)
    color = color or QApplication.palette().color(QPalette.ColorRole.ButtonText)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    p.setPen(color)
    p.setFont(font)
    from PySide6.QtCore import QRect
    p.drawText(QRect(0, 0, int(side), int(side)), Qt.AlignCenter, ligature)
    p.end()
    return QIcon(pix)

class TotpPreviewWidget(QWidget):
    
    def __init__(self, otp_field: QLineEdit, icon_family: str | None, parent=None):
        super().__init__(parent)
        self.otp_field = otp_field
        self._icon_family = icon_family
        self._have_icons_family = bool(
            self._icon_family and self._icon_family in QFontDatabase().families()
        )
        
        self._build_ui()
        self._start_timer()
        
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        
        self.ring = TotpRingWidget(self, period=30)
        self.preview = QLabel("—")
        self.preview.setToolTip("Current TOTP code · seconds remaining")
        
        self._copy_icon, self._check_icon = self._build_icons()
        
        self.copy_btn = QPushButton()
        self.copy_btn.setIcon(self._copy_icon)
        self.copy_btn.setToolTip("Copy current TOTP code")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setFixedSize(28, 24)
        self.copy_btn.setFocusPolicy(Qt.NoFocus)
        self.copy_btn.clicked.connect(self._copy_totp)
        
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)
        self._copy_timer.timeout.connect(self._reset_copy_icon)
        
        layout.addStretch(1)
        layout.addWidget(self.ring, 0, Qt.AlignVCenter)
        layout.addWidget(self.preview, 0, Qt.AlignVCenter)
        layout.addWidget(self.copy_btn, 0, Qt.AlignVCenter)
        
    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_preview)
        self._timer.start(1000)
        self.ring.start(200)
        self._update_preview()
        self.otp_field.textChanged.connect(self._update_preview)
        
    def _update_preview(self):
        secret_text = self.otp_field.text().strip()
        
        if not secret_text:
            self.preview.setText("—")
            self.ring.set_remaining(0, period=30)
            self._set_valid(True)
            self.copy_btn.setEnabled(False)
            self.copy_btn.setIcon(self._copy_icon)
            return
        
        code, rem, period = totp_util.totp_from_uri_or_secret(secret_text)
        if not code:
            self.preview.setText("invalid secret")
            self.ring.set_remaining(0, period=period or 30)
            self._set_valid(False)
            self.copy_btn.setEnabled(False)
            self.copy_btn.setIcon(self._copy_icon)
            return
        
        self.preview.setText(f"{code} · {rem:02d}s")
        self.ring.set_remaining(rem, period=period or 30)
        self._set_valid(True)
        self.copy_btn.setEnabled(True)
        
    def _build_icons(self) -> tuple[QIcon, QIcon]:
        if self._have_icons_family:
            fg = self.palette().color(QPalette.ButtonText)
            copy_ic = _icon_from_ligature("content_copy", self._icon_family, 18, 2, fg)
            check_ic = _icon_from_ligature("check", self._icon_family, 18, 2, fg)
        else:
            st = self.style()
            copy_ic = st.standardIcon(st.SP_DialogSaveButton)
            check_ic = st.standardIcon(st.SP_DialogApplyButton)
        return copy_ic, check_ic
        
    def _copy_totp(self):
        txt = self.preview.text().strip()
        code = txt.split("·")[0].strip() if "·" in txt else txt.strip()
        
        if not code or not code.isdigit():
            return
        
        cb = QApplication.clipboard()
        cb.setText(code)
        
        self.copy_btn.setIcon(self._check_icon)
        self.copy_btn.setEnabled(False)
        self._copy_timer.start(900)
        
        sm = self._get_settings()
        secs = int(sm.get("clipboard_clear_seconds", 15) or 0)
        if secs > 0:
            def clear_if_same():
                if cb.text() == code:
                    cb.clear()
            QTimer.singleShot(secs * 1000, clear_if_same)
            
    def _reset_copy_icon(self):
        self.copy_btn.setIcon(self._copy_icon)
        self.copy_btn.setEnabled(True)
        
    def _set_valid(self, valid: bool):
        if valid:
            self.otp_field.setStyleSheet("")
            self.preview.setStyleSheet("")
        else:
            self.otp_field.setStyleSheet("QLineEdit { border: 1px solid #cc3344; }")
            self.preview.setStyleSheet("QLabel { color: #cc3344; }")
            
    def cleanup(self):
        try:
            if self._timer.isActive():
                self._timer.stop()
            self.ring.stop()
        except Exception:
            pass
        
    def handle_theme_change(self, event):
        watched = {QEvent.PaletteChange, QEvent.ApplicationPaletteChange}
        THEME_CHANGE = getattr(QEvent, "ThemeChange", None)
        if THEME_CHANGE is not None:
            watched.add(THEME_CHANGE)
        
        if event.type() in watched:
            self._copy_icon, self._check_icon = self._build_icons()
            self.copy_btn.setIcon(self._copy_icon)

    def changeEvent(self, event):
        super().changeEvent(event)
        self.handle_theme_change(event)

    def _get_settings(self) -> SettingsManager:
        w = self
        while w is not None:
            if hasattr(w, "settings"):
                s = getattr(w, "settings")
                if isinstance(s, SettingsManager):
                    return s
            w = w.parent()
        return SettingsManager()