from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QDialogButtonBox, QPushButton, 
                               QApplication, QToolButton, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from ui import material_symbols as ms
from ui.entry_dialog_sections import (BasicInfoSection, AuthSection, RecoverySection, MetadataSection)
from pwGenerator.password_window import PasswordGeneratorDialog
from core.settings_manager import SettingsManager

class CollapsibleSection(QWidget):

    def __init__(self, title: str, content: QWidget, parent=None, expanded: bool = True):
        super().__init__(parent)
        self._content = content
        self._base_title = title
        self._summary = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header_btn = QToolButton(self)
        self._header_btn.setCheckable(True)
        self._header_btn.setChecked(expanded)
        self._header_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._header_btn.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self._header_btn.clicked.connect(self._on_toggled)
        self._header_btn.setStyleSheet(
            """
            QToolButton {
                font-weight: 600;
                padding: 6px 4px;
                border: 0;
                text-align: left;
            }
            """
        )

        # Card-like frame for content
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(30, 6, 10, 10)
        frame_layout.setSpacing(6)
        frame_layout.addWidget(content)

        layout.addWidget(self._header_btn)
        layout.addWidget(frame)

        frame.setVisible(expanded)
        self._frame = frame

        self._apply_header_text()

    def _on_toggled(self, checked: bool):
        self._frame.setVisible(checked)
        self._header_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._apply_header_text()

    def _apply_header_text(self):
        expanded = self._header_btn.isChecked()
        if expanded or not self._summary:
            text = self._base_title
        else:
            text = f"{self._base_title} - {self._summary}"
        self._header_btn.setText(text)

    def set_summary(self, summary: str | None):
        self._summary = (summary or "").strip()
        self._apply_header_text()

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
        self.resize(600, 484)

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

        main = QVBoxLayout(content)
        main.setSpacing(14)
        main.setContentsMargins(0, 0, 0, 0)

        self.basic_info = BasicInfoSection(self._entry, self._icon_family, parent=self)
        self.auth = AuthSection(self._entry, self._icon_family, parent=self)
        self.recovery = RecoverySection(self._entry, self._icon_family, parent=self)
        self.metadata = MetadataSection(self._entry, default_category, self._icon_family, parent=self)

        self.basic_section = CollapsibleSection("Basic Information", self.basic_info, expanded=True)
        main.addWidget(self.basic_section)

        main.addWidget(CollapsibleSection("Authentication", self.auth, expanded=True))
        main.addWidget(CollapsibleSection("Recovery / 2FA", self.recovery, expanded=False))
        main.addWidget(CollapsibleSection("Metadata", self.metadata, expanded=False))

        main.addStretch(1)

        self._setup_basic_info_header_summary()

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

    def _setup_basic_info_header_summary(self):
        if not self.basic_info or not hasattr(self, "basic_section"):
            return

        def update_summary():
            site = self.basic_info.site.text().strip()
            username = self.basic_info.username.text().strip()
            email = self.basic_info.email.text().strip()

            parts = [p for p in (site, username, email) if p]
            summary = " · ".join(parts)
            self.basic_section.set_summary(summary if parts else "")

        for field in (self.basic_info.site,
                      self.basic_info.username,
                      self.basic_info.email):
            field.textChanged.connect(lambda _=None, u=update_summary: u())

        update_summary()