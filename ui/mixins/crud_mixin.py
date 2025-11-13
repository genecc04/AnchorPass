from PySide6.QtWidgets import QMessageBox
from core import db

STORE_PLAINTEXT_EMAIL = False

class CrudMixin:
    def _current_entry_id_from_table(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it0 = self.table.item(row, 0)
        if it0 is None:
            return None
        entry_id = it0.data(0x0100)
        if entry_id is None and hasattr(self, "_current_rows"):
            try:
                entry_id = int(self._current_rows[row][0])
            except Exception:
                return None
        return int(entry_id) if entry_id is not None else None

    def add_entry(self):
        if not getattr(self, "cipher", None):
            QMessageBox.critical(self, "Error", "Vault is locked; cannot add.")
            return

        from ui.entry_dialog import EntryDialog
        dlg = EntryDialog(self, entry=None, default_category=self.current_category, icon_family=getattr(self, "icon_family", None))
        if not dlg.exec():
            return

        v = dlg.values()

        plain = {
            "site": v.get("site", ""),
            "site_link": v.get("site_link", ""),
            "username": v.get("username", ""),
            "email": v.get("email", ""),
            "notes": v.get("notes", ""),
            "category": v.get("category", "") or self.current_category or "",
            "password": v.get("password", ""),
            "pin": v.get("pin", ""),
            "security_code": v.get("security_code", ""),
            "app_password": v.get("app_password", ""),
            "otp_secret": v.get("otp_secret", ""),
            "recovery_email": v.get("recovery_email", ""),
            "recovery_phone": v.get("recovery_phone", ""),
            "security_questions": v.get("security_questions", ""),
            "tags": v.get("tags", ""),
            "favorite": v.get("favorite", 0),
            "expiry_date": v.get("expiry_date"),
            "status": v.get("status", "active"),
        }

        row = db.encrypt_plain_to_row( plain=plain, cipher=self.cipher, base_row=None, 
                                      mirror_plaintext=STORE_PLAINTEXT_EMAIL, preserve_existing_cipher_on_empty=False )

        if not STORE_PLAINTEXT_EMAIL:
            row["email"] = ""

        if "expiry_date" in plain:
            row["expiry_date"] = plain["expiry_date"]
        if "status" in plain:
            row["status"] = plain["status"]

        db.add_entry_full(row)
        target = plain.get("category") or self.current_category
        if hasattr(self, "_refresh_tree_and_table"):
            self._refresh_tree_and_table(target_category=target)
        else:
            self.reload()

    def edit_entry(self):
        if not getattr(self, "cipher", None):
            QMessageBox.critical(self, "Error", "Vault is locked; cannot edit.")
            return

        entry_id = self._current_entry_id_from_table()
        if entry_id is None:
            return

        row = db.fetch_entry_dict(int(entry_id))
        if not row:
            return

        entry_plain = db.decrypt_row_to_plain(row, self.cipher)
        entry_plain["id"] = entry_id
        
        entry_plain["expiry_date"] = row.get("expiry_date")
        old_status = row.get("status", "active")
        entry_plain["status"] = old_status

        from ui.entry_dialog import EntryDialog
        dlg = EntryDialog(self, entry=entry_plain, default_category=self.current_category)
        if not dlg.exec():
            return

        v = dlg.values()
        new_status = v.get("status", "active")

        merged_plain = dict(entry_plain)
        merged_plain.update(v)
        merged_plain["id"] = entry_id

        new_row = db.encrypt_plain_to_row( plain=merged_plain, cipher=self.cipher, base_row=row, 
                                          mirror_plaintext=STORE_PLAINTEXT_EMAIL, preserve_existing_cipher_on_empty=True, )

        if not STORE_PLAINTEXT_EMAIL:
            new_row["email"] = ""

        if "expiry_date" in merged_plain:
            new_row["expiry_date"] = merged_plain["expiry_date"]
        if "status" in merged_plain:
            new_row["status"] = merged_plain["status"]

        if old_status != new_status:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            
            if new_status == "expired":
                new_row["expired_at"] = now
            elif new_status == "archived":
                new_row["archived_at"] = now
            elif new_status == "deleted":
                new_row["deleted_at"] = now
            elif new_status == "active":
                new_row["expired_at"] = None
                new_row["archived_at"] = None
                new_row["deleted_at"] = None

        update_payload = dict(new_row)
        update_payload.pop("id", None)

        db.update_entry_full(entry_id, update_payload)
        old_cat = entry_plain.get("category", "")
        new_cat = merged_plain.get("category", old_cat)
        target = new_cat or self.current_category
        if hasattr(self, "_refresh_tree_and_table"):
            self._refresh_tree_and_table(target_category=target)
        else:
            self.reload()
                    
    def archive_entry(self):
        entry_id = self._current_entry_id_from_table()
        if entry_id is None:
            return
        
        reply = QMessageBox.question(
            self, "Archive Entry",
            "Are you sure you want to archive this entry?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.change_status(entry_id, "archived")
            if hasattr(self, "_refresh_tree_and_table"):
                self._refresh_tree_and_table()
            else:
                self.reload()
                
    def restore_entry(self):
        entry_id = self._current_entry_id_from_table()
        if entry_id is None:
            return
        
        db.restore_entry(entry_id)
        if hasattr(self, "_refresh_tree_and_table"):
            self._refresh_tree_and_table()
        else:
            self.reload()
        QMessageBox.information(self, "Success", "Entry restored to active status.")
    
    def permanently_delete_entry(self):
        entry_id = self._current_entry_id_from_table()
        if entry_id is None:
            return
        
        reply = QMessageBox.warning(
            self, "Permanently Delete Entry",
            "This will PERMANENTLY delete this entry and cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.permanently_delete_entry(entry_id)
            if hasattr(self, "_refresh_tree_and_table"):
                self._refresh_tree_and_table()
            else:
                self.reload()
            QMessageBox.information(self, "Success", "Entry permanently deleted.")

    