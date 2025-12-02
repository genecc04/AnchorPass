from PySide6.QtWidgets import ( QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QFileDialog, 
QLabel, QMessageBox, QHBoxLayout, QWidget, QSpacerItem, QSizePolicy)
from pathlib import Path
from core.db_paths import DEFAULT_DB_DIR
from core import db, security
from core.settings_manager import SettingsManager
from ui.widgets.password_field import PasswordLineEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class DatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select or Create Vault")
        self.setFixedSize(400, 250)

        layout = QFormLayout(self)
        layout.setVerticalSpacing(8)
        layout.setHorizontalSpacing(10)
        layout.setContentsMargins(25, 20, 30, 15)

        self.db_path = db.load_last_db()
        if self.db_path and not Path(self.db_path).exists():
            self.db_path = None

        self.is_new_db = False
        if self.db_path:
            try:
                db.set_db_path(self.db_path)
                db.init()
                db.save_last_db(self.db_path)
                self.is_new_db = not security.master_exists()
            except Exception:
                self.db_path = None
                self.is_new_db = False

        db_name = self.db_path.stem if self.db_path else ""
        self.db_edit = ClickableLineEdit(db_name)
        self.db_edit.setReadOnly(True)
        self.db_edit.setCursor(Qt.PointingHandCursor)
        self.db_edit.setMinimumWidth(300)
        self.db_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if not self.db_path:
            self.db_edit.setPlaceholderText("Click to select a vault...")
        else:
            self.db_edit.setToolTip(
                "Click to select a vault...\n[Current] " + str(self.db_path)
            )

        self.warn = QLabel("<b>Select a Vault</b>")
        self.warn.setTextFormat(Qt.RichText)
        self.warn.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.warn.setOpenExternalLinks(False)
        self.warn.linkActivated.connect(lambda _: self.create_new_db())
        layout.addRow("", self.warn)
        layout.addItem(QSpacerItem(0, 18, QSizePolicy.Minimum, QSizePolicy.Fixed))
        layout.addRow("", self.db_edit)

        self.master_pw = PasswordLineEdit(
            placeholder="Master password",
            icon_family="Material Symbols Rounded",
            copy_enabled=False,
            strength_enabled=False,
            strength_alpha=0.0,
        )
        self.master_pw.setObjectName("masterPassword")
        self.master_pw.setMinimumWidth(300)
        self.master_pw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.master_pw.setVisible(False)
        layout.addRow("", self.master_pw)


        buttons = QDialogButtonBox()
        self.btn_open = buttons.addButton("Login", QDialogButtonBox.AcceptRole)
        self.btn_open.setDefault(True)
        self.btn_open.setAutoDefault(True)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 20, 0, 0)
        btn_row.addStretch()
        btn_row.addWidget(buttons)
        btn_row.addStretch()

        btn_container = QWidget()
        btn_container.setLayout(btn_row)
        layout.addRow("", btn_container)

        note = QLabel(
            "Don't have a vault? "
            "<a href='#create' style='color:#4ea1ff; text-decoration:none;'>Create a vault</a>."
        )
        note.setObjectName("hint")
        note.setTextFormat(Qt.RichText)
        note.setTextInteractionFlags(Qt.TextBrowserInteraction)
        note.setOpenExternalLinks(False)
        note.linkActivated.connect(lambda _: self.create_new_db())

        note_row = QHBoxLayout()
        note_row.setContentsMargins(0, 4, 0, 0)
        note_row.addStretch()
        note_row.addWidget(note)
        note_row.addStretch()

        note_container = QWidget()
        note_container.setLayout(note_row)
        layout.addRow("", note_container)

        self.db_edit.clicked.connect(self.choose_existing_db)
        self.btn_open.clicked.connect(self.accept)
        self._reset_password_state()

    def _reset_password_state(self):
        self._verified_password = ""
        self.master_pw.clear()
        self._update_password_field_visibility()

    def _update_password_field_visibility(self):
        if not self.db_path:
            self.setWindowTitle("AnchorPass: Create a Vault")
            self.warn.setText("There is no Vault selected please <b><a href='#create' style='color:#4ea1ff; text-decoration:none;'>Create a vault</a>.</b>")
        elif self.is_new_db:
            self.setWindowTitle("AnchorPass: Set a Masterpassword")
            self.warn.setText("Login to <b>set a Masterpassword:</b>")
        else:
            self.setWindowTitle("AnchorPass: Login")
            self.warn.setText("<b>Select a vault:</b>")

        show = bool(self.db_path) and not getattr(self, "is_new_db", False)
        self.master_pw.setVisible(show)
        if show and not self.master_pw.text():
            self.master_pw.setFocus()

    def choose_existing_db(self):
        try:
            DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        start_dir = str(self.db_path.parent) if self.db_path else str(DEFAULT_DB_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Database", start_dir, "SQLite DB (*.db)"
        )
        if not path:
            return

        self.db_path = Path(path)
        self.db_edit.setText(self.db_path.stem)
        self.db_edit.setToolTip(str(self.db_path))
        self.db_edit.setPlaceholderText("")

        db.set_db_path(self.db_path)
        db.init()
        db.save_last_db(self.db_path)
        self.is_new_db = not security.master_exists()

        self._reset_password_state()

    def create_new_db(self):
        try:
            DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        start_dir = str(self.db_path.parent) if self.db_path else str(DEFAULT_DB_DIR)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            str(Path(start_dir) / "new_vault.db"),
            "SQLite DB (*.db)",
        )

        if not path:
            return

        self.db_path = Path(path)
        self.db_edit.setText(self.db_path.stem)
        self.db_edit.setToolTip(str(self.db_path))
        self.db_edit.setPlaceholderText("")
        db.set_db_path(self.db_path)
        db.init()
        db.save_last_db(self.db_path)
        self.is_new_db = True

        self._reset_password_state()

        QMessageBox.information(
            self,
            "New Database Created",
            "A new database file has been created.\n"
            "You will now set a master password after selecting Login.",
        )

    def accept(self):
        if not getattr(self, "db_path", None):
            QMessageBox.warning(self, "Error", "Create a database first.")
            return

        if not getattr(self, "is_new_db", False):
            password = self.master_pw.text().strip()
            if not password:
                QMessageBox.warning(self, "Error", "Please enter your master password.")
                self.master_pw.setFocus()
                return

            try:
                db.set_db_path(self.db_path)
                db.init()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to open database:\n{exc}")
                return

            if not security.verify_master(password):
                QMessageBox.critical(self, "Error", "Incorrect master password.")
                self.master_pw.selectAll()
                self.master_pw.setFocus()
                return

            self._verified_password = password

        super().accept()

    def values(self):
        inline_password = getattr(self, "_verified_password", "")
        return str(self.db_path), self.is_new_db, inline_password


