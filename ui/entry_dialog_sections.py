from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPlainTextEdit, QLabel, QComboBox, 
                               QCheckBox, QSizePolicy, QHBoxLayout, QPushButton)
from PySide6.QtCore import Qt, QDate
from datetime import datetime, timezone

from core import db
from core.settings_manager import SettingsManager
from ui.widgets.password_field import PasswordLineEdit
from ui.widgets.date_picker import DatePicker
from ui.entry_dialog_totp import TotpPreviewWidget

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
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(form_widget)
        
    def _build_fields(self, form: QFormLayout):
        """Build form fields."""
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000
        
        self.site = QLineEdit(self._entry.get("site", ""))
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

        self.notes = QPlainTextEdit(self._entry.get("notes", ""))
        self.notes.setFixedHeight(96)
        self.notes.setAttribute(Qt.WA_StyledBackground, True)
        self.notes.setViewportMargins(2, 2, 2, 2)

        site_row = QWidget(self)
        site_layout = QHBoxLayout(site_row)
        site_layout.setContentsMargins(0, 0, 0, 0)
        site_layout.setSpacing(8)

        site_layout.addWidget(self.site, 2)
        site_layout.addWidget(self.site_link, 3)

        form.addRow("Site:", site_row)
        form.addRow("Username:", self.username)
        form.addRow("Email:", self.email)
        form.addRow("Notes:", self.notes)
        
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
        fld.setEchoMode(QLineEdit.Normal)
        if initial:
            fld.setText(initial)
        return fld
        
    def values(self) -> dict:
        return {
            "site": self.site.text().strip(),
            "site_link": self.site_link.text().strip(),
            "username": self.username.text().strip(),
            "email": self.email.text().strip(),
            "notes": self.notes.toPlainText(),
        }


class AuthSection(EntrySectionBase):
    
    def __init__(self, entry: dict, icon_family: str | None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._icon_family = icon_family
        self._advanced_widgets: list[tuple[QWidget, QWidget]] = []
        
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
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(form_widget)

        self._btn_toggle_advanced = QPushButton("Show more", self)
        self._btn_toggle_advanced.setFlat(True)
        self._btn_toggle_advanced.setCursor(Qt.PointingHandCursor)
        self._btn_toggle_advanced.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._btn_toggle_advanced.clicked.connect(self._toggle_advanced)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_toggle_advanced)
        layout.addLayout(btn_row)

        self._set_advanced_visible(False)

        has_advanced_values = any([
            bool(self.app_password.text().strip()),
            bool(self.pin.text().strip()),
            bool(self.security_code.text().strip()),
        ])
        if has_advanced_values:
            self._set_advanced_visible(True)

    def _build_fields(self, form: QFormLayout):
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000
        
        self.password = self._create_password_field(clear_ms, "Password", True)
        self.app_password = self._create_password_field(clear_ms, "App-specific password", True)
        
        self.pin = self._create_password_field(clear_ms, "PIN", False)
        self.security_code = self._create_password_field(
            clear_ms, "Security code / CVV / access code", False
        )
        
        if self._entry.get("password"):
            self.password.setText(self._entry["password"])
        if self._entry.get("pin"):
            self.pin.setText(self._entry["pin"])
        if self._entry.get("security_code"):
            self.security_code.setText(self._entry["security_code"])
        if self._entry.get("app_password"):
            self.app_password.setText(self._entry["app_password"])
        
        form.addRow("Password:", self.password)

        def add_advanced_row(label_text: str, widget: QWidget):
            form.addRow(label_text, widget)
            row = form.rowCount() - 1
            label_item = form.itemAt(row, QFormLayout.LabelRole)
            field_item = form.itemAt(row, QFormLayout.FieldRole)
            if label_item and field_item:
                label_widget = label_item.widget()
                field_widget = field_item.widget()
                if label_widget and field_widget:
                    self._advanced_widgets.append((label_widget, field_widget))

        add_advanced_row("App Password:", self.app_password)
        add_advanced_row("PIN:", self.pin)
        add_advanced_row("Security Code:", self.security_code)
        
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

    def _set_advanced_visible(self, visible: bool):
        for label, field in self._advanced_widgets:
            label.setVisible(visible)
            field.setVisible(visible)
        self._btn_toggle_advanced.setText("Show less" if visible else "Show more")

    def _toggle_advanced(self):
        if not self._advanced_widgets:
            return
        currently_visible = self._advanced_widgets[0][0].isVisible()
        self._set_advanced_visible(not currently_visible)
        
    def values(self) -> dict:
        return {
            "password": self.password.text(),
            "pin": self.pin.text(),
            "security_code": self.security_code.text(),
            "app_password": self.app_password.text(),
        }


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
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout.addWidget(form_widget)
        
    def _build_fields(self, form: QFormLayout):
        sm = self._get_settings()
        clear_ms = max(0, int(sm.get("clipboard_clear_seconds", 15))) * 1000
        
        self.recovery_email = QLineEdit(self._entry.get("recovery_email", ""))
        self.recovery_phone = QLineEdit(self._entry.get("recovery_phone", ""))
        
        self.security_questions = QPlainTextEdit(self._entry.get("security_questions", ""))
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
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
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
        
        self.tags = QLineEdit(self._entry.get("tags", ""))
        self.favorite = QCheckBox("Favorite")
        self.favorite.setChecked(bool(self._entry.get("favorite", 0)))
        
        from PySide6.QtGui import QFont
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
        
        self.status_timestamp_label.hide()
        self.status_timestamp_value.hide()
        
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
            "expired": ("Expired At:", self._entry.get("expired_at")),
            "archived": ("Archived At:", self._entry.get("archived_at")),
            "deleted": ("Deleted At:", self._entry.get("deleted_at")),
        }
        
        if status in timestamp_map:
            label_text, timestamp_value = timestamp_map[status]
            if timestamp_value:
                self.status_timestamp_label.setText(label_text)
                self.status_timestamp_value.setText(self._format_datetime(timestamp_value))
                self.status_timestamp_value.setToolTip(self._format_datetime_tooltip(timestamp_value))
                self.status_timestamp_label.show()
                self.status_timestamp_value.show()
                return
        
        self.status_timestamp_label.hide()
        self.status_timestamp_value.hide()
        
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