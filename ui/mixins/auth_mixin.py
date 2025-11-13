from PySide6.QtWidgets import QMessageBox, QDialog
from core import db, crypto, security
from ui.dialogs import DatabaseDialog, MasterDialog, ChangePasswordDialog
import os, sys
from pathlib import Path
from core.db_paths import get_user_documents_dir

class AuthMixin:
    def _login(self):
        from PySide6.QtWidgets import QMessageBox
        default_db_dir = get_user_documents_dir() / "securepasswordmanager" / "data"
        while True:
            db_dlg = DatabaseDialog()
            if not db_dlg.exec():
                return False
            db_path, is_new_db = db_dlg.values()
            if not db_path:
                QMessageBox.warning(self, "Error", "Create a database first.")
                continue
            p = Path(str(db_path))
            if is_new_db:
                parent = p.parent if str(p.parent) not in ("", ".", "/") else default_db_dir
                filename = p.name or "vault.db"
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                p = parent / filename
            db_path = str(p)
            break

        db.set_db_path(db_path)
        db.init()
        db.save_last_db(db_path)
        self.current_db = db_path
        self._update_title()

        try:
            self._ensure_backup_path_default()
        except Exception:
            pass
        
        while True:
            dlg = MasterDialog(setup=is_new_db, icon_family=getattr(self, "icon_family", None))
            if dlg.exec() != QDialog.Accepted:
                return False

            p1, p2, minutes = dlg.values()

            if is_new_db:
                if not p1 or p1 != p2:
                    QMessageBox.warning(self, "Error", "Passwords do not match.")
                    continue
                security.set_master(p1)
                break
            else:
                if not security.verify_master(p1):
                    QMessageBox.critical(self, "Error", "Incorrect master password.")
                    continue
                break

        salt = security.get_salt()
        self.cipher = crypto.make_cipher(p1, salt)
        self.master = p1
        self.auto_lock_minutes = minutes

        self._repair_encryption()

    def change_master_password(self):
        dlg = ChangePasswordDialog(self, icon_family=getattr(self, "icon_family", None))
        if dlg.exec() != QDialog.Accepted:
            return
        old_pw, new_pw = dlg.values()

        if not security.verify_master(old_pw):
            QMessageBox.critical(self, "Change Password", "Current master password is incorrect.")
            return

        try:
            old_cipher = self.cipher 
            extra_ciphers = []
            if hasattr(crypto, "derive_cipher_from_password"):
                try:
                    legacy_cipher = crypto.derive_cipher_from_password(self.master)
                    if legacy_cipher:
                        extra_ciphers.append(legacy_cipher)
                except Exception:
                    pass

            salt = security.get_salt()
            new_cipher = crypto.make_cipher(new_pw, salt)

            stats = db.rewrap_all_encrypted_fields(
                old_cipher=old_cipher,
                new_cipher=new_cipher,
                extra_ciphers=extra_ciphers,
            )

            security.update_master_password_hash(new_pw)
            self.master = new_pw
            self.cipher = new_cipher

            self._repair_encryption(extra_ciphers=[old_cipher])

            if hasattr(self, "reload"):
                self.reload()

            QMessageBox.information(
                self,
                "Success",
                (
                    "Master password changed successfully.\n\n"
                ),
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change password:\n{e}")

    def _repair_encryption(self, extra_ciphers=None):
        try:
            rows = db.fetch_all_entries()
            if not rows:
                return

            changed = False
            extra_ciphers = extra_ciphers or []

            for r in rows:
                rid = r.get("id")
                if rid is None:
                    continue

                plain = db.decrypt_row_to_plain(r, self.cipher, extra_ciphers=extra_ciphers)
                plain["id"] = rid

                normalized = db.encrypt_plain_to_row(
                    plain=plain,
                    cipher=self.cipher,
                    base_row=r,
                    mirror_plaintext=False,
                    preserve_existing_cipher_on_empty=True,
                )

                payload = dict(normalized)
                payload.pop("id", None)
                if any(payload.get(k) != r.get(k) for k in payload.keys()):
                    changed = True
                    db.update_entry_full(rid, payload)

            if changed and hasattr(self, "reload"):
                self.reload()

        except Exception as e:
            print(f"[Repair skipped] {e}")