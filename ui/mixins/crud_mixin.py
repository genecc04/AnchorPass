from PySide6.QtWidgets import QMessageBox
from core import db
from ui.entry_dialog import EntryDialog
from datetime import datetime, timezone

STORE_PLAINTEXT_EMAIL = False

_FIELD_LABELS = {
    "site": "Site",
    "site_link": "Site link",
    "username": "Username",
    "email": "Email",
    "password": "Password",
    "app_password": "App password",
    "pin": "PIN",
    "security_code": "Security code",
    "otp_secret": "OTP secret",
    "recovery_email": "Recovery email",
    "recovery_phone": "Recovery phone",
    "security_questions": "Security questions",
    "notes": "Notes",
    "category": "Category",
    "tags": "Tags",
    "favorite": "Favorite",
    "expiry_date": "Expiry date",
    "status": "Status",
}


def _plain_changed_keys(old_plain: dict, new_plain: dict) -> list[str]:
    """
    Compare plaintext dicts and return which keys changed.
    This runs BEFORE encryption, so encrypted fields are handled correctly.
    """
    changed: list[str] = []
    keys = set(old_plain.keys()) | set(new_plain.keys())
    ignore = {"id"}

    for k in keys:
        if k in ignore:
            continue
        if old_plain.get(k) != new_plain.get(k):
            changed.append(k)
    return changed


