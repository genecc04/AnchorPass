from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QEvent
import time

from ui.mixins.auth_mixin import AuthMixin


class LockMixin:
    def lock(self):
        self.master = None
        self.cipher = None
        self.table.setRowCount(0)
        self.search.clear()
        QMessageBox.information(self, "Locked", "Vault locked.")
        self._login()
        self.reload()

    def change_master_password(self):
        return AuthMixin.change_master_password(self)

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.MouseButtonPress,
            QEvent.KeyPress,
            QEvent.MouseMove,
        ):
            self.last_activity = time.time()
        return super().eventFilter(obj, event)

    def _auto_lock_check(self):
        if not self.auto_lock_minutes:
            return
        idle_minutes = (time.time() - self.last_activity) / 60
        if idle_minutes >= self.auto_lock_minutes:
            self.lock()
            self.last_activity = time.time()

    def change_database(self):
        self._login()
        self.populate_tree()
        self.reload()

    def _update_title(self):
        if self.current_db:
            self.setWindowTitle(f"Secure Password Manager: {self.current_db}")
            self.status_label.setText(f"Active DB: {self.current_db}")
