from PySide6.QtWidgets import ( QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox, QComboBox, QCheckBox, 
                               QPushButton, QFileDialog, QHBoxLayout, QDialogButtonBox, QTimeEdit )
from PySide6.QtCore import Qt, QTime
from core.settings_manager import SettingsManager


class PreferencesDialog(QDialog):

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(520)
        self.setModal(True)

        # Lock dialog size
        self.adjustSize()
        self.setSizeGripEnabled(False)                        
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True) 

        self.settings = SettingsManager()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tabs 
        self._init_database_tab()
        self._init_security_tab()
        self._init_ui_tab()
        self._init_backup_tab()

        # Dialog Buttons 
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # DATABASE TAB
    def _init_database_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        self.change_pw_btn = QPushButton("Change Password...")
        if self.main_window:
            self.change_pw_btn.clicked.connect(self.main_window.change_master_password)
        form.addRow("Change Password:", self.change_pw_btn)

        self.auto_lock_spin = QSpinBox()
        self.auto_lock_spin.setRange(0, 120)
        self.auto_lock_spin.setValue(self.settings.get("auto_lock_minutes", 10))
        form.addRow("Auto-lock after (minutes):", self.auto_lock_spin)

        self.lock_on_sleep_chk = QCheckBox("Lock when computer sleeps")
        self.lock_on_sleep_chk.setChecked(self.settings.get("lock_on_sleep", True))
        form.addRow("", self.lock_on_sleep_chk)

        self.tabs.addTab(tab, "Database Settings")

    # ADDITIONAL SECURITY TAB
    def _init_security_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        self.clipboard_spin = QSpinBox()
        self.clipboard_spin.setRange(1, 300)
        self.clipboard_spin.setValue(self.settings.get("clipboard_clear_seconds", 15))
        form.addRow("Clear clipboard after (seconds):", self.clipboard_spin)

        self.lock_on_minimize_chk = QCheckBox("Lock when app is minimized")
        self.lock_on_minimize_chk.setChecked(self.settings.get("lock_on_minimize", True))
        form.addRow("", self.lock_on_minimize_chk)

        self.copy_notify_chk = QCheckBox("Show notifications when copying passwords")
        self.copy_notify_chk.setChecked(self.settings.get("copy_notifications", True))
        form.addRow("", self.copy_notify_chk)

        self.tabs.addTab(tab, "Additional Security")

    # UI TAB
    def _init_ui_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "galaxy", "obsidian", "summer", "winter"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "dark"))
        form.addRow("Theme:", self.theme_combo)

        self.tabs.addTab(tab, "UI")

    # BACKUP TAB
    def _init_backup_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        # Master disable
        self.backup_disabled_chk = QCheckBox("Don't back up")
        self.backup_disabled_chk.setChecked(bool(self.settings.get("backup_disabled", False)))
        form.addRow("", self.backup_disabled_chk)

        # Backup destination folder + Browse + Backup now
        path_row = QHBoxLayout()
        current_folder = (self.settings.get("backup_path", "") or "").strip() \
                         or (self.settings.get("backup_dir", "") or "").strip()
        self.backup_path_edit = QLineEdit(current_folder)
        browse_btn = QPushButton("Browse")
        backup_now_btn = QPushButton("Backup now")
        path_row.addWidget(self.backup_path_edit, 1)
        path_row.addWidget(browse_btn, 0)
        path_row.addWidget(backup_now_btn, 0)
        form.addRow("Backup Folder:", path_row)

        # Auto on close
        self.backup_on_close = QCheckBox("Back up on close")
        self.backup_on_close.setChecked(bool(self.settings.get("backup_on_close", True)))
        form.addRow("", self.backup_on_close)

        # Scheduled backups
        self.sched_enable_chk = QCheckBox("Enable scheduled backup")
        self.sched_enable_chk.setChecked(bool(self.settings.get("backup_sched_enabled",
                                                                self.settings.get("enable_backup", False))))
        form.addRow("", self.sched_enable_chk)

        self.sched_interval_combo = QComboBox()
        self.sched_interval_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.sched_interval_combo.setCurrentText(self.settings.get("backup_interval",
                                                                   self.settings.get("backup_schedule", "Daily")))

        self.sched_time_edit = QTimeEdit()
        time_str = self.settings.get("backup_time", "02:00")
        t = QTime.fromString(time_str, "HH:mm")
        if not t.isValid():
            t = QTime.fromString(time_str, "h:mm AP")
        if not t.isValid():
            t = QTime(2, 0)
        self.sched_time_edit.setTime(t)
        self.sched_time_edit.setDisplayFormat("h:mm AP")

        sched_row = QHBoxLayout()
        sched_row.addWidget(self.sched_interval_combo)
        sched_row.addWidget(self.sched_time_edit)
        form.addRow("Scheduled:", sched_row)

        #Retention (0 = unlimited)
        self.backup_retention_spin = QSpinBox()
        self.backup_retention_spin.setRange(0, 500)
        self.backup_retention_spin.setToolTip("How many backups to keep (0 = unlimited)")
        self.backup_retention_spin.setValue(int(self.settings.get("backup_retention",
                                                                  self.settings.get("backup_number", 10)) or 0))
        form.addRow("Keep last N backups:", self.backup_retention_spin)

        browse_btn.clicked.connect(self._browse_backup)
        backup_now_btn.clicked.connect(self._backup_now)

        def _sync_disable_state():
            disabled = self.backup_disabled_chk.isChecked()
            self.backup_path_edit.setEnabled(True)
            browse_btn.setEnabled(True)
            backup_now_btn.setEnabled(True)
            for w in (
                self.backup_on_close, self.sched_enable_chk,
                self.sched_interval_combo, self.sched_time_edit,
                self.backup_retention_spin
            ):
                w.setEnabled(not disabled)

        self.backup_disabled_chk.toggled.connect(_sync_disable_state)
        _sync_disable_state()

        self.tabs.addTab(tab, "Backup / Restore")

    # SAVE / BROWSE / ACTIONS
    def _browse_backup(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if path:
            self.backup_path_edit.setText(path)

    def _backup_now(self):
        host = self.main_window
        if host and hasattr(host, "export_backup") and callable(host.export_backup):
            path_val = self.backup_path_edit.text().strip()
            self.settings.set("backup_dir", path_val)
            self.settings.set("backup_path", path_val)
            host.export_backup(reason="manual")

    def accept(self):
        self.settings.set("auto_lock_minutes", self.auto_lock_spin.value())
        self.settings.set("lock_on_sleep", self.lock_on_sleep_chk.isChecked())

        self.settings.set("clipboard_clear_seconds", self.clipboard_spin.value())
        self.settings.set("lock_on_minimize", self.lock_on_minimize_chk.isChecked())
        self.settings.set("copy_notifications", self.copy_notify_chk.isChecked())

        self.settings.set("theme", self.theme_combo.currentText())

        path_val = self.backup_path_edit.text().strip()
        self.settings.set("backup_disabled", self.backup_disabled_chk.isChecked())
        self.settings.set("backup_dir", path_val)            # legacy kept in sync
        self.settings.set("backup_path", path_val)           # preferred key (scheduler/engine use this)
        self.settings.set("backup_on_close", self.backup_on_close.isChecked())
        self.settings.set("backup_retention", int(self.backup_retention_spin.value()))
        self.settings.set("backup_sched_enabled", self.sched_enable_chk.isChecked())
        self.settings.set("backup_interval", self.sched_interval_combo.currentText())
        self.settings.set("backup_time", self.sched_time_edit.time().toString("HH:mm"))

        if hasattr(self.main_window, "_check_scheduled_backup"):
            try:
                self.main_window._check_scheduled_backup()
            except Exception:
                pass

        super().accept()