def _build_history_summary(changed_keys: list[str], plain_after: dict) -> str:
    if not changed_keys:
        return plain_after.get("site") or "Update"
    
    labels = [_FIELD_LABELS.get(k, k) for k in changed_keys]
    labels = [label if label.lower() != 'site' else 'Site/Title' for label in labels]
    if len(labels) == 1:
        changed_text = f"Changed {labels[0]}"
    else:
        changed_text = "Changed " + ", ".join(labels)

    site = (plain_after.get("site") or "").strip()
    if site:
        return f"{changed_text}"
    return changed_text

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

        dlg = EntryDialog(self, entry=None, default_category=self.current_category, icon_family=getattr(self, "icon_family", None), settings=self.settings)
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

        if hasattr(self, "_log_status"):
            self._log_status("Entry saved.", 2000)

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

        old_plain_for_diff = dict(entry_plain)

        dlg = EntryDialog(self, entry=entry_plain, default_category=self.current_category, settings=self.settings)
        if not dlg.exec():
            return

        v = dlg.values()
        new_status = v.get("status", "active")

        merged_plain = dict(entry_plain)
        merged_plain.update(v)
        merged_plain["id"] = entry_id

        changed_keys = _plain_changed_keys(old_plain_for_diff, merged_plain)

        if not changed_keys:
            return
        
        try:
            if hasattr(db, "add_entry_history_snapshot"):
                summary = _build_history_summary(changed_keys, merged_plain)
                db.add_entry_history_snapshot(entry_id, row, summary)
        except Exception:
            pass

        new_row = db.encrypt_plain_to_row( plain=merged_plain, cipher=self.cipher, base_row=row, 
                                          mirror_plaintext=STORE_PLAINTEXT_EMAIL, preserve_existing_cipher_on_empty=True, )

        if not STORE_PLAINTEXT_EMAIL:
            new_row["email"] = ""

        if "expiry_date" in merged_plain:
            new_row["expiry_date"] = merged_plain["expiry_date"]
        if "status" in merged_plain:
            new_row["status"] = merged_plain["status"]

        if old_status != new_status:
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

        if hasattr(self, "_log_status"):
            self._log_status("Entry updated.", 2000)
                    
    def edit_single_entry(self, entry_id):
        if not getattr(self, "cipher", None):
            QMessageBox.critical(self, "Error", "Vault is locked; cannot edit.")
            return

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

        old_plain_for_diff = dict(entry_plain)

        dlg = EntryDialog(self, entry=entry_plain, default_category=self.current_category, settings=self.settings)
        if not dlg.exec():
            return

        v = dlg.values()
        new_status = v.get("status", "active")

        merged_plain = dict(entry_plain)
        merged_plain.update(v)
        merged_plain["id"] = entry_id

        changed_keys = _plain_changed_keys(old_plain_for_diff, merged_plain)
        if not changed_keys:
            return 
        
        try:
            if hasattr(db, "add_entry_history_snapshot"):
                summary = _build_history_summary(changed_keys, merged_plain)
                db.add_entry_history_snapshot(entry_id, row, summary)
        except Exception:
            pass

        new_row = db.encrypt_plain_to_row(
            plain=merged_plain,
            cipher=self.cipher,
            base_row=row,
            mirror_plaintext=STORE_PLAINTEXT_EMAIL,
            preserve_existing_cipher_on_empty=True,
        )

        if not STORE_PLAINTEXT_EMAIL:
            new_row["email"] = ""

        if "expiry_date" in merged_plain:
            new_row["expiry_date"] = merged_plain["expiry_date"]
        if "status" in merged_plain:
            new_row["status"] = merged_plain["status"]

        if old_status != new_status:
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

        if hasattr(self, "_log_status"):
            self._log_status("Entry updated.", 2000)

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

    def _duplicate_single_entry(self, entry_id: int):
        try:
            new_id = db.duplicate_entry(entry_id)

            if hasattr(self, 'populate_tree'):
                self.populate_tree()
            self._refresh_current_view()

            row = self._find_row_by_id(new_id)
            if row is not None:
                self.table.setCurrentCell(row, 0)
                self.table.selectRow(row)

            self._log_status("Entry duplicated", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to duplicate entry:\n{e}")

    def duplicate_entry(self):
        sel_model = self.table.selectionModel()
        if not sel_model:
            return

        selected_rows = sel_model.selectedRows()
        if len(selected_rows) != 1:
            return

        entry_id = self._current_entry_id_from_table()
        if entry_id is None:
            return

        self._duplicate_single_entry(entry_id)

    def _move_entries_to_category(self, entry_ids, target_category):
        if not entry_ids:
            return

        if not getattr(self, "cipher", None):
            QMessageBox.critical(self, "Error", "Vault is locked; cannot move entries.")
            return

        moved = 0
        errors = 0

        for entry_id in entry_ids:
            try:
                row = db.fetch_entry_dict(int(entry_id)) or None
                if not row:
                    errors += 1
                    continue

                entry_plain = db.decrypt_row_to_plain(row, self.cipher) or {}
                entry_plain["id"] = entry_id
                entry_plain["category"] = target_category

                entry_plain["expiry_date"] = row.get("expiry_date")
                entry_plain["status"] = row.get("status", "active")

                new_row = db.encrypt_plain_to_row(
                    plain=entry_plain,
                    cipher=self.cipher,
                    base_row=row,
                    mirror_plaintext=STORE_PLAINTEXT_EMAIL,
                    preserve_existing_cipher_on_empty=True,
                )

                if not STORE_PLAINTEXT_EMAIL:
                    new_row["email"] = ""

                if "expiry_date" in entry_plain:
                    new_row["expiry_date"] = entry_plain["expiry_date"]
                if "status" in entry_plain:
                    new_row["status"] = entry_plain["status"]

                update_payload = dict(new_row)
                update_payload.pop("id", None)

                db.update_entry_full(entry_id, update_payload)
                moved += 1
            except Exception:
                errors += 1

        if hasattr(self, "_refresh_tree_and_table"):
            self._refresh_tree_and_table(target_category=target_category)
        else:
            self.reload()

        if hasattr(self, "_log_status"):
            if moved and not errors:
                label = target_category or "Uncategorized"
                self._log_status(
                    f"Moved {moved} entr{'y' if moved == 1 else 'ies'} to '{label}'.",
                    2000,
                )
            elif moved:
                self._log_status(
                    f"Moved {moved} entr{'y' if moved == 1 else 'ies'}; {errors} failed.",
                    4000,
                    is_error=True,
                )
            elif errors:
                self._log_status("Failed to move selected entries.", 4000, is_error=True)