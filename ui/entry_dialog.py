from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, QDialogButtonBox, QPushButton,
QApplication, QToolButton, QFrame, QSizePolicy,
QTabWidget, QTableWidget, QTableWidgetItem, QLabel, QHBoxLayout)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QFontDatabase
from ui import material_symbols as ms
from ui.entry_dialog_sections import (BasicInfoSection, AuthSection, RecoverySection, MetadataSection)
from pwGenerator.password_window import PasswordGeneratorDialog
from core.settings_manager import SettingsManager

from core import db

class CollapsibleSection(QWidget):

    def __init__(self, title: str, content: QWidget, parent=None, expanded: bool = True, collapsible: bool = True):
        super().__init__(parent)
        self._content = content
        self._base_title = title
        self._summary = ""
        self._collapsible = collapsible

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(0)

        self._header_btn = QToolButton(self)
        self._header_btn.setObjectName("SectionHeaderButton")
        self._header_btn.setCheckable(collapsible)
        self._header_btn.setChecked(expanded or not collapsible)
        self._header_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._header_btn.setArrowType(Qt.DownArrow if expanded or not collapsible else Qt.RightArrow)

        if collapsible:
            self._header_btn.clicked.connect(self._on_toggled)

        self._header_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._header_btn)

        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(15, 5, 10, 10)
        frame_layout.setSpacing(6)
        frame_layout.addWidget(content)

        layout.addWidget(frame)

        frame.setVisible(expanded or not collapsible)
        self._frame = frame
        self._install_focus_tracking(content)
        self._apply_header_text()

    def _install_focus_tracking(self, root: QWidget):
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn or event.type() == QEvent.FocusOut:
            QTimer.singleShot(0, self._update_section_focus_from_current)
        return super().eventFilter(obj, event)

    def _update_section_focus_from_current(self):
        try:
            fw = QApplication.focusWidget()
            has_focus = fw is not None and self.isAncestorOf(fw)
            self._set_section_focused(has_focus)
        except RuntimeError:
            pass

    def _set_section_focused(self, focused: bool):
        self._header_btn.setProperty("sectionFocused", focused)
        self._header_btn.style().unpolish(self._header_btn)
        self._header_btn.style().polish(self._header_btn)
        self._header_btn.update()

    def _on_toggled(self, checked: bool):
        if not self._collapsible:
            self._header_btn.setChecked(True)
            return
        
        self._frame.setVisible(checked)
        self._header_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._apply_header_text()

    def _apply_header_text(self):
        self._header_btn.setText(self._base_title)

    def set_header_text(self, text: str):
        self._base_title = text
        self._apply_header_text()


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry: dict | None = None, 
                 default_category: str | None = None, icon_family: str | None = None, settings: SettingsManager | None = None):
        self._entry = entry or {}
        self._last_focus_widget = None
        self.basic_info = None
        self.auth = None
        self.recovery = None
        self.metadata = None
        self._icon_family = icon_family
        self._have_icons_family = False
        
        self.settings = settings
        if self.settings is None and parent is not None and hasattr(parent, "settings"):
            self.settings = parent.settings

        super().__init__(parent)

        self.setWindowTitle("Edit Entry" if entry else "Add Entry")

        self._icon_family = (
            icon_family or 
            QApplication.instance().property("materialSymbols.family") or
            getattr(ms, "family", lambda: None)()
        )
        self._have_icons_family = bool(
            self._icon_family and self._icon_family in QFontDatabase().families()
        )

        self._build_ui(default_category)
        self._finalize_initial_size()
        #self._lock_dialog_size()

    def _finalize_initial_size(self):
        auth_section = self.auth

        if auth_section is not None and hasattr(auth_section, "_set_advanced_visible"):
            auth_section._set_advanced_visible(True)

        self.adjustSize()
        full_size = self.sizeHint()

        full_size.setWidth(max(full_size.width(), 500))
        full_size.setHeight(max(full_size.height(), 450))

        self.resize(full_size)
        self.setMinimumSize(full_size)

    def _lock_dialog_size(self):
        self.setSizeGripEnabled(False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)

    def _build_ui(self, default_category: str | None):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        tabs = QTabWidget(self)
        tabs.setObjectName("EntryTabs")
        root.addWidget(tabs)

        # ----------------- Tab 1: existing details UI -------------------
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0)

        scroll = QScrollArea(details_tab)
        scroll.setWidgetResizable(True)
        details_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        main = QVBoxLayout(content)
        main.setSpacing(5)
        main.setContentsMargins(0, 0, 0, 0)

        self.basic_info = BasicInfoSection(self._entry, self._icon_family, parent=self)
        self.auth = AuthSection(self._entry, self._icon_family, parent=self)
        self.recovery = RecoverySection(self._entry, self._icon_family, parent=self)
        self.metadata = MetadataSection(self._entry, default_category, self._icon_family, parent=self)

        self.basic_section = CollapsibleSection("Basic Information", self.basic_info, expanded=True, collapsible=False)
        main.addWidget(self.basic_section)

        main.addWidget(CollapsibleSection("More Authentication Options", self.auth, expanded=False))
        main.addWidget(CollapsibleSection("Recovery / 2FA", self.recovery, expanded=False))
        main.addWidget(CollapsibleSection("Metadata", self.metadata, expanded=False))

        main.addStretch(1)

        tabs.addTab(details_tab, "Details")

        # ----------------- Tab 2: history UI ----------------------------
        self.history_tab = HistoryTab(self._entry.get("id"), parent=self)
        history_idx = tabs.addTab(self.history_tab, "History")

        if not self._entry.get("id"):
            tabs.setTabEnabled(history_idx, False)

        self._build_buttons(root)

    def _build_buttons(self, parent_layout):
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)

        self.btn_generate_password = QPushButton("Generate Password", self)
        btns.addButton(self.btn_generate_password, QDialogButtonBox.ActionRole)
        self.btn_generate_password.setFocusPolicy(Qt.NoFocus)
        self.btn_generate_password.pressed.connect(self._remember_focus)
        self.btn_generate_password.clicked.connect(self._open_password_generator)

        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        parent_layout.addWidget(btns)

    def _remember_focus(self):
        self._last_focus_widget = self.focusWidget()

    def _open_password_generator(self):
        targets = {
            "Password": self.basic_info.password.setText,
            "App Password": self.auth.app_password.setText,
        }
        
        w = self._last_focus_widget or self.focusWidget()
        initial = "App Password" if w == self.auth.app_password else "Password"

        dlg = PasswordGeneratorDialog(
            parent=self,
            targets=targets,
            initial_target=initial,
            icon_family=self._icon_family,
            settings=self.settings
        )
        dlg.exec()
        self._last_focus_widget = None

    def values(self) -> dict:
        data = {}
        data.update(self.basic_info.values())
        data.update(self.auth.values())
        data.update(self.recovery.values())
        data.update(self.metadata.values())
        return data

    def closeEvent(self, ev):
        if self.recovery:
            self.recovery.cleanup()
        super().closeEvent(ev)

    def changeEvent(self, ev):
        if self.recovery:
            self.recovery.handle_theme_change(ev)
        super().changeEvent(ev)

    def reload_details_from_db(self):
        """Reload the Details tab from the database after a restore."""
        entry_id = self._entry.get("id")
        if not entry_id:
            return

        parent = self.parent()
        cipher = getattr(parent, "cipher", None) if parent is not None else None
        if cipher is None:
            return

        row = db.fetch_entry_dict(int(entry_id)) or {}
        if not row:
            return

        try:
            plain = db.decrypt_row_to_plain(row, cipher) or {}
        except Exception:
            return

        plain["id"] = entry_id
        plain["expiry_date"] = row.get("expiry_date")
        plain["status"] = row.get("status", "active")

        self._entry = plain

        if self.basic_info is not None:
            self.basic_info.load_plain(plain)
        if self.auth is not None:
            self.auth.load_plain(plain)
        if self.recovery is not None:
            self.recovery.load_plain(plain)
        if self.metadata is not None:
            self.metadata.load_plain(plain)

