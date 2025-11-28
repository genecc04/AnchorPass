from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QAbstractItemView, QSplitter, QLabel, QMessageBox, QDialog, QDialogButtonBox, QTextBrowser
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from ui.widgets.button import FontIconButton
from core.settings_manager import SettingsManager
from ui.mixins.tree_mixin import CategoryTreeWidget 
from pathlib import Path

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class UIBuilder:
    
    def __init__(self, window: 'MainWindow'):
        self.window = window

    def _get_settings(self) -> SettingsManager:
        s = getattr(self.window, "settings", None)
        if isinstance(s, SettingsManager):
            return s
        return SettingsManager()
    
    def build_menus(self):
        menubar = self.window.menuBar()
        menubar.setNativeMenuBar(False)
        menubar.setObjectName("AppMenuBar")

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(QAction("Change Database", self.window, 
                                    triggered=self.window.change_database))
        file_menu.addAction(QAction("Backup now", self.window, 
                                    triggered=lambda: self.window.export_backup(reason="manual")))
        file_menu.addAction(QAction("Open Backup Folder…", self.window, 
                                    triggered=self.window._open_backup_folder))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Exit", self.window, triggered=self.window.close))

        vault_menu = menubar.addMenu("&Vault")

        self.window.lock_action = QAction("Lock Vault", self.window,
                                        triggered=self.window.lock)
        
        vault_menu.addAction(self.window.lock_action)

        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(QAction("Preferences", self.window, 
                                       triggered=self.window.open_settings_dialog))

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(QAction("About", self.window, triggered=self._show_about))
        help_menu.addSeparator()
        help_menu.addAction(QAction("License", self.window,
                                    triggered=self._show_license))
        help_menu.addAction(QAction("Third-Party Notices", self.window,
                                    triggered=self._show_third_party_notices))
    
    def build_shortcuts(self):
        settings = self._get_settings()

        if hasattr(self.window, "_shortcuts"):
            for sc in self.window._shortcuts:
                sc.setParent(None)
            self.window._shortcuts.clear()
        else:
            self.window._shortcuts = []

        if not settings.get("hotkeys_enabled", True):
            if hasattr(self.window, "lock_action"):
                self.window.lock_action.setShortcut(QKeySequence())
            return

        def _seq(setting_key: str, default: str) -> QKeySequence | None:
            s = (settings.get(setting_key, default) or "").strip()
            if not s:
                return None
            return QKeySequence(s)

        def _add_copy_shortcut(setting_key: str, default: str, field: str):
            seq = _seq(setting_key, default)
            if not seq:
                return
            sc = QShortcut(seq, self.window)
            sc.activated.connect(lambda f=field: self.window._copy_selected_field(f))
            self.window._shortcuts.append(sc)

        def _add_action_shortcut(setting_key: str, default: str, handler):
            if handler is None:
                return
            seq = _seq(setting_key, default)
            if not seq:
                return
            sc = QShortcut(seq, self.window)
            sc.activated.connect(handler)
            self.window._shortcuts.append(sc)

        # Copy field shortcuts
        _add_copy_shortcut("hotkey_copy_site",           "",      "site_link")
        _add_copy_shortcut("hotkey_copy_email",          "Alt+Q", "email")
        _add_copy_shortcut("hotkey_copy_username",       "Alt+W", "username")
        _add_copy_shortcut("hotkey_copy_password",       "Alt+Z", "password")
        _add_copy_shortcut("hotkey_copy_app_password",   "Alt+X", "app_password")
        _add_copy_shortcut("hotkey_copy_security_code",  "",      "security_code")

        # TOTP uses its own helper, *not* _copy_selected_field
        _add_action_shortcut("hotkey_copy_totp", "", self.window._copy_totp_for_selection)

        # Entry action shortcuts
        _add_action_shortcut("hotkey_add_entry",       "", getattr(self.window, "add_entry", None))
        _add_action_shortcut("hotkey_edit_entry",      "", getattr(self.window, "edit_entry", None))
        _add_action_shortcut("hotkey_duplicate_entry", "", getattr(self.window, "duplicate_entry", None))
        _add_action_shortcut("hotkey_archive_entry",   "", getattr(self.window, "_on_archive_clicked", None))
        _add_action_shortcut("hotkey_expire_entry",    "", getattr(self.window, "_on_expire_clicked", None))
        _add_action_shortcut("hotkey_delete_entry",    "", getattr(self.window, "delete_entry", None))

        # Lock vault
        if hasattr(self.window, "lock_action"):
            seq = _seq("hotkey_lock_vault", "Ctrl+L")
            self.window.lock_action.setShortcut(seq or QKeySequence())
    
    def build_central_widget(self):
        central = QWidget()
        self.window.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        self._build_top_bar(root)
        
        self._build_content_area(root)
        
        self.window.status_label = QLabel("")
        self.window.statusBar().addPermanentWidget(self.window.status_label)
    
    def _build_top_bar(self, parent_layout):
        top_bar = QWidget()
        top_bar.setFixedHeight(35) 
        top_bar.setObjectName("TopBar")
        top = QHBoxLayout(top_bar)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        GAP = 4

        self.window.search = QLineEdit(placeholderText="Search...")
        self.window.search.setObjectName("topelements")
        self.window.search.installEventFilter(self.window)

        self.window.add_btn  = FontIconButton("add",  tooltip="Add",  size=14, min_button_side=40,
                                            hover_enabled=False, border_enabled=False)
        self.window.duplicate_btn = FontIconButton("content_copy", tooltip="Duplicate", size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        self.window.edit_btn = FontIconButton("edit", tooltip="Edit", size=14, min_button_side=40,
                                            hover_enabled=False, border_enabled=False)

        self.window.copy_email_btn = FontIconButton("mail",   tooltip="Copy Email",    size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        self.window.copy_user_btn  = FontIconButton("person", tooltip="Copy Username", size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        self.window.copy_pass_btn  = FontIconButton("key",    tooltip="Copy Password", size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        
        self.window.archive_btn = FontIconButton("archive", tooltip="Archive", size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        self.window.expire_btn  = FontIconButton("timer",   tooltip="Expire",  size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        self.window.del_btn     = FontIconButton("delete",  tooltip="Delete",  size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        
        self.window.columns_btn = FontIconButton("Settings", tooltip="Customize Columns", size=14, min_button_side=40, 
                                                 hover_enabled=False, border_enabled=False,)

        for btn in (
            self.window.add_btn, self.window.duplicate_btn, self.window.edit_btn,
            self.window.copy_email_btn, self.window.copy_user_btn, self.window.copy_pass_btn,
            self.window.archive_btn, self.window.expire_btn, self.window.del_btn, self.window.columns_btn
        ):
            btn.setStyleSheet("")
            btn.setObjectName("topelements")

        top.addWidget(self.window.search, 1)

        top.addSpacing(GAP)

        top.addWidget(self.window.add_btn)
        top.addWidget(self.window.duplicate_btn)
        top.addWidget(self.window.edit_btn)

        top.addSpacing(GAP)

        top.addWidget(self.window.copy_email_btn)
        top.addWidget(self.window.copy_user_btn)
        top.addWidget(self.window.copy_pass_btn)

        top.addSpacing(GAP)

        top.addWidget(self.window.archive_btn)
        top.addWidget(self.window.expire_btn)
        top.addWidget(self.window.del_btn)

        top.addSpacing(GAP)

        top.addWidget(self.window.columns_btn)
        parent_layout.addWidget(top_bar)

        
    def _build_content_area(self, parent_layout):

        self.window.splitter_h = QSplitter(Qt.Horizontal)
        parent_layout.addWidget(self.window.splitter_h)

        self.window.tree = CategoryTreeWidget(self.window)
        self.window.tree.setHeaderHidden(True)
        self.window.tree.setMaximumWidth(320)
        self.window.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.window.tree.customContextMenuRequested.connect(self.window.show_tree_menu)
        self.window.splitter_h.addWidget(self.window.tree)

        self.window.splitter_r = QSplitter(Qt.Vertical)
        self.window.splitter_r.setChildrenCollapsible(False)
        self.window.splitter_h.addWidget(self.window.splitter_r)

        self._setup_table()
        
        if hasattr(self.window, "_init_preview_pane"):
            self.window._init_preview_pane(self.window.splitter_r)

        self.window.splitter_h.setStretchFactor(0, 0)
        self.window.splitter_h.setStretchFactor(1, 1)
        self.window.splitter_h.setSizes([240, 760])

        self.window.splitter_r.setStretchFactor(0, 1)
        self.window.splitter_r.setStretchFactor(1, 0)
    
    def _setup_table(self):
        self.window.setup_table()
        table = self.window.table

        vh = table.verticalHeader()
        vh.setDefaultSectionSize(36)
        vh.setVisible(False)

        table.setWordWrap(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.window.splitter_r.addWidget(table)
    
    def wire_connections(self):
        self.window.add_btn.clicked.connect(self.window.add_entry)
        self.window.duplicate_btn.clicked.connect(self.window.duplicate_entry)
        self.window.edit_btn.clicked.connect(self.window.edit_entry)
        self.window.del_btn.clicked.connect(self.window.delete_entry)
        self.window.archive_btn.clicked.connect(self.window._on_archive_clicked)
        self.window.expire_btn.clicked.connect(self.window._on_expire_clicked)
        self.window.columns_btn.clicked.connect(self.window.open_column_settings)

        self.window.copy_email_btn.clicked.connect(lambda: self.window._copy_selected_field("email"))
        self.window.copy_user_btn.clicked.connect(lambda: self.window._copy_selected_field("username"))
        self.window.copy_pass_btn.clicked.connect(lambda: self.window._copy_selected_field("password"))

        self.window.search.textChanged.connect(self.window.filter_table)
        self.window.tree.itemClicked.connect(self.window.filter_by_category)

        try:
            self.window.table.selectionModel().selectionChanged.connect(
                self.window._update_actions_for_selection)
            self.window.table.itemSelectionChanged.connect(
                self.window.update_preview_for_selection)
        except Exception:
            pass

    def _show_about(self):
        settings = self._get_settings()

        hk_copy_site      = settings.get("hotkey_copy_site", "None")
        hk_copy_totp      = settings.get("hotkey_copy_totp", "None")
        hk_copy_sec       = settings.get("hotkey_copy_security_code", "None")
        hk_copy_email     = settings.get("hotkey_copy_email", "None")
        hk_copy_username  = settings.get("hotkey_copy_username", "None")
        hk_copy_password  = settings.get("hotkey_copy_password", "None")
        hk_copy_app_pass  = settings.get("hotkey_copy_app_password", "None")

        hk_add_entry      = settings.get("hotkey_add_entry", "None")
        hk_edit_entry     = settings.get("hotkey_edit_entry", "None")
        hk_duplicate      = settings.get("hotkey_duplicate_entry", "None")
        hk_archive        = settings.get("hotkey_archive_entry", "None")
        hk_expire         = settings.get("hotkey_expire_entry", "None")
        hk_delete         = settings.get("hotkey_delete_entry", "None")
        hk_lock           = settings.get("hotkey_lock_vault", "None")

        text = f"""
        <b>AnchorPass</b><br>
        Built with PySide6 and SQLite.<br><br><br>

        <b>Hotkeys</b><br>

        <table cellspacing="4" cellpadding="2">
        <tr>
            <td><b>Copy Site:</b></td><td>{hk_copy_site}</td>
            <td style="padding-left:20px;"><b>Add Entry:</b></td><td>{hk_add_entry}</td>
        </tr>
        <tr>
            <td><b>Copy TOTP:</b></td><td>{hk_copy_totp}</td>
            <td style="padding-left:20px;"><b>Edit Entry:</b></td><td>{hk_edit_entry}</td>
        </tr>
        <tr>
            <td><b>Copy Security Code:</b></td><td>{hk_copy_sec}</td>
            <td style="padding-left:20px;"><b>Duplicate Entry:</b></td><td>{hk_duplicate}</td>
        </tr>
        <tr>
            <td><b>Copy Email:</b></td><td>{hk_copy_email}</td>
            <td style="padding-left:20px;"><b>Archive:</b></td><td>{hk_archive}</td>
        </tr>
        <tr>
            <td><b>Copy Username:</b></td><td>{hk_copy_username}</td>
            <td style="padding-left:20px;"><b>Expire:</b></td><td>{hk_expire}</td>
        </tr>
        <tr>
            <td><b>Copy Password:</b></td><td>{hk_copy_password}</td>
            <td style="padding-left:20px;"><b>Delete:</b></td><td>{hk_delete}</td>
        </tr>
        <tr>
            <td><b>Copy App Password:</b></td><td>{hk_copy_app_pass}</td>
            <td style="padding-left:20px;"><b>Lock Vault:</b></td><td>{hk_lock}</td>
        </tr>
        </table>
        """

        QMessageBox.information(self.window, "About", text)

    def _show_text_file_dialog(self, title: str, filename: str):
        project_root = Path(__file__).resolve().parent.parent.parent
        path = project_root / filename

        if not path.exists():
            QMessageBox.warning(
                self.window,
                title,
                f"Could not find {filename} at:\n{path}"
            )
            return

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(
                self.window,
                title,
                f"Failed to read {filename}:\n{e}"
            )
            return

        dlg = QDialog(self.window)
        dlg.setWindowTitle(title)
        dlg.resize(700, 500)

        layout = QVBoxLayout(dlg)

        viewer = QTextBrowser(dlg)
        try:
            viewer.setMarkdown(text)
        except Exception:
            viewer.setPlainText(text)

        layout.addWidget(viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        dlg.exec()

    def _show_license(self):
        self._show_text_file_dialog("License", "license.md")

    def _show_third_party_notices(self):
        self._show_text_file_dialog("Third-Party Notices", "THIRD_PARTY_NOTICES.md")
