from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame,
    QAbstractItemView, QSplitter, QLabel, QMessageBox, 
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from ui.widgets.button import FontIconButton

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class UIBuilder:
    
    def __init__(self, window: 'MainWindow'):
        self.window = window
    
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
        vault_menu.addAction(QAction("Lock Vault", self.window, 
                                     shortcut=QKeySequence("Ctrl+L"), 
                                     triggered=self.window.lock))

        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(QAction("Preferences", self.window, 
                                       triggered=self.window.open_settings_dialog))

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(QAction("About", self.window, triggered=self._show_about))
    
    def _show_about(self):
        QMessageBox.information(
            self.window, "About", 
            "Secure Password Manager\nBuilt with PySide6 and SQLite."
        )
    
    def build_shortcuts(self):
        QShortcut(QKeySequence("Alt+Z"), self.window, 
                 activated=lambda: self.window._copy_selected_field("email"))
        QShortcut(QKeySequence("Alt+X"), self.window, 
                 activated=lambda: self.window._copy_selected_field("username"))
        QShortcut(QKeySequence("Alt+C"), self.window, 
                 activated=lambda: self.window._copy_selected_field("password"))
        QShortcut(QKeySequence("Alt+A"), self.window, 
                 activated=lambda: self.window._copy_selected_field("app_password"))
    
    def build_central_widget(self):
        central = QWidget()
        self.window.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_top_bar(root)
        
        self._build_content_area(root)
        
        self.window.status_label = QLabel("")
        self.window.statusBar().addPermanentWidget(self.window.status_label)
    
    def _build_top_bar(self, parent_layout):
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        GAP = 4

        self.window.search = QLineEdit(placeholderText="Search...")
        self.window.search.setObjectName("topelements")

        self.window.add_btn  = FontIconButton("add",  tooltip="Add",  size=14, min_button_side=40,
                                            hover_enabled=False, border_enabled=False)
        self.window.edit_btn = FontIconButton("edit", tooltip="Edit", size=14, min_button_side=40,
                                            hover_enabled=False, border_enabled=False)

        self.window.copy_email_btn = FontIconButton("mail",           tooltip="Copy Email",    size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        self.window.copy_user_btn  = FontIconButton("person",         tooltip="Copy Username", size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        self.window.copy_pass_btn  = FontIconButton("key",            tooltip="Copy Password", size=14, min_button_side=40,
                                                    hover_enabled=False, border_enabled=False)
        
        self.window.archive_btn = FontIconButton("archive", tooltip="Archive", size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        self.window.expire_btn  = FontIconButton("timer",   tooltip="Expire",  size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)
        self.window.del_btn     = FontIconButton("delete",  tooltip="Delete",  size=14, min_button_side=40,
                                                hover_enabled=False, border_enabled=False)

        for btn in (
            self.window.add_btn, self.window.edit_btn,
            self.window.copy_email_btn, self.window.copy_user_btn, self.window.copy_pass_btn,
            self.window.archive_btn, self.window.expire_btn, self.window.del_btn
        ):
            btn.setStyleSheet("")
            btn.setObjectName("topelements")

        top.addWidget(self.window.search, 1)

        top.addSpacing(GAP)

        top.addWidget(self.window.add_btn)
        top.addWidget(self.window.edit_btn)

        top.addSpacing(GAP)

        top.addWidget(self.window.copy_email_btn)
        top.addWidget(self.window.copy_user_btn)
        top.addWidget(self.window.copy_pass_btn)

        top.addSpacing(GAP)

        top.addWidget(self.window.archive_btn)
        top.addWidget(self.window.expire_btn)
        top.addWidget(self.window.del_btn)

        parent_layout.addLayout(top)

        
    def _build_content_area(self, parent_layout):
        from core.styled_tree import StyledTreeWidget
        
        self.window.splitter_h = QSplitter(Qt.Horizontal)
        parent_layout.addWidget(self.window.splitter_h)

        self.window.tree = StyledTreeWidget(self.window)
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
        self.window.splitter_r.setStretchFactor(0, 1)
        self.window.splitter_r.setStretchFactor(1, 0)
    
    def _setup_table(self):
        self.window.setup_table()
        self.window.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.window.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.window.table.verticalHeader().setDefaultSectionSize(36)
        self.window.table.verticalHeader().setVisible(False)
        self.window.table.setWordWrap(True)
        self.window.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.window.splitter_r.addWidget(self.window.table)
    
    def wire_connections(self):
        self.window.add_btn.clicked.connect(self.window.add_entry)
        self.window.edit_btn.clicked.connect(self.window.edit_entry)
        self.window.del_btn.clicked.connect(self.window.delete_entry)
        self.window.archive_btn.clicked.connect(self.window._on_archive_clicked)
        self.window.expire_btn.clicked.connect(self.window._on_expire_clicked)

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
