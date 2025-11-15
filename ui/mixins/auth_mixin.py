from PySide6.QtWidgets import QMessageBox, QDialog, QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import QEventLoop, Qt, QSize
from PySide6.QtGui import QPalette
from core import db, crypto, security
from ui.dialogs import DatabaseDialog, MasterDialog, ChangePasswordDialog
from ui.widgets.unlock_overlay import UnlockOverlay
from pathlib import Path
from core.db_paths import get_user_documents_dir
from ui.widgets.button import _glyph_to_icon

class AuthMixin:
    def _login(self) -> bool:
        default_db_dir = get_user_documents_dir() / "securepasswordmanager" / "data"

        while True:
            db_dlg = DatabaseDialog(self)
            if db_dlg.exec() != QDialog.Accepted:
                return False

            db_path, is_new_db = db_dlg.values()
            if not db_path:
                QMessageBox.warning(self, "Error", "Create a database first.")
                continue

            p = Path(str(db_path))
            if is_new_db:
                parent = p.parent if str(p.parent) not in ("", ".", "/") else default_db_dir
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                filename = p.name or "vault.db"
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
            dlg = MasterDialog(setup=is_new_db, parent=self,
                            icon_family=getattr(self, "icon_family", None))
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

        try:
            self._repair_encryption()
        except Exception:
            pass

        return True

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

    def _ask_master_inline(self, setup: bool):
        overlay = UnlockOverlay(parent=self.centralWidget(), setup=setup,
                                icon_family=getattr(self, "icon_family", None))
        overlay.show(); overlay.raise_()

        loop = QEventLoop()
        result = {"ok": False, "p1": "", "p2": "", "m": 0}

        def on_ok(p1, p2, minutes):
            result.update(ok=True, p1=p1, p2=p2, m=minutes)
            loop.quit()

        def on_cancel():
            result.update(ok=False)
            loop.quit()

        overlay.accepted.connect(on_ok)
        overlay.canceled.connect(on_cancel)

        loop.exec()
        overlay.deleteLater()
        return result["ok"], result["p1"], result["p2"], result["m"]
    
    def prompt_login(self, force: bool = False) -> None:
        if getattr(self, "_login_in_progress", False):
            return
        if getattr(self, "cipher", None) and not force:
            return

        self._login_in_progress = True
        try:
            ok = self._login()
            if ok:
                    self.unlock()
            else:
                    self.lock()
        finally:
            self._login_in_progress = False

    def unlock(self):
        self.show_lock_overlay(False)
        self._set_menu_locked_state(False)
        self._update_tray_icon_locked_state(False)
        
        if hasattr(self, "show_lock_overlay"):
            self.show_lock_overlay(False)
        if hasattr(self, "_cache_active_db_path_safely"):
            self._cache_active_db_path_safely()
        if hasattr(self, "populate_tree"):
            self.populate_tree()
        if hasattr(self, "reload"):
            self.reload()
        if hasattr(self, "_update_actions_for_selection"):
            self._update_actions_for_selection()

        for fn in ("_start_idle_lock_timer",
                "_start_scheduled_backup_timer",
                "_start_sleep_guard",
                "_start_expiration_checker"):
            if hasattr(self, fn):
                getattr(self, fn)()

    def _init_lock_overlay(self):
        if hasattr(self, "_lock_overlay"):
            return

        cw = self.centralWidget()
        self._lock_overlay = QWidget(cw)
        self._lock_overlay.setObjectName("LockOverlay")
        self._lock_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self._lock_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._lock_overlay.setFocusPolicy(Qt.StrongFocus)

        lay = QVBoxLayout(self._lock_overlay)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        glyph = chr(0xE898)

        color = self.palette().color(QPalette.ButtonText)
        icon = _glyph_to_icon(glyph, size=50, color=color, y_offset=3)

        btn = QPushButton("Unlock")
        btn.setDefault(True)
        btn.setIcon(icon)
        btn.setIconSize(QSize(50, 50))

        btn.clicked.connect(lambda: self.prompt_login(force=True))
        lay.addWidget(btn, 0, Qt.AlignCenter)

        self._lock_btn = btn

    def show_lock_overlay(self, show: bool):
        cw = self.centralWidget()
        if not hasattr(self, "_lock_overlay"):
            self._init_lock_overlay()
        self._lock_overlay.setGeometry(cw.rect())
        self._lock_overlay.setVisible(show)
        if show:
            self._lock_overlay.raise_()
            try:
                self._lock_overlay.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            except Exception:
                self._lock_overlay.setFocus()
            if hasattr(self, "_lock_btn"):
                self._lock_btn.setEnabled(True)
