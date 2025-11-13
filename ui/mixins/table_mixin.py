from PySide6.QtWidgets import QTableWidgetItem, QMenu, QApplication, QHeaderView, QMessageBox
from PySide6.QtCore import Qt, QTimer, QEventLoop
from PySide6.QtGui import QColor

from ui.widgets.custom_table import ModernTable, SortableItem, STATUS_ORDER
from ui.widgets.status_badge import StatusBadgeTableWidget
from core import db
from core import totp as totp_util
from core.settings_manager import SettingsManager


class TableMixin:
    def setup_table(self):
        self.table = ModernTable(self)
        self.table.setObjectName("ModernTable")

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Site", "Email", "Username", "Status", "Notes"])

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.on_table_double_clicked)

        self.adjust_table_columns()

    def adjust_table_columns(self):
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        hdr.resizeSection(3, 120)
        hdr.setSectionResizeMode(4, QHeaderView.Stretch)

        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def refresh_qss(self):
        app = QApplication.instance()
        self.table.style().unpolish(self.table)
        self.table.style().polish(self.table)
        self.table.update()

    def _create_status_badge(self, status: str) -> QTableWidgetItem:
        s = (status or "").strip().lower()
        rank = STATUS_ORDER.get(s, 99)
        it = SortableItem(status, (0, rank))
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        it.setText("")
        return it

    def _load_table(self, rows):
        hdr = self.table.horizontalHeader()
        prev_col   = hdr.sortIndicatorSection()
        prev_order = hdr.sortIndicatorOrder()
        self.table.setSortingEnabled(False)

        self.table.setRowCount(0)
        self._current_rows = rows
        self.table.setRowCount(len(rows))

        icon_family = getattr(self, "icon_family", None)

        for r, row in enumerate(rows):
            id_ = row[0]
            entry_full = db.fetch_entry_dict(int(id_)) or {}

            site = row[1] or ""
            email = row[2] or ""
            username = row[3] or ""
            notes = row[5] or ""
            status = entry_full.get("status", "active")

            display_email = email
            if getattr(self, "cipher", None):
                plain = db.decrypt_row_to_plain(entry_full, self.cipher)
                display_email = plain.get("email", display_email) or display_email

            it_site   = QTableWidgetItem(site);    it_site.setData(Qt.UserRole, int(id_))
            it_email  = QTableWidgetItem(display_email)
            it_user   = QTableWidgetItem(username)
            it_status = self._create_status_badge(status)
            it_notes  = QTableWidgetItem(notes)

            if status == "deleted":
                font = it_site.font(); font.setStrikeOut(True)
                for it in (it_site, it_email, it_user, it_notes):
                    it.setFont(font); it.setForeground(QColor("#6b7280"))

            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            for it in (it_site, it_email, it_user, it_notes):
                it.setFlags(flags)

            self.table.setItem(r, 0, it_site)
            self.table.setItem(r, 1, it_email)
            self.table.setItem(r, 2, it_user)
            self.table.setItem(r, 3, it_status)
            self.table.setItem(r, 4, it_notes)

            badge = StatusBadgeTableWidget(status, icon_family)
            self.table.setCellWidget(r, 3, badge)
            it_status.setSizeHint(badge.sizeHint())

        if rows:
            self.table.setCurrentCell(0, 0)

        self.table.setSortingEnabled(True)
        if prev_col >= 0:
            self.table.sortItems(prev_col, prev_order)

    def reload(self):
        try:
            db.check_and_expire_entries()
        except Exception:
            pass
            
        if getattr(self, "current_category", None):
            rows = db.fetch_by_category(self.current_category, include_descendants=False)
        else:
            rows = db.fetch_all()
        self._load_table(rows)

    def filter_table(self, text: str):
        text = (text or "").strip()
        if not text:
            self.tree.clearSelection()
            self.reload()
            return

        rows = db.search_entries(text)

        if getattr(self, "cipher", None):
            text_low = text.lower()
            present_ids = {int(r[0]) for r in rows}
            for r in db.fetch_all():
                rid = int(r[0])
                if rid in present_ids:
                    continue
                entry_full = db.fetch_entry_dict(rid) or {}
                plain = db.decrypt_row_to_plain(entry_full, self.cipher)
                dec_email = plain.get("email", "") or ""
                if dec_email and text_low in dec_email.lower():
                    rows.append(
                        (
                            entry_full["id"],
                            entry_full.get("site", ""),
                            entry_full.get("email", "") or "",
                            entry_full.get("username", ""),
                            entry_full.get("password_enc", ""),
                            entry_full.get("notes", ""),
                            entry_full.get("category", ""),
                        )
                    )
                    present_ids.add(rid)

        self.tree.clearSelection()
        self.current_category = None
        self._load_table(rows)

    def _get_selected_entry_id_from_table(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it0 = self.table.item(row, 0)
        if it0 is not None:
            iddata = it0.data(Qt.UserRole)
            if iddata is not None:
                try:
                    return int(iddata)
                except Exception:
                    pass
        if hasattr(self, "_current_rows") and 0 <= row < len(self._current_rows):
            try:
                return int(self._current_rows[row][0])
            except Exception:
                return None
        return None

    def _find_row_by_id(self, entry_id: int):
        if entry_id is None:
            return None
        rows = self.table.rowCount()
        for r in range(rows):
            it0 = self.table.item(r, 0)
            if not it0:
                continue
            iddata = it0.data(Qt.UserRole)
            try:
                if iddata is not None and int(iddata) == int(entry_id):
                    return r
            except Exception:
                pass
        return None

    def on_table_double_clicked(self, *_):
        entry_id = self._get_selected_entry_id_from_table()
        self.edit_entry()
        if entry_id is not None:
            row = self._find_row_by_id(entry_id)
            if row is not None:
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)

    def _copy_to_clipboard(self, label: str, value: str):
        if not value:
            return

        cb = QApplication.clipboard()
        cb.setText(value)

        settings = SettingsManager()
        secs = int(settings.get("clipboard_clear_seconds", 15) or 0)
        notify = bool(settings.get("copy_notifications", True))

        if notify:
            try:
                self.statusBar().showMessage(f"Copied {label}", 1500)
            except Exception:
                pass

        token = getattr(self, "_cb_token", 0) + 1
        self._cb_token = token

        if secs > 0:
            def clear_if_unchanged():
                if getattr(self, "_cb_token", None) == token and cb.text() == value:
                    cb.clear()
                    if notify:
                        try:
                            self.statusBar().showMessage("Clipboard cleared", 1500)
                        except Exception:
                            pass

            QTimer.singleShot(secs * 1000, clear_if_unchanged)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self.table.setCurrentCell(row, 0)

        entry_id = self._get_selected_entry_id_from_table()
        if not entry_id:
            return

        entry = db.fetch_entry_dict(entry_id) or {}
        plain = db.decrypt_row_to_plain(entry, self.cipher)
        status = entry.get("status", "active")

        site = entry.get("site", "")
        email = entry.get("email", "")
        username = entry.get("username", "")
        password = plain.get("password", "")
        pin = plain.get("pin", "")
        sec_code = plain.get("security_code", "")
        app_pass = plain.get("app_password", "")
        otp_secret = plain.get("otp_secret", "")

        code_now = ""
        if otp_secret:
            code_now, _, _ = totp_util.totp_from_uri_or_secret(otp_secret)

        menu = QMenu(self)

        menu.addAction("Edit…", lambda: QTimer.singleShot(0, self.edit_entry))
        menu.addSeparator()

        a_site = menu.addAction("Copy Site", lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("site", site)))
        a_site.setEnabled(bool(site))

        a_email = menu.addAction(
            "Copy Email",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("email", email or plain.get("email", "")))
        )
        a_email.setEnabled(bool(email or plain.get("email", "")))

        a_user = menu.addAction(
            "Copy Username",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("username", username))
        )
        a_user.setEnabled(bool(username))

        a_pwd = menu.addAction(
            "Copy Password",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("password", password))
        )
        a_pwd.setEnabled(bool(password) and bool(getattr(self, "cipher", None)))

        menu.addSeparator()

        a_pin = menu.addAction(
            "Copy PIN",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("PIN", pin))
        )
        a_pin.setEnabled(bool(pin) and bool(getattr(self, "cipher", None)))

        a_sec = menu.addAction(
            "Copy Security Code",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("security code", sec_code))
        )
        a_sec.setEnabled(bool(sec_code) and bool(getattr(self, "cipher", None)))

        a_app = menu.addAction(
            "Copy App Password",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("app password", app_pass))
        )
        a_app.setEnabled(bool(app_pass) and bool(getattr(self, "cipher", None)))

        a_totp = menu.addAction(
            "Copy TOTP Code",
            lambda: QTimer.singleShot(0, lambda: self._copy_to_clipboard("TOTP code", totp_util.totp_from_uri_or_secret(otp_secret)[0]))
        )
        a_totp.setEnabled(bool(code_now))

        menu.addSeparator()

        if status in ["active", "expired"]:
            menu.addAction("Archive", lambda: QTimer.singleShot(0, lambda: self._archive_single_entry(entry_id)))
        
        if status == "active":
            menu.addAction("Force Expire", lambda: QTimer.singleShot(0, lambda: self._force_expire_entry(entry_id)))
        
        if status in ["archived", "deleted"]:
            menu.addAction("Restore", lambda: QTimer.singleShot(0, lambda: self._restore_single_entry(entry_id)))
        
        menu.addSeparator()
        
        if status != "deleted":
            menu.addAction("Delete (to Trash)", lambda: QTimer.singleShot(0, self.delete_entry))
        else:
            menu.addAction("Permanently Delete", lambda: QTimer.singleShot(0, lambda: self._permanently_delete_single_entry(entry_id)))

        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        menu.exec(self.table.viewport().mapToGlobal(pos))
        self.table.clearFocus()

    # Lifecycle helper methods
    def _archive_single_entry(self, entry_id: int):
        try:
            db.change_status(entry_id, "archived")
            if hasattr(self, 'populate_tree'):
                self.populate_tree()
            self._refresh_current_view()
            self._log_status("Entry archived", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to archive entry:\n{e}")

    def _force_expire_entry(self, entry_id: int):
        try:
            db.change_status(entry_id, "expired")
            if hasattr(self, 'populate_tree'):
                self.populate_tree()
            self._refresh_current_view()
            self._log_status("Entry marked as expired", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to expire entry:\n{e}")

    def _restore_single_entry(self, entry_id: int):
        try:
            db.restore_entry(entry_id)
            refresher = getattr(self, "_refresh_tree_and_table", None)
            if callable(refresher):
                refresher()
            else:
                if hasattr(self, "populate_tree"):
                    self.populate_tree()
                self._refresh_current_view()
            self._log_status("Entry restored", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore entry:\n{e}")
    
    def _refresh_current_view(self):
        category = getattr(self, 'current_category', None)
        
        if not category:
            self.reload()
            return
        
        try:
            from ui.mixins.tree_mixin import TreeMixin
            SPECIAL_DELETED = TreeMixin.SPECIAL_DELETED
            SPECIAL_ARCHIVED = TreeMixin.SPECIAL_ARCHIVED
            SPECIAL_EXPIRED = TreeMixin.SPECIAL_EXPIRED
            
            if category == SPECIAL_DELETED:
                self._load_special_folder_entries("deleted")
            elif category == SPECIAL_ARCHIVED:
                self._load_special_folder_entries("archived")
            elif category == SPECIAL_EXPIRED:
                self._load_special_folder_entries("expired")
            else:
                self.reload()
        except:
            self.reload()
    
    def _load_special_folder_entries(self, status: str):
        try:
            rows = db.fetch_by_status(status)
            self._load_table(rows)
        except Exception:
            self._load_table([])

    def _permanently_delete_single_entry(self, entry_id: int):
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.warning(
            self, "Permanently Delete Entry",
            "This will PERMANENTLY delete this entry and cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                db.permanently_delete_entry(entry_id)
                if hasattr(self, 'populate_tree'):
                    self.populate_tree()
                self._refresh_current_view()
                self._log_status("Entry permanently deleted", 1500)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to permanently delete entry:\n{e}")