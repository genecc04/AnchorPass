from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, QDialogButtonBox, QPushButton, 
                               QApplication, QToolButton, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QFontDatabase
from ui import material_symbols as ms
from ui.entry_dialog_sections import (BasicInfoSection, AuthSection, RecoverySection, MetadataSection)
from pwGenerator.password_window import PasswordGeneratorDialog
from core.settings_manager import SettingsManager

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
        self._lock_dialog_size()

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

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

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
