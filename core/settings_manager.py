from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from typing import Any, Dict
import os

APP_NAME = "AnchorPass"

def _appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    return Path(base) / APP_NAME if base else (Path.home() / f".{APP_NAME}")

def _user_documents() -> Path:
    docs = Path(os.path.expanduser("~/Documents"))
    return docs if docs.exists() else Path.home()

def _config_dir() -> Path:
    return _user_documents() / "anchorpass" / "settings"

CONFIG_DIR = _config_dir()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = CONFIG_DIR / "settings.json" #global settings file

DEFAULT_SETTINGS: Dict[str, Any] = {
    "auto_lock_minutes": 10,
    "lock_on_sleep": True,
    "database_path": "vault.db",

    "clipboard_clear_seconds": 15,
    "lock_on_minimize": True,
    "copy_notifications": True,

    "theme": "dark",
    "minimize_to_tray_on_exit": False,
    "enable_backup": True,
    "backup_schedule": "Daily",
    "backup_time": "02:00",
    "backup_path": str(_user_documents() / "anchorpass" / "backup"),
    "backup_number": 5,
}

def _atomic_write(path: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        os.close(fd)
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass

def _maybe_migrate_legacy_settings() -> None:
    """Migrate an existing settings.json from old locations to AppData once."""
    if SETTINGS_PATH.exists():
        return
    candidates = []
    try:
        exe_dir = Path(getattr(sys, "frozen", False) and sys.executable or __file__).resolve().parent
        candidates.append(exe_dir / "settings.json")
    except Exception:
        pass

    candidates.append(Path.cwd() / "settings.json")

    for old in candidates:
        if old.exists():
            try:
                data = json.loads(old.read_text(encoding="utf-8"))
                _atomic_write(SETTINGS_PATH, json.dumps(data, indent=4))
                return
            except Exception:
                break

def _settings_path_for_db(db_path: str | Path) -> Path:
    p = Path(db_path).expanduser().resolve()
    return CONFIG_DIR / f"{p.name}.settings.json"

class SettingsManager:
    def __init__(self, db_path: str | Path | None = None):
        
        raw_arg = db_path

        if db_path is not None:
            # PER-DB MODE
            self._db_path = Path(db_path).expanduser().resolve()
            self._settings_path = _settings_path_for_db(self._db_path)
            mode = "per-db"
        else:
            # GLOBAL MODE (legacy / app-wide)
            _maybe_migrate_legacy_settings()
            self._db_path = None
            self._settings_path = SETTINGS_PATH
            mode = "global"

        self._settings_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._settings_path.exists():
            initial = DEFAULT_SETTINGS.copy()
            if self._db_path is not None:
                initial["database_path"] = str(self._db_path)

            try:
                _atomic_write(self._settings_path, json.dumps(initial, indent=4))
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create settings file at {self._settings_path!r}: {e}"
                ) from e

        try:
            self._data: Dict[str, Any] = json.loads(
                self._settings_path.read_text(encoding="utf-8")
            )
        except Exception:
            try:
                backup = self._settings_path.with_suffix(self._settings_path.suffix + ".bak")
                backup.write_text(
                    self._settings_path.read_text(encoding="utf-8"),
                    encoding="utf-8"
                )
            except Exception:
                pass

            self._data = DEFAULT_SETTINGS.copy()
            if self._db_path is not None:
                self._data["database_path"] = str(self._db_path)
            self.save()

        for k, v in DEFAULT_SETTINGS.items():
            self._data.setdefault(k, v)

        if not self._data.get("backup_path"):
            self._data["backup_path"] = DEFAULT_SETTINGS["backup_path"]
            self.save()

    def save(self) -> None:
        _atomic_write(self._settings_path, json.dumps(self._data, indent=4))

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    @property
    def all(self) -> Dict[str, Any]:
        return dict(self._data)