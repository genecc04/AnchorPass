from __future__ import annotations
from typing import Optional, Callable
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


class ClipboardManager:
    
    def __init__(self, settings_manager, status_callback: Optional[Callable[[str, int], None]] = None):
        self.settings = settings_manager
        self.status_callback = status_callback
    
    def copy_to_clipboard(self, value: str, label: str):
        if not value:
            return
            
        cb = QApplication.clipboard()
        cb.setText(value)

        notify = bool(self.settings.get("copy_notifications", True))
        secs = int(self.settings.get("clipboard_clear_seconds", 15) or 0)
        
        if notify and self.status_callback:
            self.status_callback(f"{label} copied.", 1500)

        if secs > 0:
            orig = value
            def _clear_if_unchanged():
                try:
                    if cb.text() == orig:
                        cb.clear()
                        if notify and self.status_callback:
                            self.status_callback("Clipboard cleared.", 1500)
                except Exception:
                    pass
            QTimer.singleShot(secs * 1000, _clear_if_unchanged)
    
    def copy_field_from_entry(self, entry_dict: dict, field: str, cipher=None) -> bool:
        try:
            from core import db_crypto as dbx
            plain = dbx.decrypt_row_to_plain(entry_dict, cipher) if cipher else dict(entry_dict)
        except Exception:
            plain = dict(entry_dict)

        value = (plain.get(field) or "").strip()
        if not value:
            if self.status_callback:
                self.status_callback(f"No {field.replace('_', ' ')} in this entry.", 2000)
            return False

        label = field.replace('_', ' ').title()
        self.copy_to_clipboard(value, label)
        return True