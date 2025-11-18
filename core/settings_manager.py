from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from typing import Any, Dict
import os

APP_NAME = "AnchorPass"

def _appdata_dir() -> Path:
    """Roaming AppData (stable across runs/updates)."""
    base = os.environ.get("APPDATA")
    #return Path(base) / APP_NAME if base else (Path.home() / f".{APP_NAME})
    return Path.home() / f".{APP_NAME}"

def _user_documents() -> Path:
    """Simpler Documents resolution via expanduser."""
    docs = Path(os.path.expanduser("~/Documents"))
    return docs if docs.exists() else Path.home()

def _config_dir() -> Path:
    return _user_documents() / "anchorpass" / "settings"

CONFIG_DIR = _config_dir()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = CONFIG_DIR / "settings.json"

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

class SettingsManager:
    def __init__(self):
        _maybe_migrate_legacy_settings()

        if not SETTINGS_PATH.exists():
            _atomic_write(SETTINGS_PATH, json.dumps(DEFAULT_SETTINGS, indent=4))

        try:
            self._data: Dict[str, Any] = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            try:
                (SETTINGS_PATH.parent / "settings.bak").write_text(
                    SETTINGS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
                )
            except Exception:
                pass
            self._data = DEFAULT_SETTINGS.copy()
            self.save()

        if not self._data.get("backup_path"):
            self._data["backup_path"] = DEFAULT_SETTINGS["backup_path"]
            self.save()

    def save(self) -> None:
        _atomic_write(SETTINGS_PATH, json.dumps(self._data, indent=4))

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    @property
    def all(self) -> Dict[str, Any]:
        return dict(self._data)