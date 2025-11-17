from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import os

import re
from PySide6.QtWidgets import QMessageBox

from core.settings_manager import SettingsManager
from core import db
from core.db_paths import get_user_documents_dir

class BackupMixin:

    def _resolve_db_path(self, want_exists: bool = True) -> Optional[Path]:
        def to_valid_path(v) -> Optional[Path]:
            try:
                if not v:
                    return None
                p = Path(str(v))
                return p if (not want_exists or p.exists()) else None
            except Exception:
                return None

        sources = [
            lambda: (getattr(db, "get_db_path", None)() 
                    if callable(getattr(db, "get_db_path", None)) else None),
            lambda: getattr(self, "_active_db_path", None),
            lambda: getattr(self, "current_db", None),
            lambda: SettingsManager().get("database_path", ""),
            lambda: getattr(db, "DB_PATH", None),
        ]

        for src in sources:
            try:
                v = src()
            except Exception:
                v = None
            p = to_valid_path(v)
            if p is not None:
                return p

        return None

    def _resolve_backup_folder(self) -> Optional[Path]:
        sm = SettingsManager()
        folder_str = (sm.get("backup_path", "") or "").strip()
        if not folder_str:
            folder_str = (sm.get("backup_dir", "") or "").strip()
        if not folder_str:
            return None
        try:
            return Path(folder_str).expanduser()
        except Exception:
            return None

    def _cache_active_db_path(self, path) -> None:
        try:
            if path:
                p = Path(str(path))
                self._active_db_path = str(p)
                try:
                    SettingsManager().set("database_path", str(p))
                except Exception:
                    pass
        except Exception:
            pass

    def export_backup(self, reason: str = "manual") -> Optional[Path]:
        dst = self._export_backup_core(reason=reason)
        if dst is None:
            # show UI messages based on failure reason if you want
            QMessageBox.warning(self, "Backup", "Backup failed or is not configured.")
            try:
                self.statusBar().showMessage("Backup failed.", 3000)
            except Exception:
                pass
            return None

        try:
            self.statusBar().showMessage(f"Backup saved: {dst.name}", 3000)
        except Exception:
            pass
        return dst

    def maybe_auto_backup(self, reason: str) -> None:
        """
        AUTO backups only:
          - honor 'backup_disabled'
          - only run on 'close' (per your configuration)
        """
        sm = SettingsManager()
        if bool(sm.get("backup_disabled", False)):
            return
        if reason == "close" and bool(sm.get("backup_on_close", True)):
            self.export_backup(reason=reason)

    def _read_retention(self, sm):
        def to_int(val):
            try: return int(str(val).strip())
            except: return None
        keep = to_int(sm.get("backup_retention", None))
        if keep is None:
            keep = to_int(sm.get("backup_number", None))
        if keep is None:
            keep = 5
        return max(1, keep)

    def _apply_backup_retention(self, backup_dir, stem, suffix, keep):
        suf = suffix.lstrip('.')
        patterns = [f"{stem}-*-*.{suf}", f"{stem}-*.{suf}"]
        seen, files = set(), []
        for pat in patterns:
            for p in backup_dir.glob(pat):
                if p.is_file():
                    rp = p.resolve()
                    if rp not in seen:
                        seen.add(rp); files.append(p)

        rx = re.compile(rf"^{re.escape(stem)}-(\d{{8}}-\d{{6}})(?:-[^-]+)?\.{re.escape(suf)}$")
        def ts_key(p):
            m = rx.match(p.name)
            return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S") if m else datetime.min

        files.sort(key=ts_key, reverse=True)
        for old in files[keep:]:
            try:
                old.unlink(missing_ok=True)
            except Exception as e:
                pass

    def _diagnose_paths(self) -> Tuple[str, str]:
        candidates = []
        try:
            getp = getattr(db, "get_db_path", None)
            if callable(getp):
                p = getp()
                if p:
                    candidates.append(("db.get_db_path()", Path(p)))
        except Exception:
            pass

        try:
            if getattr(self, "_active_db_path", None):
                candidates.append(("_active_db_path", Path(str(self._active_db_path))))
        except Exception:
            pass

        try:
            if getattr(self, "current_db", None):
                candidates.append(("current_db", Path(str(self.current_db))))
        except Exception:
            pass

        try:
            s = SettingsManager().get("database_path", "")
            if s:
                candidates.append(("settings.database_path", Path(s)))
        except Exception:
            pass

        try:
            if getattr(db, "DB_PATH", None):
                candidates.append(("db.DB_PATH", Path(str(db.DB_PATH))))
        except Exception:
            pass

        chosen = None
        for src, p in candidates:
            if p.exists():
                chosen = (src, p)
                break

        db_line = "Active DB: <not found>"
        if chosen:
            db_line = f"Active DB: {chosen[1]}  (from {chosen[0]})"
        elif candidates:
            db_line = f"Active DB candidate (missing): {candidates[0][1]}  (from {candidates[0][0]})"

        bdir = self._resolve_backup_folder()
        backup_line = f"Backup folder: {bdir if bdir else '<not set>'}"
        return db_line, backup_line

    def _default_backup_dir(self) -> Path:
        return get_user_documents_dir() / "securepasswordmanager" / "backup"

    def _ensure_backup_path_default(self):
        path = (self.settings.get("backup_path", "") or "").strip()
        if not path:
            default_dir = self._default_backup_dir()
            default_dir.mkdir(parents=True, exist_ok=True)
            self.settings.set("backup_path", str(default_dir))

    def _export_backup_core(self, reason: str = "manual") -> Optional[Path]:
        sm = SettingsManager()

        src = self._resolve_db_path()
        if not src or not src.exists():
            return None

        backup_dir = self._resolve_backup_folder()
        if not backup_dir:
            return None

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = src.stem
        suffix = src.suffix or ".db"
        reason_tag = reason if reason in ("manual", "scheduled", "close") else "manual"
        dst = backup_dir / f"{stem}-{timestamp}-{reason_tag}{suffix}"

        tmp = dst.with_suffix(dst.suffix + ".part")
        try:
            shutil.copy2(src, tmp)
            tmp.replace(dst)
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        keep = self._read_retention(sm)
        if keep > 0:
            self._apply_backup_retention(backup_dir, stem, suffix, keep)

        return dst
