from PySide6.QtWidgets import ( QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit, QComboBox, QCheckBox, 
                               QPushButton, QFileDialog, QHBoxLayout, QDialogButtonBox, QKeySequenceEdit, QLabel, QGridLayout, QMessageBox)
from PySide6.QtGui import QKeySequence, QKeyEvent
from PySide6.QtCore import Qt, QTime, QEvent
from core.settings_manager import SettingsManager
from ui.widgets.plusminus_spinbox import PlusMinusSpinBox
from ui.widgets.plusminus_timeedit import PlusMinusTimeEdit
from core.startup_manager import is_startup_enabled, set_startup_enabled

class PreferencesDialog(QDialog):

    def __init__(self, main_window=None, settings: SettingsManager | None = None):
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

        if settings is not None:
            self.settings = settings
        elif main_window is not None and hasattr(main_window, "settings"):
            self.settings = main_window.settings
        else:
            self.settings = SettingsManager()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")
        layout.addWidget(self.tabs)

        # Tabs 
        self._init_database_tab()
        self._init_hotkeys_tab()
        self._init_backup_tab()

        # Dialog Buttons 
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _handle_accept(self):
        auto_lock_val = self.auto_lock_spin.value()
        clipboard_val = self.clipboard_spin.value()

        if auto_lock_val == 0 or clipboard_val == 0:
            result = QMessageBox.warning(
                self,
                "Security warning",
                (
                    "Setting Auto-Lock or Clear Clipboard to 0 may expose your "
                    "password and other sensitive data.\n\n"
                    "Press OK to save anyway, or Cancel to go back."
                ),
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )

            if result != QMessageBox.Ok:
                return

        self.accept()

    def eventFilter(self, obj, event):
        if isinstance(obj, QKeySequenceEdit) and event.type() == QEvent.KeyPress:
            key_event: QKeyEvent = event
            if key_event.key() in (Qt.Key_Backspace, Qt.Key_Delete) and key_event.modifiers() == Qt.NoModifier:
                obj.clear()
                return True

        return super().eventFilter(obj, event)

    # DATABASE TAB
    def _init_database_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setContentsMargins(15, 15, 30, 15)
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        # --- Top fields in normal form layout ---

        self.change_pw_btn = QPushButton("Change Password...")
        if self.main_window:
            self.change_pw_btn.clicked.connect(self.main_window.change_master_password)
        form.addRow("Change Password:", self.change_pw_btn)

        self.auto_lock_spin = PlusMinusSpinBox()
        self.auto_lock_spin.setRange(0, 120)
        self.auto_lock_spin.setValue(self.settings.get("auto_lock_minutes", 10))
        form.addRow("Auto-Lock (minutes):", self.auto_lock_spin)

        self.clipboard_spin = PlusMinusSpinBox()
        self.clipboard_spin.setRange(0, 300)
        self.clipboard_spin.setValue(self.settings.get("clipboard_clear_seconds", 15))
        form.addRow("Clear Clipboard (seconds):", self.clipboard_spin)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "galaxy", "obsidian", "summer", "winter"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "dark"))
        form.addRow("Theme:", self.theme_combo)

        # --- Checkboxes in a 2-column grid ---

        # Create checkboxes (same as before)
        self.start_with_windows_chk = QCheckBox("Start with Windows")
        stored = self.settings.get("start_with_windows", None)
        if stored is None:
            self.start_with_windows_chk.setChecked(is_startup_enabled())
        else:
            self.start_with_windows_chk.setChecked(bool(stored))

        self.minimize_to_tray_chk = QCheckBox("Minimize to tray on exit")
        self.minimize_to_tray_chk.setChecked(
            bool(self.settings.get("minimize_to_tray_on_exit", False))
        )

        self.minimize_to_tray_on_minimize_chk = QCheckBox("Minimize to tray")
        self.minimize_to_tray_on_minimize_chk.setChecked(
            bool(self.settings.get("minimize_to_tray_on_minimize", False))
        )

        self.lock_on_sleep_chk = QCheckBox("Lock when computer sleeps")
        self.lock_on_sleep_chk.setChecked(self.settings.get("lock_on_sleep", True))

        self.lock_on_minimize_chk = QCheckBox("Lock when app is minimized")
        self.lock_on_minimize_chk.setChecked(self.settings.get("lock_on_minimize", True))

        self.copy_notify_chk = QCheckBox("Show notifications when copying passwords")
        self.copy_notify_chk.setChecked(self.settings.get("copy_notifications", True))

        # Put them into a 2-column grid
        checks_panel = QWidget()
        checks_panel.setObjectName("HotkeysPanel")
        grid = QGridLayout(checks_panel)
        grid.setContentsMargins(0, 8, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(4)

        row = 0
        grid.addWidget(self.start_with_windows_chk,            row, 0)
        grid.addWidget(self.lock_on_minimize_chk,              row, 1); row += 1

        grid.addWidget(self.minimize_to_tray_on_minimize_chk,  row, 0)
        grid.addWidget(self.lock_on_sleep_chk,                 row, 1); row += 1

        grid.addWidget(self.minimize_to_tray_chk,              row, 0)
        grid.addWidget(self.copy_notify_chk,                   row, 1)

        # Add the whole panel as one form row (no label)
        form.addRow("", checks_panel)
        
        self.tabs.addTab(tab, "Database/Application Settings")

    def _init_hotkeys_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")

        # Main vertical layout for the tab
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(8, 8, 0, 8)
        vbox.setSpacing(6)

        form = QFormLayout()
        form.setObjectName("prefsTabs")
        form.setLabelAlignment(Qt.AlignLeft)

        self.hotkeys_enabled_chk = QCheckBox("Enable keyboard shortcuts")
        self.hotkeys_enabled_chk.setChecked(
            bool(self.settings.get("hotkeys_enabled", True))
        )

        def _make_key_edit(setting_key: str, default: str = "") -> QKeySequenceEdit:
            seq_str = self.settings.get(setting_key, default) or ""
            edit = QKeySequenceEdit()
            if seq_str:
                edit.setKeySequence(QKeySequence(seq_str))
            edit.installEventFilter(self)
            return edit

        # Copy-related hotkeys
        self.hk_copy_email        = _make_key_edit("hotkey_copy_email", "")
        self.hk_copy_username     = _make_key_edit("hotkey_copy_username", "")
        self.hk_copy_password     = _make_key_edit("hotkey_copy_password", "")
        self.hk_copy_app_password = _make_key_edit("hotkey_copy_app_password", "")

        self.hk_copy_site         = _make_key_edit("hotkey_copy_site", "")
        self.hk_copy_totp         = _make_key_edit("hotkey_copy_totp", "")
        self.hk_copy_sec_code     = _make_key_edit("hotkey_copy_security_code", "")

        # Entry actions
        self.hk_add_entry         = _make_key_edit("hotkey_add_entry", "")
        self.hk_edit_entry        = _make_key_edit("hotkey_edit_entry", "")
        self.hk_duplicate_entry   = _make_key_edit("hotkey_duplicate_entry", "")
        self.hk_archive_entry     = _make_key_edit("hotkey_archive_entry", "")
        self.hk_expire_entry      = _make_key_edit("hotkey_expire_entry", "")
        self.hk_delete_entry      = _make_key_edit("hotkey_delete_entry", "")

        # Lock Vault default Ctrl+L
        self.hk_lock_vault        = _make_key_edit("hotkey_lock_vault", "Ctrl+L")

        # Build a 2 column grid for hotkeys
        hotkeys_widget = QWidget()
        hotkeys_widget.setObjectName("HotkeysPanel")
        grid = QGridLayout(hotkeys_widget)
        grid.setContentsMargins(0, 0, 8, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        # Left column
        row = 0
        grid.addWidget(QLabel("Copy Site:"),            row, 0)
        grid.addWidget(self.hk_copy_site,               row, 1); row += 1

        grid.addWidget(QLabel("Copy TOTP:"),            row, 0)
        grid.addWidget(self.hk_copy_totp,               row, 1); row += 1

        grid.addWidget(QLabel("Copy Security code:"),   row, 0)
        grid.addWidget(self.hk_copy_sec_code,           row, 1); row += 1

        grid.addWidget(QLabel("Copy Email:"),           row, 0)
        grid.addWidget(self.hk_copy_email,              row, 1); row += 1

        grid.addWidget(QLabel("Copy Username:"),        row, 0)
        grid.addWidget(self.hk_copy_username,           row, 1); row += 1

        grid.addWidget(QLabel("Copy Password:"),        row, 0)
        grid.addWidget(self.hk_copy_password,           row, 1); row += 1

        grid.addWidget(QLabel("Copy App Password:"),    row, 0)
        grid.addWidget(self.hk_copy_app_password,       row, 1)

        # Right column
        row = 0
        grid.addWidget(QLabel("Add entry:"),            row, 2)
        grid.addWidget(self.hk_add_entry,               row, 3); row += 1

        grid.addWidget(QLabel("Edit entry:"),           row, 2)
        grid.addWidget(self.hk_edit_entry,              row, 3); row += 1

        grid.addWidget(QLabel("Duplicate entry:"),      row, 2)
        grid.addWidget(self.hk_duplicate_entry,         row, 3); row += 1

        grid.addWidget(QLabel("Archive:"),              row, 2)
        grid.addWidget(self.hk_archive_entry,           row, 3); row += 1

        grid.addWidget(QLabel("Expire:"),               row, 2)
        grid.addWidget(self.hk_expire_entry,            row, 3); row += 1

        grid.addWidget(QLabel("Delete:"),               row, 2)
        grid.addWidget(self.hk_delete_entry,            row, 3); row += 1

        grid.addWidget(QLabel("Lock Vault (Ctrl+L):"),  row, 2)
        grid.addWidget(self.hk_lock_vault,              row, 3)

        # Put the hotkeys grid inside the form
        form.addRow("Hotkeys:", hotkeys_widget)

        # Add form to main vbox
        vbox.addLayout(form)
        vbox.addStretch()

        # Bottom left checkbox row
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.hotkeys_enabled_chk)
        bottom_row.addStretch()
        vbox.addLayout(bottom_row)

        self.tabs.addTab(tab, "Hotkeys")

    # BACKUP TAB
    def _init_backup_tab(self):
        tab = QWidget()
        tab.setObjectName("prefsTabs")
        form = QFormLayout(tab)
        form.setContentsMargins(15,15,30,15)
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

        self.sched_time_edit = PlusMinusTimeEdit()
        time_str = self.settings.get("backup_time", "02:00")
        t = QTime.fromString(time_str, "HH:mm")
        if not t.isValid():
            t = QTime.fromString(time_str, "h:mm AP")
        if not t.isValid():
            t = QTime(2, 0)
        self.sched_time_edit.setTime(t)
        self.sched_time_edit.setDisplayFormat("h:mm AP")

        h = self.sched_interval_combo.sizeHint().height()
        self.sched_time_edit.setMinimumHeight(h)

        sched_row = QHBoxLayout()
        sched_row.addWidget(self.sched_interval_combo)
        sched_row.addWidget(self.sched_time_edit)
        form.addRow("Scheduled:", sched_row)

        #Retention (0 = unlimited)
        self.backup_retention_spin = PlusMinusSpinBox()
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
        _global_settings = SettingsManager()
        self.settings.set("auto_lock_minutes", self.auto_lock_spin.value())
        self.settings.set("lock_on_sleep", self.lock_on_sleep_chk.isChecked())

        self.settings.set("clipboard_clear_seconds", self.clipboard_spin.value())
        self.settings.set("lock_on_minimize", self.lock_on_minimize_chk.isChecked())
        self.settings.set("copy_notifications", self.copy_notify_chk.isChecked())

        self.settings.set("theme", self.theme_combo.currentText())
        _global_settings.set("theme", self.theme_combo.currentText())
        self.settings.set("minimize_to_tray_on_exit", self.minimize_to_tray_chk.isChecked())
        self.settings.set("minimize_to_tray_on_minimize", self.minimize_to_tray_on_minimize_chk.isChecked())
        self.settings.set("hotkeys_enabled", self.hotkeys_enabled_chk.isChecked())
        start_with_windows = self.start_with_windows_chk.isChecked()
        self.settings.set("start_with_windows", start_with_windows)
        try:
            set_startup_enabled(start_with_windows)
        except Exception:
            pass

        def _save_hotkey(key: str, editor: QKeySequenceEdit):
            self.settings.set(key, editor.keySequence().toString())
        _save_hotkey("hotkey_copy_email",          self.hk_copy_email)
        _save_hotkey("hotkey_copy_username",       self.hk_copy_username)
        _save_hotkey("hotkey_copy_password",       self.hk_copy_password)
        _save_hotkey("hotkey_copy_app_password",   self.hk_copy_app_password)

        _save_hotkey("hotkey_copy_site",           self.hk_copy_site)
        _save_hotkey("hotkey_copy_totp",           self.hk_copy_totp)
        _save_hotkey("hotkey_copy_security_code",  self.hk_copy_sec_code)

        _save_hotkey("hotkey_add_entry",           self.hk_add_entry)
        _save_hotkey("hotkey_edit_entry",          self.hk_edit_entry)
        _save_hotkey("hotkey_duplicate_entry",     self.hk_duplicate_entry)
        _save_hotkey("hotkey_archive_entry",       self.hk_archive_entry)
        _save_hotkey("hotkey_expire_entry",        self.hk_expire_entry)
        _save_hotkey("hotkey_delete_entry",        self.hk_delete_entry)
        _save_hotkey("hotkey_lock_vault",          self.hk_lock_vault)

        path_val = self.backup_path_edit.text().strip()
        self.settings.set("backup_disabled", self.backup_disabled_chk.isChecked())
        self.settings.set("backup_dir", path_val)
        self.settings.set("backup_path", path_val)
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