class MasterDialog(QDialog):
    def __init__(
        self,
        setup: bool = False,
        parent=None,
        icon_family: str | None = None,
        settings: SettingsManager | None = None,
    ):
        super().__init__(parent)
        self.setup = setup
        self.setFixedSize(400, 250)

        if settings is not None:
            self.settings = settings
        elif hasattr(parent, "settings"):
            self.settings = parent.settings
        else:
            self.settings = SettingsManager()

        self.db_name = self.settings._db_path.stem if self.settings._db_path else ""

        self.setWindowTitle(
            ("Setup Master Password: " if setup else "Unlock Vault: ") + self.db_name
        )

        layout = QFormLayout(self)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel("Setup Master Password" if setup else "Unlock Vault")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        layout.addRow("", title)

        if setup:
            self.p1 = PasswordLineEdit(
                placeholder="New master password",
                icon_family="Material Symbols Rounded",
                copy_enabled=False,
                strength_enabled=True,
                strength_alpha=0.12,
            )
            layout.addRow(self.p1)

            self.p2 = PasswordLineEdit(
                placeholder="Confirm password",
                icon_family="Material Symbols Rounded",
                copy_enabled=False,
                strength_enabled=True,
                strength_alpha=0.12,
            )
            layout.addRow(self.p2)
        else:
            self.p1 = PasswordLineEdit(
                placeholder="Master password",
                icon_family="Material Symbols Rounded",
                copy_enabled=False,
                strength_enabled=False,
                strength_alpha=0.0,
            )
            layout.addRow(self.p1)
            self.p2 = None

        hint_text = (
            "Please don't forget your master password"
            if setup
            else "Please enter your master password."
        )
        hint = QLabel(hint_text)
        hint.setObjectName("hint")
        layout.addRow("", hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)

        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Back")

    def validate(self):
        if self.setup:
            if not self.p1.text() or not self.p2.text():
                QMessageBox.warning(self, "Error", "Please fill out both password fields.")
                return
            if self.p1.text() != self.p2.text():
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return
        elif not self.p1.text():
            QMessageBox.warning(self, "Error", "Please enter your master password.")
            return

        try:
            self.settings.set("auto_lock_minutes", 10)
        except Exception:
            pass

        self.accept()

    def values(self):
        return (
            self.p1.text(),
            self.p2.text() if self.setup and self.p2 is not None else "",
            self.settings.set("auto_lock_minutes", 10),
        )


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None, icon_family: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Change Master Password")

        layout = QFormLayout(self)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        title = QLabel("Change Master Password")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        layout.addRow("", title)

        self.old_pw = PasswordLineEdit(
            placeholder="Current master password",
            icon_family="Material Symbols Rounded",
            copy_enabled=False,
            strength_enabled=False,
            strength_alpha=0.0,
        )
        layout.addRow("Current:", self.old_pw)

        self.new_pw = PasswordLineEdit(
            placeholder="New master password",
            icon_family="Material Symbols Rounded",
            copy_enabled=False,
            strength_enabled=True,
            strength_alpha=0.12,
        )
        layout.addRow("New:", self.new_pw)

        self.conf_pw = PasswordLineEdit(
            placeholder="Confirm new master password",
            icon_family="Material Symbols Rounded",
            copy_enabled=False,
            strength_enabled=True,
            strength_alpha=0.12,
        )
        layout.addRow("Confirm:", self.conf_pw)

        hint = QLabel(
            "Please don't forget your master password, it's the key to your vault."
        )
        hint.setObjectName("hint")
        layout.addRow("", hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setFixedSize(self.sizeHint())
        self.setSizeGripEnabled(False)

    def validate(self):
        if not self.old_pw.text() or not self.new_pw.text() or not self.conf_pw.text():
            QMessageBox.warning(self, "Error", "Please fill out all fields.")
            return
        if self.new_pw.text() != self.conf_pw.text():
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return
        self.accept()

    def values(self):
        return self.old_pw.text(), self.new_pw.text()

class ClickableLineEdit(QLineEdit):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)