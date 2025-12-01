from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QDialog
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint, QItemSelectionModel, QObject
from PySide6.QtGui import QIcon

from ui.mixins.tree_mixin import TreeMixin
from ui.mixins.table_mixin import TableMixin
from ui.mixins.crud_mixin import CrudMixin
from ui.mixins.auth_mixin import AuthMixin
from ui.mixins.backup_mixin import BackupMixin
from ui.mixins.lock_mixin import LockMixin
from ui.mixins.preview_mixin import PreviewMixin

from ui.preferences_dialog import PreferencesDialog
from core.settings_manager import SettingsManager
from core import db
from styles.theme import load_styles

from ui.managers.backup_manager import BackupManager
from ui.managers.clipboard_manager import ClipboardManager
from ui.builders.ui_builder import UIBuilder

import time
from datetime import datetime, date
from ui.widgets.tray_icon_widget import TrayIconWidget
from pathlib import Path
from core import totp as totp_util
from ui.widgets.rounded_menu import RoundedMenu

BASE_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = BASE_DIR / "assets" / "icon.ico"
LOCKED_ICON_PATH = BASE_DIR / "assets" / "bwicon.ico"

class MainWindow(PreviewMixin, BackupMixin, LockMixin, CrudMixin, TableMixin, TreeMixin, AuthMixin, QMainWindow):
            
    def __init__(self, icon_family: str | None = None):

        super().__init__()
        self.settings = SettingsManager()
        self.setWindowTitle("AnchorPass")
        self.resize(1030, 550)
        self.setMinimumSize(818, 385)

        self.normal_icon = QIcon(str(ICON_PATH))
        self.locked_icon = QIcon(str(LOCKED_ICON_PATH))
        
        if not self.normal_icon.isNull():
            self.setWindowIcon(self.normal_icon)

        self.current_db = None
        self.master = None
        self.cipher = None
        self._ensure_backup_path_default()
        self.auto_lock_minutes = self.settings.get("auto_lock_minutes", 10)
        self.current_db = self.settings.get("database_path", None)
        self.current_category = None
        self._path_items = {}

        self.icon_family = icon_family or "Material Symbols Rounded"

        self.backup_manager = BackupManager(self.settings)
        self.clipboard_manager = ClipboardManager(self.settings, self._log_status)
        self.ui_builder = UIBuilder(self)
        
        self.ui_builder.build_central_widget()
        
        self.prompt_login(force=True)
        self.ui_builder.build_menus()

        self.ui_builder.build_shortcuts()
        self.ui_builder.wire_connections()

        try:
            if hasattr(self, "apply_table_prefs_from_settings"):
                self.apply_table_prefs_from_settings()
        except Exception:
            pass

        self.tray_icon = TrayIconWidget(
            parent=self,
            on_open=self._tray_open_from_tray,
            on_lock_db=self._lock_database_from_tray,
            icon=self.normal_icon,
            tooltip="AnchorPass",
        )
        self._search_prev_category: str | None = None

    def _cache_active_db_path_safely(self):
        try:
            active = getattr(db, "DB_PATH", None) or self.settings.get("database_path", None)
            if hasattr(self, "_cache_active_db_path"):
                self._cache_active_db_path(active)
        except Exception:
            pass

    def _start_idle_lock_timer(self):
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._auto_lock_check)
        self.idle_timer.start(30_000)
        self.last_activity = time.time()
        QApplication.instance().installEventFilter(self)

    def _start_scheduled_backup_timer(self):
        self._sched_timer = QTimer(self)
        self._sched_timer.timeout.connect(self._check_scheduled_backup)
        self._sched_timer.start(30_000)
        QTimer.singleShot(1500, self._check_scheduled_backup)

    def _start_sleep_guard(self):
        self._sleep_guard_last = time.monotonic()
        self._sleep_guard_timer = QTimer(self)
        self._sleep_guard_timer.setInterval(5_000)
        self._sleep_guard_timer.timeout.connect(self._sleep_guard_tick)
        self._sleep_guard_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.adjust_table_columns)

    def changeEvent(self, event):
        try:
            if event.type() == QEvent.WindowStateChange and self.isMinimized():
                if bool(self.settings.get("minimize_to_tray_on_minimize_chk", True)):
                    QTimer.singleShot(0, self._minimize_to_tray)

                if bool(self.settings.get("lock_on_minimize", True)):
                    QTimer.singleShot(100, self.lock)
        except Exception:
            pass

        super().changeEvent(event)

    def closeEvent(self, event):

        if self.settings.get("minimize_to_tray_on_exit", True):
            event.ignore()
            self.hide()

            if bool(self.settings.get("lock_on_minimize", True)):
                QTimer.singleShot(100, self.lock)
        else:
            super().closeEvent(event)

    def _start_expiration_checker(self):
        self._expiration_timer = QTimer(self)
        self._expiration_timer.timeout.connect(self._check_and_expire_entries)
        self._expiration_timer.start(60_000)
        QTimer.singleShot(2000, self._check_and_expire_entries)

    def _check_and_warn_expiring_entries(self):
        try:
            expiring_ids = db.get_entries_expiring_soon(days=5)
        except Exception:
            return

        if not expiring_ids:
            return

        self._log_status(
            f"{len(expiring_ids)} entr"
            f"{'y is' if len(expiring_ids) == 1 else 'ies are'} "
            "within 5 days of expiry",
            5000
        )

    def _check_and_expire_entries(self):
        try:
            expired_ids = db.check_and_expire_entries()
        except Exception:
            return

        if not expired_ids:
            return 

        if getattr(self, "cipher", None):
            try:
                if hasattr(self, "_rebuild_tree_preserving_selection"):
                    self._rebuild_tree_preserving_selection(target_category=getattr(self, "current_category", None))
                    self.reload()
                else:
                    if hasattr(self, "populate_tree"):
                        self.populate_tree()
                    self.reload()
            except Exception:
                try:
                    self._refresh_tree_and_table()
                except Exception:
                    pass

        self._log_status(f"{len(expired_ids)} entr{'y' if len(expired_ids)==1 else 'ies'} expired", 3000)

    def _update_actions_for_selection(self):
        try:
            count = len(self.table.selectionModel().selectedRows())
        except Exception:
            count = 0

        self.edit_btn.setEnabled(count == 1)
        self.duplicate_btn.setEnabled(count == 1)
        self.del_btn.setEnabled(count >= 1)

        outside_deleted = not self._in_deleted_folder()
        if hasattr(self, "archive_btn"):
            self.archive_btn.setEnabled(outside_deleted and count >= 1)
        if hasattr(self, "expire_btn"):
            self.expire_btn.setEnabled(outside_deleted and count >= 1)

        email_ok = user_ok = pwd_ok = False
        if count == 1:
            _, entry, plain = self._selected_entry_record()
            email_ok = bool(entry.get("email") or plain.get("email"))
            user_ok  = bool(entry.get("username") or plain.get("username"))
            pwd_ok   = bool(plain.get("password")) or bool(entry.get("password"))

        if hasattr(self, "copy_email_btn"):
            self.copy_email_btn.setEnabled(count == 1 and email_ok)
        if hasattr(self, "copy_user_btn"):
            self.copy_user_btn.setEnabled(count == 1 and user_ok)
        if hasattr(self, "copy_pass_btn"):
            self.copy_pass_btn.setEnabled(count == 1 and pwd_ok)

    def _selected_entry_id(self):
        sel = self.table.selectionModel()
        if not sel:
            return None
        rows = sel.selectedRows()
        if not rows:
            return None

        view_index = rows[0]
        model = self.table.model()

        if hasattr(model, "mapToSource"):
            source_index = model.mapToSource(view_index)
            source_model = model.sourceModel()
        else:
            source_index = view_index
            source_model = model

        if hasattr(self, "ID_COL"):
            id_idx = source_model.index(source_index.row(), self.ID_COL)
            return source_model.data(id_idx, Qt.DisplayRole)

        first_col = source_model.index(source_index.row(), 0)
        return source_model.data(first_col, Qt.UserRole)

    def _post_menu_refresh(self):
        refresher = getattr(self, "_refresh_tree_and_table", None)
        if callable(refresher):
            refresher(getattr(self, "current_category", None))
        else:
            try:
                if hasattr(self, "populate_tree"):
                    self.populate_tree()
            finally:
                try:
                    self.reload()
                except Exception:
                    pass

    def show_context_menu(self, pos: QPoint):
        view = self.table
        idx = view.indexAt(pos)
        if not idx.isValid():
            return
        
        sm = view.selectionModel()
        sm.setCurrentIndex(idx, QItemSelectionModel.NoUpdate | QItemSelectionModel.Rows)

        count = len(sm.selectedRows())

        if count > 1:
            self.show_context_menu_multi(pos)
            QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._post_menu_refresh))
            return

        try:
            super().show_context_menu(pos)
        except AttributeError:
            menu = RoundedMenu(self)
            if count == 1:
                menu.addAction("Edit", self.edit_entry)
            label = "Delete Permanently" if self._in_deleted_folder() else "Delete (to Trash)"
            menu.addAction(
                label,
                self.delete_entry if count <= 1 else self.delete_selected_entries,
            )
            menu.exec(view.viewport().mapToGlobal(pos))

    def show_context_menu_multi(self, pos: QPoint):
        view = self.table
        sm = view.selectionModel()
        cnt = len(sm.selectedRows()) if sm else 0
        if cnt < 2:
            return

        menu = RoundedMenu(self)

        hdr = menu.addAction(f"{cnt} selected")
        hdr.setEnabled(False)
        menu.addSeparator()

        if self._in_deleted_folder():
            if hasattr(self, "restore_selected_entries"):
                menu.addAction("Restore Selected", self.restore_selected_entries)
            menu.addAction("Delete Permanently", self.delete_selected_entries)
        else:
            menu.addAction("Archive Selected", self.archive_selected_entries)
            menu.addAction("Expire Selected", self.expire_selected_entries)
            menu.addSeparator()
            menu.addAction("Delete (to Trash)", self.delete_selected_entries)

        menu.exec(view.viewport().mapToGlobal(pos))
            
    def add_entry(self):
        try:
            super().add_entry()
            self._refresh_tree_and_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add entry:\n{e}")

    def edit_entry(self):
        try:
            if len(self.table.selectionModel().selectedRows()) != 1:
                return
        except Exception:
            return
        try:
            super().edit_entry()
            self._refresh_tree_and_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit entry:\n{e}")

    def _edit_single_entry(self, entry_id):
        if not entry_id:
            return

        try:
            super().edit_single_entry(entry_id)
            self._refresh_tree_and_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit entry:\n{e}")

    def delete_entry(self):
        try:
            count = len(self.table.selectionModel().selectedRows())
        except Exception:
            count = 0

        if count <= 1:
            try:
                entry_id = self._get_selected_entry_id_from_table()
            except AttributeError:
                entry_id = None

            if not entry_id:
                QMessageBox.information(self, "Delete", "Please select a row to delete.")
                return

            row = self.table.currentRow()
            site_text = self.table.item(row, 0).text() if row >= 0 and self.table.item(row, 0) else ""

            if self._in_deleted_folder():
                ok = QMessageBox.warning( self, "Permanently Delete", f"Permanently delete '{site_text}'?\n\nThis action cannot be undone!",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No )
                if ok != QMessageBox.Yes:
                    return
                try:
                    db.permanently_delete_entry(entry_id)
                    self._refresh_tree_and_table()
                    self._log_status("Item permanently deleted.", 1500)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to permanently delete entry:\n{e}")
            else:
                ok = QMessageBox.question( self, "Confirm Delete", f"Move '{site_text}' to Trash?\n(You can restore it later.)",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No )
                if ok != QMessageBox.Yes:
                    return

                try:
                    db.delete_entry(entry_id)
                    self._refresh_tree_and_table()
                    self._log_status("Moved to Trash", 1500)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete entry:\n{e}")
        else:
            self.delete_selected_entries()

    def _delete_single_entry(self, entry_id: int):
        if not entry_id:
            QMessageBox.information(self, "Delete", "Please select a row to delete.")
            return

        entry = db.fetch_entry_dict(entry_id) or {}
        site_text = entry.get("site", "")

        if self._in_deleted_folder():
            ok = QMessageBox.warning(
                self,
                "Permanently Delete",
                f"Permanently delete '{site_text}'?\n\nThis action cannot be undone!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ok != QMessageBox.Yes:
                return

            try:
                db.permanently_delete_entry(entry_id)
                self.populate_tree()
                self.reload()
                self._log_status("Item permanently deleted.", 1500)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to permanently delete entry:\n{e}")
        else:
            ok = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Move '{site_text}' to Trash?\n(You can restore it later.)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ok != QMessageBox.Yes:
                return

            try:
                db.delete_entry(entry_id)
                self._refresh_tree_and_table()
                self._log_status("Moved to Trash", 1500)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete entry:\n{e}")

    def delete_selected_entries(self):
        ids = self._get_all_selected_entry_ids()
        if not ids:
            QMessageBox.information(self, "Delete", "Please select at least one row to delete.")
            return

        if self._in_deleted_folder():
            if len(ids) == 1:
                msg = "Permanently delete the selected entry?\n\nThis cannot be undone!"
            else:
                msg = f"Permanently delete {len(ids)} selected entries?\n\nThis cannot be undone!"
            ok = QMessageBox.warning(self, "Permanently Delete", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ok != QMessageBox.Yes:
                return

            errors = 0
            for entry_id in ids:
                try:
                    db.permanently_delete_entry(entry_id)
                except Exception:
                    errors += 1

            self._refresh_tree_and_table()
            if errors == 0:
                self._log_status(f"Permanently deleted {len(ids)} item{'s' if len(ids)!=1 else ''}.", 2000)
            else:
                QMessageBox.warning(self, "Delete", f"Permanently deleted {len(ids)-errors}, but {errors} failed.")
        else:
            if len(ids) == 1:
                msg = f"Move the entry '{self.table.item(self.table.currentRow(), 0).text()}' to Trash?"
            else:
                msg = f"Move {len(ids)} selected entries to Trash?"
            msg += "\n(You can restore them later.)"

            ok = QMessageBox.question(self, "Confirm Delete", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ok != QMessageBox.Yes:
                return

            errors = 0
            for entry_id in ids:
                try:
                    db.delete_entry(entry_id)
                except Exception:
                    errors += 1

            self._refresh_tree_and_table()
            if errors == 0:
                self._log_status(f"Moved {len(ids)} entr{'y' if len(ids)==1 else 'ies'} to Trash.", 1500)
            else:
                QMessageBox.warning(self, "Delete", f"Moved {len(ids)-errors} to Trash, but {errors} failed.")

    def restore_selected_entries(self, checked: bool = False):
        ids = self._get_all_selected_entry_ids()
        if not ids:
            self._log_status("No entries selected.", 1500); return
        errors = 0
        for eid in ids:
            try:
                if hasattr(db, "restore_entry"):
                    db.restore_entry(eid)
                else:
                    db.set_status(eid, "active")
            except Exception:
                errors += 1
        self._refresh_tree_and_table()
        self._log_status(
            f"Restored {len(ids)-errors}/{len(ids)} entr{'y' if len(ids)==1 else 'ies'}.",
            2000
        )

    def archive_selected_entries(self, checked: bool = False):
        ids = self._get_all_selected_entry_ids()
        if not ids:
            self._log_status("No entries selected.", 1500)
            return

        errors = 0
        for eid in ids:
            try:
                if hasattr(self, "_archive_single_entry"):
                    self._archive_single_entry(eid)
                else:
                    db.delete_entry(eid)             
            except Exception:
                errors += 1

        self._refresh_tree_and_table()
        ok = len(ids) - errors
        if errors == 0:
            self._log_status(f"Archived {ok} entr{'y' if ok==1 else 'ies'}.", 1500)
        else:
            QMessageBox.warning(self, "Archive Selected", f"Archived {ok}; {errors} failed.")

    def expire_selected_entries(self, checked: bool = False):
        ids = self._get_all_selected_entry_ids()
        if not ids:
            self._log_status("No entries selected.", 1500)
            return

        errors = 0
        for eid in ids:
            try:
                if hasattr(self, "_force_expire_entry"):
                    self._force_expire_entry(eid)   
                elif hasattr(db, "force_expire_entry"):
                    db.force_expire_entry(eid)   
                elif hasattr(db, "set_status"):
                    db.set_status(eid, "expired")   
                else:
                    raise RuntimeError("No expire API available.")
            except Exception:
                errors += 1

        self.reload()
        ok = len(ids) - errors
        if errors == 0:
            self._log_status(f"Expired {ok} entr{'y' if ok==1 else 'ies'}.", 1500)
        else:
            QMessageBox.warning(self, "Expire Selected", f"Expired {ok}; {errors} failed.")
            
    def _on_archive_clicked(self, checked: bool = False):
        try:
            rows = self.table.selectionModel().selectedRows()
        except Exception:
            rows = []
        if not rows:
            self._log_status("Select at least one entry.", 1500)
            return
        return self.archive_selected_entries()

    def _on_expire_clicked(self, checked: bool = False):
        if hasattr(self, "expire_selected_entries"):
            return self.expire_selected_entries()

        try:
            entry_id = self._get_selected_entry_id_from_table()
        except Exception:
            entry_id = None
        entry_id = entry_id or getattr(self, "_selected_entry_id", lambda: None)()
        if not entry_id:
            self._log_status("Select an entry.", 1500)
            return
        try:
            if hasattr(self, "_force_expire_entry"):
                self._force_expire_entry(entry_id)
            elif hasattr(db, "force_expire_entry"):
                db.force_expire_entry(entry_id)
            else:
                db.set_status(entry_id, "expired")
            self.reload()
            self._log_status("Entry expired.", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Expire", f"Failed to expire entry:\n{e}")

    def purge_selected_entries(self):
        ids = self._get_all_selected_entry_ids()
        if not ids:
            QMessageBox.information(self, "Permanently Delete", "Please select at least one row.")
            return
        if len(ids) == 1:
            msg = "Permanently delete the selected entry?\n\nThis cannot be undone!"
        else:
            msg = f"Permanently delete {len(ids)} selected entries?\n\nThis cannot be undone!"
        ok = QMessageBox.warning(self, "Permanently Delete", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        errors = 0
        for entry_id in ids:
            try:
                db.permanently_delete_entry(entry_id)
            except Exception:
                errors += 1
        self._refresh_tree_and_table()
        if errors == 0:
            self._log_status(f"Permanently deleted {len(ids)} item{'s' if len(ids)!=1 else ''}.", 2000)
        else:
            QMessageBox.warning(self, "Permanently Delete", f"Deleted {len(ids)-errors}; {errors} failed.")

    def _get_all_selected_entry_ids(self) -> list[int]:
        ids, seen = [], set()
        sm = self.table.selectionModel()
        if not sm:
            return ids

        for idx in sm.selectedRows():
            eid = None
            it0 = self.table.item(idx.row(), 0)
            if it0 is not None:
                val = it0.data(Qt.UserRole)
                try:
                    eid = int(val) if val is not None else None
                except Exception:
                    eid = None

            if eid is None and hasattr(self, "_current_rows"):
                try:
                    eid = int(self._current_rows[idx.row()][0])
                except Exception:
                    pass

            if eid is not None and eid not in seen:
                seen.add(eid)
                ids.append(eid)

        return ids


    def reload(self):

        cat = getattr(self, "current_category", None)

        try:
            if cat == getattr(TreeMixin, "SPECIAL_DELETED", "__SPECIAL_DELETED__"):
                rows = db.fetch_by_status("deleted")
            elif cat == getattr(TreeMixin, "SPECIAL_EXPIRED", "__SPECIAL_EXPIRED__"):
                rows = db.fetch_by_status("expired")
            elif cat == getattr(TreeMixin, "SPECIAL_ARCHIVED", "__SPECIAL_ARCHIVED__"):
                rows = db.fetch_by_status("archived")
            elif cat:
                rows = db.fetch_by_category(cat, include_descendants=False)
            else:
                rows = db.fetch_all()
        except Exception:
            rows = db.fetch_all()

        self._load_table(rows)
        
    def _copy_selected_field(self, field: str):
        try:
            if len(self.table.selectionModel().selectedRows()) != 1:
                self._log_status("Select exactly one entry to use this hotkey.", 2000)
                return
        except Exception:
            self._log_status("No selection.", 1500)
            return

        try:
            entry_id = self._get_selected_entry_id_from_table()
        except Exception:
            entry_id = None
            
        if not entry_id:
            self._log_status("Could not resolve selected entry.", 2000)
            return

        try:
            row = db.fetch_entry_dict(entry_id)
        except Exception:
            row = None
            
        if not row:
            self._log_status("Entry not found.", 2000)
            return

        self.clipboard_manager.copy_field_from_entry(row, field, self.cipher)

    def open_settings_dialog(self):
        old_theme = self.settings.get("theme", "dark")

        dlg = PreferencesDialog(main_window=self, settings=self.settings)
        try:
            result = dlg.exec()
        finally:
            dlg.deleteLater()

        if result != QDialog.Accepted:
            self._log_status("Settings unchanged.", 2000)
            return

        self.backup_manager.settings = self.settings
        self.clipboard_manager.settings = self.settings
        
        self.auto_lock_minutes = self.settings.get("auto_lock_minutes", 10)
        self.current_db = self.settings.get("database_path", None)

        self._cache_active_db_path_safely()

        if hasattr(self, "ui_builder"):
                self.ui_builder.build_shortcuts()

        new_theme = self.settings.get("theme", "dark")
        if new_theme != old_theme:
            try:
                self._apply_theme_from_settings()
            except Exception:
                pass

        self._sched_first_log_done = False
        self._sched_last_skip_note_at = 0
        self._check_scheduled_backup()

        self._log_status("Settings saved.", 2000)

    def _open_backup_folder(self):
        path = (self.settings.get("backup_path", "") or "").strip() or \
               (self.settings.get("backup_dir", "") or "").strip()
        if not path:
            QMessageBox.information(self, "Backups", "Set a backup folder in Preferences first.")
            return
        try:
            QFileDialog.getOpenFileName(self, "Backup Folder", path)
        except Exception:
            QMessageBox.information(self, "Backups", path)

    def _check_scheduled_backup(self):
        ok, reason, interval = self.backup_manager.is_backup_configured()
        now_ts = int(time.time())
        first_logged = getattr(self, "_sched_first_log_done", False)

        if not ok:
            last_note = getattr(self, "_sched_last_skip_note_at", 0)
            if (not first_logged) or (now_ts - last_note > 3600):
                self._log_status(reason or "Scheduled backup skipped.")
                self._sched_last_skip_note_at = now_ts
                self._sched_first_log_done = True
            return

        target_today = self.backup_manager.get_target_time()
        now = datetime.now()

        if not first_logged:
            self._log_status(f"Scheduler armed for ~{target_today.strftime('%Y-%m-%d %H:%M')} ({interval}).")
            self._sched_first_log_done = True

        if now < target_today:
            return

        last_run = self.settings.get("backup_last_run", "")
        
        if self.backup_manager.should_run_backup(interval, last_run):
            dst = self.export_backup(reason="scheduled")
            if dst:
                self.settings.set("backup_last_run", date.today().strftime("%Y-%m-%d"))
                self._log_status("Scheduled backup saved.")
            else:
                self._log_status("Scheduled backup attempted but not saved.", 4000)
                
    def _log_status(self, text: str, ms: int = 3000, is_error: bool = False) -> None:
        try:
            bar = self.statusBar()
            if is_error:
                bar.setStyleSheet("color: red;")
            else:
                bar.setStyleSheet("")

            bar.showMessage(text, ms)
        except Exception:
            pass

    def _sleep_guard_tick(self):
        try:
            if not bool(self.settings.get("lock_on_sleep", True)):
                self._sleep_guard_last = time.monotonic()
                return

            now = time.monotonic()
            delta = now - getattr(self, "_sleep_guard_last", now)
            self._sleep_guard_last = now
            if delta > 20:
                self.lock()
        except Exception:
            self._sleep_guard_last = time.monotonic()

    def change_database(self):
        try:
            super().change_database()
        finally:
            self._cache_active_db_path_safely()
            try:
                if hasattr(self, "apply_table_prefs_from_settings"):
                    self.apply_table_prefs_from_settings()
            except Exception:
                pass

    def _in_deleted_folder(self) -> bool:
        return getattr(self, "current_category", None) == getattr(TreeMixin, "SPECIAL_DELETED", "__SPECIAL_DELETED__")
    
    def _in_expired_folder(self) -> bool:
        return getattr(self, "current_category", None) == getattr(TreeMixin, "SPECIAL_EXPIRED", "__SPECIAL_EXPIRED__")

    def _in_archived_folder(self) -> bool:
        return getattr(self, "current_category", None) == getattr(TreeMixin, "SPECIAL_ARCHIVED", "__SPECIAL_ARCHIVED__")
    
    def _selected_entry_record(self):
        try:
            count = len(self.table.selectionModel().selectedRows())
        except Exception:
            count = 0
        if count != 1:
            return None, {}, {}

        try:
            entry_id = self._get_selected_entry_id_from_table()
        except Exception:
            entry_id = None
        if not entry_id and hasattr(self, "_selected_entry_id"):
            entry_id = self._selected_entry_id()
        if not entry_id:
            return None, {}, {}

        try:
            entry = db.fetch_entry_dict(entry_id) or {}
        except Exception:
            entry = {}
        plain = {}
        try:
            if hasattr(db, "decrypt_row_to_plain"):
                plain = db.decrypt_row_to_plain(entry, self.cipher) or {}
        except Exception:
            pass
        return entry_id, entry, plain

    def _refresh_tree_and_table(self, target_category: str | None = None):
        prev = getattr(self, "current_category", None)
        try:
            if hasattr(self, "populate_tree"):
                self.populate_tree()
        except Exception:
            pass

        cat = target_category if target_category is not None else prev
        if cat and hasattr(self, "_path_items") and hasattr(self, "tree"):
            item = self._path_items.get(cat)
            if item:
                try:
                    self.tree.setCurrentItem(item)
                    self.current_category = cat
                except Exception:
                    pass

        self.reload()
        if hasattr(self, "_update_actions_for_selection"):
            self._update_actions_for_selection()

    def _set_menu_locked_state(self, locked: bool):
        mb = self.menuBar()
        if mb:
            mb.setEnabled(not locked)

    def _tray_open_from_tray(self):
        if not self.isVisible():
            self.show()

        if self.isMinimized():
            self.showNormal()

        self.raise_()
        self.activateWindow()

        self.setWindowState(self.windowState() | Qt.WindowActive)

    def _minimize_to_tray(self):
        self.hide()

        try:
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        except Exception:
            pass

    def _lock_database_from_tray(self):
        if hasattr(self, "lock"):
            self.lock()
        else:
            pass

    def _update_tray_icon_locked_state(self, locked: bool):
        if not hasattr(self, "tray_icon") or self.tray_icon is None:
            return

        icon = self.locked_icon if locked else self.normal_icon

        if icon is None or icon.isNull():
            return

        self.tray_icon.set_icon(icon)
        try:
            self.setWindowIcon(icon)
        except Exception:
            pass

    def searchEventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is getattr(self, "search", None):
            if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):

                table = getattr(self, "table", None)
                if table is not None:
                    try:
                        sm = table.selectionModel()
                        if sm:
                            sm.clearSelection()
                        table.setCurrentItem(None)
                    except Exception:
                        pass

                tree = getattr(self, "tree", None)
                if tree is not None:
                    try:
                        tree.clearSelection()
                    except Exception:
                        pass

        return False
    
    def _copy_totp_for_selection(self):
        entry_id = self._get_selected_entry_id_from_table()
        if not entry_id:
            return

        entry = db.fetch_entry_dict(int(entry_id)) or {}

        plain = {}
        if getattr(self, "cipher", None):
            try:
                plain = db.decrypt_row_to_plain(entry, self.cipher) or {}
            except Exception:
                plain = {}

        otp_secret = (plain.get("otp_secret") or entry.get("otp_secret") or "").strip()
        if not otp_secret:
            try:
                self.statusBar().showMessage("No TOTP configured for this entry.", 2000)
            except Exception:
                pass
            return

        try:
            code_now, _, _ = totp_util.totp_from_uri_or_secret(otp_secret)
        except Exception:
            return

        if not code_now:
            return

        self._copy_to_clipboard("TOTP code", code_now)

    def _apply_theme_from_settings(self):
        try:
            theme = self.settings.get("theme", "dark")
            load_styles(QApplication.instance(), theme=theme)
            self._refresh_lock_overlay_icon()
        except Exception as e:
            pass