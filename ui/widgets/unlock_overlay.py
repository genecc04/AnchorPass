from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QFormLayout, QLabel, QDialogButtonBox, QApplication, QPushButton
from PySide6.QtGui import QFont
import time

from core.settings_manager import SettingsManager
from ui.widgets.password_field import PasswordLineEdit
from ui.widgets.plusminus_spinbox import PlusMinusSpinBox 

class UnlockOverlay(QWidget):
    accepted = Signal(str, str, int)
    canceled = Signal()

    def __init__(self, parent=None, setup=False, icon_family=None, settings: SettingsManager | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setup = setup
        self.icon_family = icon_family

        if settings is not None:
            self.settings = settings
        else:
            w = parent
            while w is not None and not hasattr(w, "settings"):
                w = w.parent()
            if w is not None and hasattr(w, "settings"):
                self.settings = w.settings
            else:
                self.settings = SettingsManager()

        if parent:
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card_l = QFormLayout(card)
        card_l.setContentsMargins(30, 25, 30, 25)
        card_l.setVerticalSpacing(12)

        title = QLabel("Setup Master Password" if setup else "Unlock Vault")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        title.setFont(f)
        card_l.addRow("", title)

        if setup:
            self.p1 = PasswordLineEdit(placeholder="New master password",
                                       icon_family=self.icon_family,
                                       copy_enabled=False, strength_enabled=True, strength_alpha=0.12)
            self.p2 = PasswordLineEdit(placeholder="Confirm password",
                                       icon_family=self.icon_family,
                                       copy_enabled=False, strength_enabled=True, strength_alpha=0.12)
            card_l.addRow("Master password:", self.p1)
            card_l.addRow("Confirm password:", self.p2)
        else:
            self.p1 = PasswordLineEdit(placeholder="Master password",
                                       icon_family=self.icon_family,
                                       copy_enabled=False, strength_enabled=False, strength_alpha=0.0)
            self.p2 = PasswordLineEdit(placeholder="", icon_family=self.icon_family,
                                       copy_enabled=False, strength_enabled=False, strength_alpha=0.0)
            self.p2.hide()
            card_l.addRow("Master password:", self.p1)

        self.auto = PlusMinusSpinBox()
        self.auto.setRange(0, 120)
        self.auto.setValue(self.settings.get("auto_lock_minutes", 10))
        card_l.addRow("Auto-lock (minutes, 0 = off):", self.auto)

        hint = QLabel("The master password encrypts your entire vault. Keep it safe!")
        hint.setObjectName("hint")
        card_l.addRow("", hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self._on_cancel)
        card_l.addRow("", btns)

        root.addWidget(card)

    def eventFilter(self, obj, ev):
        t = ev.type()

        if obj is self.parent() and t in (QEvent.Resize, QEvent.Move, QEvent.Show):
            if self.parent() is not None:
                self.setGeometry(self.parent().rect())
            return False

        if t in (
            QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseMove, QEvent.Wheel,
            QEvent.KeyPress, QEvent.KeyRelease
        ):
            self.last_activity = time.time()
            return False

        return super().eventFilter(obj, ev)
    
    def showEvent(self, e):
        super().showEvent(e)
        if self.parent():
            self.setGeometry(self.parent().rect())

    def closeEvent(self, e):
        app = QApplication.instance()
        try:
            app.removeEventFilter(self)
        except Exception:
            pass
        if self.parent():
            try:
                self.parent().removeEventFilter(self)
            except Exception:
                pass
        super().closeEvent(e)

    def _on_accept(self):
        p1 = self.p1.text()
        p2 = self.p2.text() if self.setup else ""
        minutes = int(self.auto.value())
        self.accepted.emit(p1, p2, minutes)

    def _on_cancel(self):
        self.canceled.emit()