class HistoryTab(QWidget):
    """
    Tab that shows history rows for a password entry.
    It calls functions that we'll add in core.db:
        - db.fetch_entry_history(entry_id)
        - db.restore_entry_from_history(entry_id, history_id)
        - db.delete_entry_history(history_id)
    """

    def __init__(self, entry_id: int | None, parent=None):
        super().__init__(parent)
        self._entry_id = entry_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.info_label = QLabel(self)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Changed at", "Changed by", "Summary"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_restore = QPushButton("Restore", self)
        self.btn_delete = QPushButton("Delete history row", self)
        btn_row.addWidget(self.btn_restore)
        btn_row.addWidget(self.btn_delete)
        layout.addLayout(btn_row)

        self.btn_restore.clicked.connect(self._on_restore_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.reload()

    # --- public API -------------------------------------------------

    def reload(self):
        """Reload history rows from the database."""
        self.table.setRowCount(0)

        if not self._entry_id:
            self.info_label.setText("Save this entry first to see its history.")
            return

        rows = []
        try:
            # this will come from db_ops, exported via core.db (see section 2)
            if hasattr(db, "fetch_entry_history"):
                rows = db.fetch_entry_history(self._entry_id) or []
        except Exception:
            rows = []

        if not rows:
            self.info_label.setText("No history recorded for this entry yet.")
            return

        self.info_label.setText("")
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            hid = row.get("id") or row.get("history_id") or ""
            when = row.get("changed_at") or row.get("snapshot_at") or ""
            who = row.get("changed_by") or ""
            summary = row.get("summary") or ""

            self.table.setItem(r, 0, QTableWidgetItem(str(hid)))
            self.table.setItem(r, 1, QTableWidgetItem(str(when)))
            self.table.setItem(r, 2, QTableWidgetItem(str(who)))
            self.table.setItem(r, 3, QTableWidgetItem(str(summary)))

    # --- helpers ----------------------------------------------------

    def _selected_history_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _on_restore_clicked(self):
        hid = self._selected_history_id()
        if not hid:
            return
        try:
            if hasattr(db, "restore_entry_from_history"):
                db.restore_entry_from_history(self._entry_id, hid)
        except Exception:
            pass
        self.reload()

        dialog = self.window()
        if dialog is not None and hasattr(dialog, "reload_details_from_db"):
            dialog.reload_details_from_db()

    def _on_delete_clicked(self):
        hid = self._selected_history_id()
        if not hid:
            return
        try:
            if hasattr(db, "delete_entry_history"):
                db.delete_entry_history(hid)
        except Exception:
            pass
        self.reload()
