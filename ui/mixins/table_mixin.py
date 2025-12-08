from PySide6.QtWidgets import (QTableWidgetItem, QApplication, QHeaderView, QMessageBox, QAbstractItemView, QDialog, QVBoxLayout, 
                               QCheckBox, QDialogButtonBox, QHBoxLayout, QGridLayout)
from PySide6.QtCore import Qt, QTimer, QItemSelectionModel, QByteArray
from PySide6.QtGui import QColor

from ui.widgets.custom_table import ModernTable, SortableItem, STATUS_ORDER
from ui.widgets.status_badge import StatusBadgeTableWidget
from core import db
from core import totp as totp_util
from core.settings_manager import SettingsManager
from ui.mixins.tree_mixin import TreeMixin
from datetime import date, timedelta, datetime
from typing import Optional
from ui.widgets.rounded_menu import RoundedMenu
from core.utils.datetime_utils import format_datetime

def is_expiring_soon(expiry_date_str: str | None, days: int = 5) -> bool:
    if not expiry_date_str:
        return False
    try:
        expiry = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
    except ValueError:
        return False

    today = date.today()
    return today < expiry <= today + timedelta(days=days)

def days_left_if_expiring_soon(expiry_date_str: str | None, days: int = 5) -> Optional[int]:
    if not expiry_date_str:
        return None

    try:
        expiry = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    today = date.today()
    delta_days = (expiry - today).days

    if 0 < delta_days <= days:
        return delta_days
    elif delta_days == 0:
        return 0  
    
    return None

COLUMN_DEFS = {
    "email": "Email",
    "username": "Username",
    "status": "Status",
    "notes": "Notes",
    "site_link": "Link",
    "date_modified": "Modified",
    "date_created": "Created",
    "category": "Category",
    "tags": "Tags"
}

DEFAULT_EXTRA_COLUMNS = ["email", "username", "status", "notes"]

MAX_EXTRA_COLUMNS = 4

