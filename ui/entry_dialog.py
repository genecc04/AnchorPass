from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QDialogButtonBox, QPushButton, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from ui import material_symbols as ms
from ui.entry_dialog_sections import (BasicInfoSection, AuthSection, RecoverySection, MetadataSection)
from pwGenerator.password_window import PasswordGeneratorDialog

class EntryDialog(QDialog):
    def __init__(self, parent=None, entry: dict | None = None, 
                 default_category: str | None = None, icon_family: str | None = None):
        self._entry = entry or {}
        self._last_focus_widget = None
        self.basic_info = None
        self.auth = None
        self.recovery = None
        self.metadata = None
        self._icon_family = icon_family
        self._have_icons_family = False
        
        super().__init__(parent)

        self.setWindowTitle("Edit Entry" if entry else "Add Entry")
        self.resize(900, 700)

        self._icon_family = (
            icon_family or 
            QApplication.instance().property("materialSymbols.family") or
            getattr(ms, "family", lambda: None)()
        )
        self._have_icons_family = bool(
            self._icon_family and self._icon_family in QFontDatabase().families()
        )

        self._lock_dialog_size()

        self._build_ui(default_category)

    def _lock_dialog_size(self):
        self.adjustSize()
        self.setFixedSize(self.size())
        self.setSizeGripEnabled(False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)

    def _build_ui(self, default_category: str | None):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        cols = QHBoxLayout(content)
        cols.setSpacing(24)
        cols.setContentsMargins(0, 0, 0, 0)

        col_left = QVBoxLayout()
        col_left.setSpacing(14)
        col_right = QVBoxLayout()
        col_right.setSpacing(14)

        cols.addLayout(col_left, 1)
        cols.addLayout(col_right, 1)

        self.basic_info = BasicInfoSection(self._entry, self._icon_family)
        self.auth = AuthSection(self._entry, self._icon_family)
        self.recovery = RecoverySection(self._entry, self._icon_family)
        self.metadata = MetadataSection(self._entry, default_category, self._icon_family)

        col_left.addWidget(self.basic_info)
        col_left.addWidget(self.auth)
        col_left.addStretch(1)

        col_right.addWidget(self.recovery)
        col_right.addWidget(self.metadata)
        col_right.addStretch(1)

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
            "Password": self.auth.password.setText,
            "App Password": self.auth.app_password.setText,
        }
        
        w = self._last_focus_widget or self.focusWidget()
        initial = "App Password" if w == self.auth.app_password else "Password"

        dlg = PasswordGeneratorDialog(
            parent=self,
            targets=targets,
            initial_target=initial,
            icon_family=self._icon_family
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