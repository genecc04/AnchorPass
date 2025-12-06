from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox, 
                               QCheckBox, QSizePolicy, QHBoxLayout)
from PySide6.QtCore import Qt, QDate
from datetime import datetime, timezone
from PySide6.QtGui import QFont
from core import db
from core.settings_manager import SettingsManager
from ui.widgets.password_field import PasswordLineEdit
from ui.entry_dialog_totp import TotpPreviewWidget
from ui.widgets.rounded_context_menu import LineEdit, PlainTextEdit, DatePicker

class EntrySectionBase(QWidget):
    def _get_settings(self) -> SettingsManager:
        w = self
        while w is not None:
            if hasattr(w, "settings"):
                s = getattr(w, "settings")
                if isinstance(s, SettingsManager):
                    return s
            w = w.parent()
        return SettingsManager()
    
    def _get_logger(self):
        settings = self._get_settings()
        if not bool(settings.get("copy_notifications", True)):
            return None

        w = self
        while w is not None:
            if hasattr(w, "_log_status"):
                return getattr(w, "_log_status")
            w = w.parent()
        return None
        
class BasicInfoSection(EntrySectionBase):
    
    def __init__(self, entry: dict, icon_family: str | None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._icon_family = icon_family
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        
        self._build_fields(form)
        
        form_widget = QWidget()
        form_widget.setLayout(form)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(form_widget)
        
    def _build_fields(self, form: QFormLayout):
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000

        self.site = LineEdit(self._entry.get("site", ""))
        self.site.setPlaceholderText("Site / App")

        self.site_link = self._create_plain_copy_field(
            self._entry.get("site_link", ""),
            "https://example.com/login",
            clear_ms,
        )

        self.username = self._create_plain_copy_field(
            self._entry.get("username", ""),
            "Username",
            clear_ms,
        )
        self.email = self._create_plain_copy_field(
            self._entry.get("email", ""),
            "Email",
            clear_ms,
        )

        self.password = PasswordLineEdit(
            placeholder="Password",
            clear_clipboard_after_ms=clear_ms,
            icon_point_size=18,
            icon_padding=2,
            strength_alpha=0.12,
            strength_enabled=True,
            icon_family=self._icon_family,
            copy_enabled=True,
        )
        if self._entry.get("password"):
            self.password.setText(self._entry["password"])

        self.notes = PlainTextEdit(self._entry.get("notes", ""))
        self.notes.setFixedHeight(96)
        self.notes.setAttribute(Qt.WA_StyledBackground, True)
        self.notes.setViewportMargins(2, 2, 2, 2)

        site_row = QWidget(self)
        site_layout = QHBoxLayout(site_row)
        site_layout.setContentsMargins(0, 0, 0, 0)
        site_layout.setSpacing(8)

        site_layout.addWidget(self.site, 2)
        site_layout.addWidget(self.site_link, 3)

        form.addRow("Site/Title:", site_row)
        form.addRow("Username:", self.username)
        form.addRow("Email:", self.email)
        form.addRow("Password:", self.password)
        form.addRow("Notes:", self.notes)

        logger = self._get_logger()
        if logger:
            fields = [
                (self.site_link, "Site URL"),
                (self.username, "Username"),
                (self.email, "Email"),
                (self.password, "Password"),
            ]
            for fld, label in fields:
                if hasattr(fld, "copied"):
                    fld.copied.connect(lambda lbl=label: logger(f"{lbl} copied", 1500))
        
    def _create_plain_copy_field(self, initial: str, placeholder: str, clear_ms: int) -> PasswordLineEdit:
        fld = PasswordLineEdit(
            placeholder=placeholder,
            clear_clipboard_after_ms=clear_ms,
            icon_point_size=18,
            icon_padding=2,
            strength_alpha=0.0,
            strength_enabled=False,
            icon_family=self._icon_family,
            copy_enabled=True,
            visibility_enabled=False
        )
        fld.setEchoMode(LineEdit.Normal)
        if initial:
            fld.setText(initial)
        return fld
        
    def values(self) -> dict:
        return {
            "site": self.site.text().strip(),
            "site_link": self.site_link.text().strip(),
            "username": self.username.text().strip(),
            "email": self.email.text().strip(),
            "password": self.password.text(),
            "notes": self.notes.toPlainText(),
        }
    
    def load_plain(self, entry: dict) -> None:
        self._entry = entry
        self.site.setText(entry.get("site", "") or "")
        self.site_link.setText(entry.get("site_link", "") or "")
        self.username.setText(entry.get("username", "") or "")
        self.email.setText(entry.get("email", "") or "")
        self.password.setText(entry.get("password", "") or "")
        self.notes.setPlainText(entry.get("notes", "") or "")


class AuthSection(EntrySectionBase):
    
    def __init__(self, entry: dict, icon_family: str | None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._icon_family = icon_family
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        self._build_fields(form)
        
        form_widget = QWidget()
        form_widget.setLayout(form)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(form_widget)

    def _build_fields(self, form: QFormLayout):
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000

        self.app_password = self._create_password_field(clear_ms, "App-specific password", True)
        self.pin = self._create_password_field(clear_ms, "PIN", False)
        self.security_code = self._create_password_field(
            clear_ms, "Security code / CVV / access code", False
        )

        if self._entry.get("app_password"):
            self.app_password.setText(self._entry["app_password"])
        if self._entry.get("pin"):
            self.pin.setText(self._entry["pin"])
        if self._entry.get("security_code"):
            self.security_code.setText(self._entry["security_code"])

        form.addRow("App Password:", self.app_password)
        form.addRow("PIN:", self.pin)
        form.addRow("Security Code:", self.security_code)

        logger = self._get_logger()
        if logger:
            fields = [
                (self.app_password, "App password"),
                (self.pin, "PIN"),
                (self.security_code, "Security code"),
            ]
            for fld, label in fields:
                if hasattr(fld, "copied"):
                    fld.copied.connect(lambda lbl=label: logger(f"{lbl} copied", 1500))

    def _create_password_field(self, clear_ms: int, placeholder: str, strength_enabled: bool) -> PasswordLineEdit:
        return PasswordLineEdit(
            placeholder=placeholder,
            clear_clipboard_after_ms=clear_ms,
            icon_point_size=18,
            icon_padding=2,
            strength_alpha=0.12 if strength_enabled else 0.0,
            strength_enabled=strength_enabled,
            icon_family=self._icon_family,
            copy_enabled=True
        )
        
    def values(self) -> dict:
        return {
            "app_password": self.app_password.text(),
            "pin": self.pin.text(),
            "security_code": self.security_code.text(),
        }
    
    def load_plain(self, entry: dict) -> None:
        self._entry = entry
        self.app_password.setText(entry.get("app_password", "") or "")
        self.pin.setText(entry.get("pin", "") or "")
        self.security_code.setText(entry.get("security_code", "") or "")

class RecoverySection(EntrySectionBase):
    
    def __init__(self, entry: dict, icon_family: str | None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._icon_family = icon_family
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        
        self._build_fields(form)
        
        form_widget = QWidget()
        form_widget.setLayout(form)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(form_widget)
        
    def _build_fields(self, form: QFormLayout):
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000
        
        self.recovery_email = LineEdit(self._entry.get("recovery_email", ""))
        self.recovery_phone = LineEdit(self._entry.get("recovery_phone", ""))
        
        self.security_questions = PlainTextEdit(self._entry.get("security_questions", ""))
        self.security_questions.setPlaceholderText("Example:\nPet name: Python\nFavorite Drink: Coffee")
        self.security_questions.setFixedHeight(96)
        self.security_questions.setAttribute(Qt.WA_StyledBackground, True)
        self.security_questions.setViewportMargins(2, 2, 2, 2)
        
        self.otp_secret = PasswordLineEdit(
            placeholder="OTP secret (TOTP key)",
            clear_clipboard_after_ms=clear_ms,
            icon_point_size=18,
            icon_padding=2,
            strength_alpha=0.0,
            strength_enabled=False,
            icon_family=self._icon_family,
            copy_enabled=True
        )
        if self._entry.get("otp_secret"):
            self.otp_secret.setText(self._entry["otp_secret"])
        
        form.addRow("Recovery email:", self.recovery_email)
        form.addRow("Recovery phone:", self.recovery_phone)
        form.addRow("Security questions:", self.security_questions)
        form.addRow("OTP secret:", self.otp_secret)
        
        self.totp_widget = TotpPreviewWidget(self.otp_secret, self._icon_family, self)
        form.addRow("TOTP now:", self.totp_widget)

        logger = self._get_logger()
        if logger and hasattr(self.otp_secret, "copied"):
            self.otp_secret.copied.connect(
                lambda: logger("OTP secret copied", 1500)
            )
        
    def cleanup(self):
        self.totp_widget.cleanup()
        
    def handle_theme_change(self, event):
        self.totp_widget.handle_theme_change(event)
        
    def values(self) -> dict:
        return {
            "recovery_email": self.recovery_email.text().strip(),
            "recovery_phone": self.recovery_phone.text().strip(),
            "security_questions": self.security_questions.toPlainText(),
            "otp_secret": self.otp_secret.text(),
        }
    
    def load_plain(self, entry: dict) -> None:
        self._entry = entry
        self.recovery_email.setText(entry.get("recovery_email", "") or "")
        self.recovery_phone.setText(entry.get("recovery_phone", "") or "")
        self.security_questions.setPlainText(entry.get("security_questions", "") or "")
        self.otp_secret.setText(entry.get("otp_secret", "") or "")

class MetadataSection(EntrySectionBase):
    
    def __init__(self, entry: dict, default_category: str | None, icon_family: str | None = None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._is_new_entry = not bool(entry.get("id"))
        self._icon_family = icon_family
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        
        self._build_fields(form, default_category)
        
        form_widget = QWidget()
        form_widget.setLayout(form)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(form_widget)
        
    def _build_fields(self, form: QFormLayout, default_category: str | None):
        self.category = QComboBox()
        cats = db.fetch_categories()
        self.category.addItems(cats)
        
        if self._entry.get("category"):
            idx = self.category.findText(self._entry["category"])
            if idx >= 0:
                self.category.setCurrentIndex(idx)
        elif default_category:
            idx = self.category.findText(default_category)
            if idx >= 0:
                self.category.setCurrentIndex(idx)
        
        self.tags = LineEdit(self._entry.get("tags", ""))
        self.favorite = QCheckBox("Favorite")
        self.favorite.setChecked(bool(self._entry.get("favorite", 0)))
                
        icon_font = None
        if self._icon_family:
            icon_font = QFont(self._icon_family)
        
        self.expiry_date = DatePicker(
            parent=self,
            display_format="MMM dd, yyyy",
            initial_date=None,
            icon_font=icon_font,
            icon_px=20
        )
        self.expiry_date.setMinimumDate(QDate.currentDate())
        
        expiry_str = self._entry.get("expiry_date")
        if expiry_str:
            try:
                parts = expiry_str.split("-")
                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                self.expiry_date.setDate(qdate)
            except:
                pass
        
        expiry_container = self.expiry_date
        
        self.status = QComboBox()
        self.status.addItems(["active", "expired", "archived", "deleted"])
        
        current_status = self._entry.get("status", "active")
        idx = self.status.findText(current_status)
        if idx >= 0:
            self.status.setCurrentIndex(idx)
        
        if self._is_new_entry:
            self.status.setEnabled(False)
            self.status.setToolTip("New entries always start as 'active'")
        
        self.status.currentTextChanged.connect(self._update_status_timestamp_visibility)
        
        self.status_timestamp_label = QLabel()
        self.status_timestamp_value = QLabel()
        
        self.status_timestamp_label.setProperty("secondary", True)
        self.status_timestamp_value.setProperty("secondary", True)
        
        self.status_timestamp_label.setText("")
        self.status_timestamp_value.setText("-")
        
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        created_iso = self._entry.get("date_created") or now_utc_iso
        modified_iso = self._entry.get("date_modified") or now_utc_iso
        
        self.date_created_lbl = QLabel(self._format_datetime(created_iso))
        self.date_modified_lbl = QLabel(self._format_datetime(modified_iso))
        self.date_created_lbl.setToolTip(self._format_datetime_tooltip(created_iso))
        self.date_modified_lbl.setToolTip(self._format_datetime_tooltip(modified_iso))
        self.date_created_lbl.setProperty("secondary", True)
        self.date_modified_lbl.setProperty("secondary", True)
        
        form.addRow("Category:", self.category)
        form.addRow("Tags (comma-separated):", self.tags)
        form.addRow("", self.favorite)
        form.addRow("Expiry Date:", expiry_container)
        form.addRow("Status:", self.status)
        
        form.addRow(self.status_timestamp_label, self.status_timestamp_value)
        
        form.addRow("Date created:", self.date_created_lbl)
        form.addRow("Date modified:", self.date_modified_lbl)
        
        self._update_status_timestamp_visibility(current_status)
    
    def _parse_iso_datetime(self, iso_str: str) -> datetime | None:
        if not iso_str:
            return None
        try:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    
    def _format_datetime(self, iso_str: str) -> str:
        dt = self._parse_iso_datetime(iso_str)
        if not dt:
            return "—"
        local = dt.astimezone()
        return local.strftime("%b %d, %Y · %I:%M %p")
    
    def _format_datetime_tooltip(self, iso_str: str) -> str:
        dt = self._parse_iso_datetime(iso_str)
        if not dt:
            return ""
        local = dt.astimezone()
        utc = dt.astimezone(timezone.utc)
        return (
            f"Local: {local.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"UTC:   {utc.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"ISO:   {iso_str}"
        )
    
    def _update_status_timestamp_visibility(self, status: str):
        timestamp_map = {
            "expired": ("Expired at:", self._entry.get("expired_at")),
            "archived": ("Archived at:", self._entry.get("archived_at")),
            "deleted": ("Deleted at:", self._entry.get("deleted_at")),
        }

        if status in timestamp_map:
            label_text, timestamp_value = timestamp_map[status]
            self.status_timestamp_label.setText(label_text)
            if timestamp_value:
                self.status_timestamp_value.setText(self._format_datetime(timestamp_value))
                self.status_timestamp_value.setToolTip(self._format_datetime_tooltip(timestamp_value))
            else:
                self.status_timestamp_value.setText("-")
                self.status_timestamp_value.setToolTip("")
        else:
            self.status_timestamp_label.setText("")
            self.status_timestamp_value.setText("")
            self.status_timestamp_value.setToolTip("")
        
    def values(self) -> dict:
        expiry_date_value = None
        qdate = self.expiry_date.date()
        if qdate.isValid():
            expiry_date_value = qdate.toString("yyyy-MM-dd")
        
        return {
            "category": self.category.currentText(),
            "tags": self.tags.text().strip(),
            "favorite": 1 if self.favorite.isChecked() else 0,
            "expiry_date": expiry_date_value,
            "status": self.status.currentText(),
        }
    
    def load_plain(self, entry: dict) -> None:
        from PySide6.QtCore import QDate

        self._entry = entry

        # category
        cat = entry.get("category", "") or ""
        idx = self.category.findText(cat)
        if idx >= 0:
            self.category.setCurrentIndex(idx)

        self.tags.setText(entry.get("tags", "") or "")
        self.favorite.setChecked(bool(entry.get("favorite", 0)))

        # expiry_date: expects "yyyy-MM-dd"
        expiry_str = entry.get("expiry_date")
        if expiry_str:
            try:
                parts = expiry_str.split("-")
                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                if qdate.isValid():
                    self.expiry_date.setDate(qdate)
            except Exception:
                pass

        # status
        status = entry.get("status", "active")
        idx = self.status.findText(status)
        if idx >= 0:
            self.status.setCurrentIndex(idx)