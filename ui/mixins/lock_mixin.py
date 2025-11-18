from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QEvent
import time
from pathlib import Path
from ui.mixins.auth_mixin import AuthMixin
from core import settings_manager
from core import db


class LockMixin:
    def lock(self, show_toast: bool = True) -> None:
        self.master = None
        self.cipher = None
        self._set_menu_locked_state(True)
        self.show_lock_overlay(True)
        self._update_tray_icon_locked_state(True)
        try:
            if hasattr(self, "table"):
                self.table.blockSignals(True)
                self.table.clearSelection()
                self.table.setRowCount(0)
        finally:
            if hasattr(self, "table"):
                self.table.blockSignals(False)

        if hasattr(self, "search"):
            self.search.clear()

        try:
            if hasattr(self, "_preview_panel"):
                self._preview_panel.update_plain(None)
                self._preview_panel.stop()
        except Exception:
            pass

        if hasattr(self, "_update_actions_for_selection"):
            self._update_actions_for_selection()

        if hasattr(self, "show_lock_overlay"):
            try:
                self.show_lock_overlay(True)
            except Exception:
                pass

        try:
            if show_toast and hasattr(self, "statusBar"):
                self.statusBar().showMessage("Vault locked.", 2000)
        except Exception:
            pass


    def change_master_password(self):
        return AuthMixin.change_master_password(self)

    def eventFilter(self, obj, event):
        if hasattr(self, "searchEventFilter"):
            handled = self.searchEventFilter(obj, event)
            if handled:
                return True

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
        before_db = getattr(self, "current_db", None)

        ok = self._login()

        if not ok:
            if before_db:
                try:
                    db.set_db_path(before_db)
                    db.init()
                    db.save_last_db(before_db)
                    self.current_db = before_db

                    if hasattr(self, "_update_title"):
                        self._update_title()
                except Exception as e:
                    print("Failed to restore previous DB:", e)
            return

        if hasattr(self, "populate_tree"):
            self.populate_tree()
        if hasattr(self, "reload"):
            self.reload()

    def _update_title(self):
        db_path = (getattr(self, "current_db", "") or "").strip()
        if db_path:
            fname = Path(db_path).name
            self.setWindowTitle(f"AnchorPass: {fname}")
            if hasattr(self, "status_label"):
                self.status_label.setText(f"Active DB: {fname}")
        else:
            self.setWindowTitle("AnchorPass")
            if hasattr(self, "status_label"):
                self.status_label.setText("No database open")
