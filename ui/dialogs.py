from PySide6.QtWidgets import ( QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QPushButton, QFileDialog, QHBoxLayout, 
                               QLabel, QMessageBox)

from pathlib import Path
from core.db_paths import DEFAULT_DB_DIR
from core import db, security
from ui.widgets.plusminus_spinbox import PlusMinusSpinBox
from core.settings_manager import SettingsManager
from ui.widgets.password_field import PasswordLineEdit

class DatabaseDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select or Create Database")
        layout = QFormLayout(self)
        layout.setVerticalSpacing(15)
        layout.setHorizontalSpacing(10)
        layout.setContentsMargins(30, 25, 30, 25)

        self.db_path = db.load_last_db()
        if self.db_path and not Path(self.db_path).exists():
            self.db_path = None
        db_name = self.db_path.stem if self.db_path else ""
        self.db_edit = QLineEdit(db_name)
        self.db_edit.setReadOnly(True)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self.db_btn_open = QPushButton("Open Database")
        self.db_btn_new = QPushButton("Create New Database")
        btn_layout.addWidget(self.db_btn_open)
        btn_layout.addWidget(self.db_btn_new)

        layout.addRow(QLabel("<b>Select or create a database:</b>"))
        layout.addRow("", self.db_edit)
        layout.addRow("", btn_layout)

        note = QLabel("Open an existing vault or Create a new one.")
        note.setObjectName("hint")
        layout.addRow("", note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)

        self.db_btn_open.clicked.connect(self.choose_existing_db)
        self.db_btn_new.clicked.connect(self.create_new_db)
        self.is_new_db = False

        self.setFixedSize(self.sizeHint())
        self.setSizeGripEnabled(False)

    def choose_existing_db(self):
        try:
            DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        start_dir = str(self.db_path.parent) if self.db_path else str(DEFAULT_DB_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Database", start_dir, "SQLite DB (*.db)"
        )
        if path:
            self.db_path = Path(path)
            db_name = self.db_path.stem
            self.db_edit.setText(db_name)
            db.set_db_path(self.db_path)
            db.init()
            db.save_last_db(self.db_path)
            self.is_new_db = not security.master_exists()

    def create_new_db(self):
        try:
            DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        start_dir = str(self.db_path.parent) if self.db_path else str(DEFAULT_DB_DIR)
        path, _ = QFileDialog.getSaveFileName(
            self, "Create New Database", str(Path(start_dir) / "new_vault.db"), "SQLite DB (*.db)"
        )
        if path:
            self.db_path = Path(path)
            db_name = self.db_path.stem
            self.db_edit.setText(db_name)
            db.set_db_path(self.db_path)
            db.init()
            db.save_last_db(self.db_path)
            self.is_new_db = True
            QMessageBox.information(
                self,
                "New Database Created",
                "A new database file has been created.\n"
                "You will now set a master password after selecting OK.",
            )
    
    def accept(self):
        if not getattr(self, 'db_path', None):
            QMessageBox.warning(self, 'Error', 'Create a database first.')
            return
        super().accept()

    def values(self):
        return str(self.db_path), self.is_new_db


class MasterDialog(QDialog):

    def __init__(self, setup: bool = False, parent=None, icon_family: str | None = None, settings: SettingsManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("Setup Master Password" if setup else "Unlock Vault")
        layout = QFormLayout(self)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        self.setup = setup

        if settings is not None:
            self.settings = settings
        elif hasattr(parent, "settings"):
            self.settings = parent.settings
        else:
            self.settings = SettingsManager()

        if not setup:
            self.p1 = PasswordLineEdit(
                placeholder="Master password",
                icon_family='Material Symbols Rounded',
                copy_enabled=False,
                strength_enabled=False,
                strength_alpha=0.0,
            )
            layout.addRow("Master password:", self.p1)

            self.p2 = PasswordLineEdit(
                placeholder="", icon_family='Material Symbols Rounded', copy_enabled=False,
                strength_enabled=False, strength_alpha=0.0,
            )
            self.p2.hide()
        else:
            self.p1 = PasswordLineEdit(
                placeholder="New master password",
                icon_family='Material Symbols Rounded',
                copy_enabled=False,
                strength_enabled=True,
                strength_alpha=0.12,
            )
            layout.addRow("Master password:", self.p1)

            self.p2 = PasswordLineEdit(
                placeholder="Confirm password",
                icon_family='Material Symbols Rounded',
                copy_enabled=False,
                strength_enabled=True,
                strength_alpha=0.12,
            )
            layout.addRow("Confirm password:", self.p2)

        self.auto = PlusMinusSpinBox()
        self.auto.setRange(0, 120)
        self.auto.setValue(self.settings.get("auto_lock_minutes", 10))
        self.auto.setObjectName("autoLockSpin")
        layout.addRow("Auto-lock:", self.auto)

        hint = QLabel("Enter your master password to unlock the vault.\nAutolock time is in minutes (0 to disable).")
        hint.setObjectName("hint")
        layout.addRow("", hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)

        self.setFixedSize(self.sizeHint())
        self.setSizeGripEnabled(False)

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
            self.settings.set("auto_lock_minutes", int(self.auto.value()))
        except Exception:
            pass

        self.accept()

    def values(self):
        return self.p1.text(), (self.p2.text() if self.setup else ""), self.auto.value()


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None, icon_family: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Change Master Password")

        layout = QFormLayout(self)
        layout.setVerticalSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        self.old_pw = PasswordLineEdit(
            placeholder="Current master password",
            icon_family='Material Symbols Rounded',
            copy_enabled=False,
            strength_enabled=False,
            strength_alpha=0.0,
        )
        layout.addRow("current Master password:", self.old_pw)

        self.new_pw = PasswordLineEdit(
            placeholder="New master password",
            icon_family='Material Symbols Rounded',
            copy_enabled=False,
            strength_enabled=True,
            strength_alpha=0.12,
        )
        layout.addRow("new Master password:", self.new_pw)

        self.conf_pw = PasswordLineEdit(
            placeholder="Confirm new master password",
            icon_family='Material Symbols Rounded',
            copy_enabled=False,
            strength_enabled=True,
            strength_alpha=0.12,
        )
        layout.addRow("confirm Master password:", self.conf_pw)

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