class TableMixin:
    def setup_table(self):
        self.table = ModernTable(self)
        self.table.setObjectName("ModernTable")

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setDragEnabled(True)
        self.table.setDragDropMode(QAbstractItemView.DragOnly)

        self._extra_column_keys = self._load_extra_column_keys()
        self._apply_table_headers()

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        self.table.clicked.connect(self._on_table_clicked)

        header = self.table.horizontalHeader()
        header.sectionMoved.connect(self._on_header_section_moved)

        self.adjust_table_columns()

    def _on_table_clicked(self, index):
        search = getattr(self, "search", None)
        if search is None:
            return
        search.clearFocus()

    def adjust_table_columns(self):
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(150)
        for i in range(self.table.columnCount()):
            hdr.setSectionResizeMode(i, QHeaderView.Interactive)

        default_widths = [150, 150, 150, 150]  # 1 per column, tweak as needed
        for col, width in enumerate(default_widths):
            if col < self.table.columnCount():
                hdr.resizeSection(col, width)

        if hasattr(self, "_extra_column_keys") and "status" in self._extra_column_keys:
            status_idx = 1 + self._extra_column_keys.index("status")
            hdr.setSectionResizeMode(status_idx, QHeaderView.Interactive)
            hdr.resizeSection(status_idx, 120)

        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def _on_header_section_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int):
        self._save_column_order()

    def _save_column_order(self):
        if not hasattr(self, "table") or self.table is None:
            return

        header = self.table.horizontalHeader()
        state = header.saveState()
        state_str = bytes(state.toBase64()).decode("ascii")

        settings = getattr(self, "settings", None)
        if settings is None:
            return

        settings.set("table_header_state", state_str)

    def _restore_column_order(self):
        if not hasattr(self, "table") or self.table is None:
            return

        settings = getattr(self, "settings", None)
        if settings is None:
            return

        state_str = settings.get("table_header_state", None)


        if not state_str:
            return

        header = self.table.horizontalHeader()

        try:
            ba = QByteArray.fromBase64(state_str.encode("ascii"))
        except Exception:
            return

        header.restoreState(ba)

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
            expiry_date = entry_full.get("expiry_date")

            display_email = email
            if getattr(self, "cipher", None):
                plain = db.decrypt_row_to_plain(entry_full, self.cipher)
                display_email = plain.get("email", display_email) or display_email

            it_site   = QTableWidgetItem(site);    it_site.setData(Qt.UserRole, int(id_))
            it_email  = QTableWidgetItem(display_email)
            it_user   = QTableWidgetItem(username)
            it_status = self._create_status_badge(status)
            it_notes  = QTableWidgetItem(notes)

            deleted_font = None
            deleted_brush = None
            if status == "deleted":
                deleted_font = it_site.font()
                deleted_font.setStrikeOut(True)
                deleted_brush = QColor("#6b7280")

                for it in (it_site, it_email, it_user, it_notes):
                    it.setFont(deleted_font)
                    it.setForeground(deleted_brush)

            can_drag = status not in ("deleted",)
            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            if can_drag:
                flags |= Qt.ItemIsDragEnabled

            for it in (it_site, it_email, it_user, it_notes):
                it.setFlags(flags)

            self.table.setItem(r, 0, it_site)

            badge_status = status
            if status == "active" and is_expiring_soon(expiry_date, days=5):
                badge_status = "expiring"

            days_left = days_left_if_expiring_soon(expiry_date, days=5)
            badge = StatusBadgeTableWidget(badge_status, icon_family)
            it_status.setSizeHint(badge.sizeHint())

            if days_left is not None and days_left >= 0:
                if days_left == 0:
                    tip = "Expires today"
                elif days_left == 1:
                    tip = "Expires in 1 day"
                else:
                    tip = f"Expires in {days_left} days"

                badge.setToolTip(tip)
                it_status.setToolTip(tip)

            for offset, col_key in enumerate(self._extra_column_keys, start=1):
                col = offset

                if col_key == "email":
                    self.table.setItem(r, col, it_email)

                elif col_key == "username":
                    self.table.setItem(r, col, it_user)

                elif col_key == "status":
                    self.table.setItem(r, col, it_status)
                    self.table.setCellWidget(r, col, badge)

                elif col_key == "notes":
                    self.table.setItem(r, col, it_notes)

                elif col_key == "site_link":
                    url = (entry_full.get("site_link") or "").strip()

                    display_text = url

                    it_link = QTableWidgetItem(display_text)
                    it_link.setFlags(flags)

                    if url:
                        it_link.setToolTip(url)
                        it_link.setData(Qt.UserRole, url)

                    if deleted_font is not None:
                        it_link.setFont(deleted_font)
                        it_link.setForeground(deleted_brush)

                    self.table.setItem(r, col, it_link)

                elif col_key == "date_modified":
                    modified_raw = (
                        entry_full.get("modified_at")
                        or entry_full.get("date_modified")
                        or entry_full.get("updated_at")
                        or ""
                    )

                    text = format_datetime(modified_raw, format_str="%b %d, %Y")
                    it_mod = QTableWidgetItem(text)
                    it_mod.setFlags(flags)

                    if deleted_font is not None:
                        it_mod.setFont(deleted_font)
                        it_mod.setForeground(deleted_brush)

                    self.table.setItem(r, col, it_mod)

                elif col_key == "date_created":
                    created_raw = (
                        entry_full.get("date_created")
                        or ""
                    )

                    text = format_datetime(created_raw, format_str="%b %d, %Y")
                    it_crd = QTableWidgetItem(text)
                    it_crd.setFlags(flags)

                    if deleted_font is not None:
                        it_crd.setFont(deleted_font)
                        it_crd.setForeground(deleted_brush)

                    self.table.setItem(r, col, it_crd)

                elif col_key == "category":
                    cat = (entry_full.get("category") or "").strip()

                    display_text = cat

                    it_cat = QTableWidgetItem(display_text)
                    it_cat.setFlags(flags)

                    if deleted_font is not None:
                        it_cat.setFont(deleted_font)
                        it_cat.setForeground(deleted_brush)

                    self.table.setItem(r, col, it_cat)

                elif col_key == "tags":
                    tags = (entry_full.get("tags") or "").strip()

                    display_text = tags

                    it_tags = QTableWidgetItem(display_text)
                    it_tags.setFlags(flags)

                    if deleted_font is not None:
                        it_tags.setFont(deleted_font)
                        it_tags.setForeground(deleted_brush)

                    self.table.setItem(r, col, it_tags)

        self.table.setSortingEnabled(True)
        if prev_col >= 0:
            self.table.sortItems(prev_col, prev_order)
    
    def _load_extra_column_keys(self) -> list[str]:
        settings = getattr(self, "settings", None)
        if settings is None:
            return list(DEFAULT_EXTRA_COLUMNS)

        saved = settings.get("table_columns", None)

        if not saved:
            keys = list(DEFAULT_EXTRA_COLUMNS)
        else:
            if isinstance(saved, str):
                try:
                    saved = [s.strip() for s in saved.split(",") if s.strip()]
                except Exception:
                    saved = []

            if not isinstance(saved, (list, tuple)):
                saved = []

            keys = [k for k in saved if k in COLUMN_DEFS]

        if not keys:
            keys = list(DEFAULT_EXTRA_COLUMNS)

        keys = keys[:MAX_EXTRA_COLUMNS]
        return keys


    def _apply_table_headers(self) -> None:
        total_cols = 1 + len(self._extra_column_keys)
        self.table.setColumnCount(total_cols)

        headers = ["Site/Title"] + [COLUMN_DEFS[k] for k in self._extra_column_keys]
        self.table.setHorizontalHeaderLabels(headers)

    
    def _rebuild_table_columns_and_reload(self):
        settings = getattr(self, "settings", None)
        if settings is not None:
            settings.set("table_columns", self._extra_column_keys)

        total_cols = 1 + len(self._extra_column_keys)
        self.table.setColumnCount(total_cols)
        headers = ["Site/Title"] + [COLUMN_DEFS[k] for k in self._extra_column_keys]
        self.table.setHorizontalHeaderLabels(headers)

        self.adjust_table_columns()
        self.reload()
        try:
            self._save_column_order()
        except Exception:
            pass


    def reload(self):
        prev_ids = self._remember_selected_ids()

        try:
            db.check_and_expire_entries()
        except Exception:
            pass

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

        if prev_ids:
            self._select_rows_by_ids(prev_ids)
        elif rows:
            self.table.setCurrentCell(0, 0)


    def filter_table(self, text: str):
        all_flag = False
        raw = (text or "").strip()
        if not raw:
            prev = getattr(self, "_search_prev_category", None)

            if prev is not None:
                self.current_category = prev
                self._search_prev_category = None

                if hasattr(self, "_refresh_tree_and_table"):
                    self._refresh_tree_and_table(target_category=prev)
                    return
                
            try:
                self.tree.clearSelection()
            except Exception:
                pass

            self.reload()
            return

        if getattr(self, "_search_prev_category", None) is None:
            self._search_prev_category = getattr(self, "current_category", None)

        tokens = raw.split()
        status_from_query: str | None = None
        remaining_tokens: list[str] = []

        for t in tokens:
            tl = t.lower()
            if tl.startswith("is:"):
                val = tl[3:]
                if val in {"active", "archived", "deleted", "expired"}:
                    status_from_query = val
                    continue

                if val == "all":
                    all_flag = True
                    status_from_query = None
                    continue
            remaining_tokens.append(t)

        text = " ".join(remaining_tokens)

        status_filter: str | None = None
        category_filter: str | None = None

        if status_from_query is not None:
            status_filter = status_from_query

        if all_flag:
            status_filter = None
            category_filter = None

        cipher = getattr(self, "cipher", None)

        search_kwargs = {}
        if status_filter:
            search_kwargs["status"] = status_filter
        if category_filter:
            search_kwargs["category"] = category_filter

        if cipher:
            rows = db.search_entries(text or "", exclude_fields=("email",), **search_kwargs)
        else:
            rows = db.search_entries(text or "", **search_kwargs)

        if cipher and text:
            text_low = text.lower()
            present_ids = {int(r[0]) for r in rows}

            if status_filter:
                base_rows = db.fetch_by_status(status_filter)
            elif category_filter:
                base_rows = db.fetch_by_category(category_filter, include_descendants=False)
            else:
                base_rows = db.fetch_all()

            for r in base_rows:
                rid = int(r[0])
                if rid in present_ids:
                    continue

                entry_full = db.fetch_entry_dict(rid) or {}
                plain = db.decrypt_row_to_plain(entry_full, cipher)
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

        try:
            self.tree.clearSelection()
        except Exception:
            pass
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

        settings = getattr(self, "settings", None) or SettingsManager()
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
        view = self.table
        idx = view.indexAt(pos)
        if not idx.isValid():
            return

        sm = view.selectionModel()
        sm.setCurrentIndex(idx, QItemSelectionModel.NoUpdate | QItemSelectionModel.Rows)

        entry_id = self._get_selected_entry_id_from_table()
        if not entry_id:
            return

        entry = db.fetch_entry_dict(entry_id) or {}
        plain = db.decrypt_row_to_plain(entry, self.cipher)
        status = entry.get("status", "active")

        site = entry.get("site_link", "")
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

        menu = RoundedMenu(self)

        menu.addAction("Edit…", lambda: QTimer.singleShot(0, lambda: self.edit_single_entry(entry_id)))
        menu.addAction("Duplicate Entry",lambda: QTimer.singleShot(0, lambda: self._duplicate_single_entry(entry_id)))
        menu.addSeparator()

        def make_copy_action(label, value, entry_id):
            def _do():
                self._copy_to_clipboard(label, value)
                self._select_entry_by_id(entry_id)
            return _do
        
        a_site = menu.addAction("Copy Site", lambda: QTimer.singleShot(0, make_copy_action("site", site, entry_id)))
        a_site.setEnabled(bool(site))

        a_email = menu.addAction(
            "Copy Email",
            lambda: QTimer.singleShot(0, make_copy_action("email", email or plain.get("email", ""), entry_id))
        )
        a_email.setEnabled(bool(email or plain.get("email", "")))

        a_user = menu.addAction(
            "Copy Username",
            lambda: QTimer.singleShot(0, make_copy_action("username", username, entry_id))
        )
        a_user.setEnabled(bool(username))

        a_pwd = menu.addAction(
            "Copy Password",
            lambda: QTimer.singleShot(0, make_copy_action("password", password, entry_id))
        )
        a_pwd.setEnabled(bool(password) and bool(getattr(self, "cipher", None)))

        menu.addSeparator()

        a_pin = menu.addAction(
            "Copy PIN",
            lambda: QTimer.singleShot(0, make_copy_action("PIN", pin, entry_id))
        )
        a_pin.setEnabled(bool(pin) and bool(getattr(self, "cipher", None)))

        a_sec = menu.addAction(
            "Copy Security Code",
            lambda: QTimer.singleShot(0, make_copy_action("security code", sec_code, entry_id))
        )
        a_sec.setEnabled(bool(sec_code) and bool(getattr(self, "cipher", None)))

        a_app = menu.addAction(
            "Copy App Password",
            lambda: QTimer.singleShot(0, make_copy_action("app password", app_pass, entry_id))
        )
        a_app.setEnabled(bool(app_pass) and bool(getattr(self, "cipher", None)))

        a_totp = menu.addAction(
            "Copy TOTP Code",
            lambda: QTimer.singleShot(0, make_copy_action("TOTP code", totp_util.totp_from_uri_or_secret(otp_secret)[0], entry_id))
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
            menu.addAction("Delete (to Trash)", lambda: QTimer.singleShot(0, lambda: self._delete_single_entry(entry_id)))
        else:
            menu.addAction("Permanently Delete", lambda: QTimer.singleShot(0, lambda: self._permanently_delete_single_entry(entry_id)))

        menu.exec(self.table.viewport().mapToGlobal(pos))

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
        search_widget = getattr(self, "search", None)
        if search_widget is not None:
            text = (search_widget.text() or "").strip()
            if text:
                try:
                    self.filter_table(text)
                    return
                except Exception:
                    pass

        category = getattr(self, 'current_category', None)
        if not category:
            self.reload()
            return

        try:
            SPECIAL_DELETED  = TreeMixin.SPECIAL_DELETED
            SPECIAL_ARCHIVED = TreeMixin.SPECIAL_ARCHIVED
            SPECIAL_EXPIRED  = TreeMixin.SPECIAL_EXPIRED

            if category == SPECIAL_DELETED:
                self._load_special_folder_entries("deleted")
            elif category == SPECIAL_ARCHIVED:
                self._load_special_folder_entries("archived")
            elif category == SPECIAL_EXPIRED:
                self._load_special_folder_entries("expired")
            else:
                self.reload()
        except Exception:
            self.reload()
    
    def _load_special_folder_entries(self, status: str):
        try:
            rows = db.fetch_by_status(status)
            self._load_table(rows)
        except Exception:
            self._load_table([])

    def _permanently_delete_single_entry(self, entry_id: int):
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

    def _remember_selected_ids(self) -> list[int]:
        ids = []
        sm = self.table.selectionModel()
        if not sm:
            return ids
        for idx in sm.selectedRows():
            try:
                it0 = self.table.item(idx.row(), 0)
                val = it0.data(Qt.UserRole) if it0 else None
                if val is not None:
                    ids.append(int(val))
            except Exception:
                pass
        return ids

    def _select_rows_by_ids(self, ids: list[int]) -> None:
        if not ids:
            return
        sm = self.table.selectionModel()
        if not sm:
            return
        sm.clearSelection()
        first_row = None
        for r in range(self.table.rowCount()):
            it0 = self.table.item(r, 0)
            if not it0:
                continue
            try:
                val = it0.data(Qt.UserRole)
                if val is not None and int(val) in ids:
                    self.table.selectRow(r)
                    if first_row is None:
                        first_row = r
            except Exception:
                pass

        if first_row is not None:
            self.table.setCurrentCell(first_row, 0)

    def _select_entry_by_id(self, entry_id):
        view = self.table
        model = view.model()
        if model is None:
            return

        id_column = 0  

        for row in range(model.rowCount()):
            idx = model.index(row, id_column)
            if model.data(idx, Qt.UserRole) == entry_id:
                sm = view.selectionModel()
                sm.setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                view.scrollTo(idx)
                break
    
    def apply_table_prefs_from_settings(self):
        self._extra_column_keys = self._load_extra_column_keys()

        total_cols = 1 + len(self._extra_column_keys)
        self.table.setColumnCount(total_cols)
        headers = ["Site/Title"] + [COLUMN_DEFS[k] for k in self._extra_column_keys]
        self.table.setHorizontalHeaderLabels(headers)

        try:
            self._restore_column_order()
        except Exception:
            pass

        self.adjust_table_columns()
        self.reload()

    def open_column_settings(self):
        all_keys = list(COLUMN_DEFS.keys())

        dlg = ColumnSettingsDialog(self, all_keys, getattr(self, "_extra_column_keys", []))
        if dlg.exec() == QDialog.Accepted:
            new_keys = dlg.selected_keys()
            if not new_keys:
                new_keys = list(DEFAULT_EXTRA_COLUMNS)[:MAX_EXTRA_COLUMNS]
            self._extra_column_keys = new_keys
            self._rebuild_table_columns_and_reload()


class ColumnSettingsDialog(QDialog):
    def __init__(self, parent, all_keys: list[str], selected_keys: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Customize Columns")

        self._all_keys = all_keys
        self._selected_keys = set(selected_keys)

        layout = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setContentsMargins(10,5,10,15)
        layout.addLayout(grid)

        self.checkboxes: dict[str, QCheckBox] = {}

        cols = 3
        for i, key in enumerate(self._all_keys):
            label = COLUMN_DEFS[key]
            cb = QCheckBox(label)
            cb.setChecked(key in self._selected_keys)
            cb.toggled.connect(self._on_checkbox_toggled)

            row = i // cols
            col = i % cols
            grid.addWidget(cb, row, col)

            self.checkboxes[key] = cb

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(buttons)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        self.setFixedSize(self.sizeHint())

    def _on_checkbox_toggled(self, checked: bool):
        checked_keys = [k for k, cb in self.checkboxes.items() if cb.isChecked()]
        if len(checked_keys) > MAX_EXTRA_COLUMNS:
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.blockSignals(True)
                sender.setChecked(False)
                sender.blockSignals(False)

    def selected_keys(self) -> list[str]:
        keys = [k for k in self._all_keys if self.checkboxes[k].isChecked()]
        return keys[:MAX_EXTRA_COLUMNS]
